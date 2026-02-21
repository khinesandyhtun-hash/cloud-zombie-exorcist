#!/bin/bash
#
# Cloud-Zombie Exorcist - Snowflake Optimization Scripts
# Safely suspends, resizes, or drops underutilized warehouses
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
DRY_RUN=${DRY_RUN:-true}
SNOWFLAKE_ACCOUNT="${SNOWFLAKE_ACCOUNT:-}"
SNOWFLAKE_USER="${SNOWFLAKE_USER:-}"
SNOWFLAKE_PASSWORD="${SNOWFLAKE_PASSWORD:-}"
SNOWFLAKE_WAREHOUSE="${SNOWFLAKE_WAREHOUSE:-ACCOUNTADMIN}"
REPORT_FILE="${REPORT_FILE:-./reports/snowflake_optimization_$(date +%Y%m%d_%H%M%S).json}"

# Check for snowsql
check_dependencies() {
    if command -v snowsql &> /dev/null; then
        log_success "SnowSQL available"
        return 0
    fi

    log_warning "SnowSQL not found. Will use REST API instead."
    return 0
}

# Execute Snowflake SQL
execute_sql() {
    local sql="$1"
    local output_format="${2:-json}"

    if command -v snowsql &> /dev/null; then
        snowsql -a "$SNOWFLAKE_ACCOUNT" \
                -u "$SNOWFLAKE_USER" \
                -w "$SNOWFLAKE_WAREHOUSE" \
                --query "$sql" \
                --format "$output_format" \
                --silent 2>/dev/null
    else
        log_error "SnowSQL required for SQL execution"
        return 1
    fi
}

# Get warehouse details
get_warehouse_info() {
    local warehouse_name="$1"

    log_info "Getting info for warehouse: $warehouse_name"

    local sql="SHOW WAREHOUSES LIKE '$warehouse_name'"
    execute_sql "$sql" "json"
}

# Suspend warehouse
suspend_warehouse() {
    local warehouse_name="$1"

    log_info "Suspending warehouse: $warehouse_name"

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would suspend warehouse: $warehouse_name"
        return 0
    fi

    local sql="ALTER WAREHOUSE $warehouse_name SUSPEND"
    execute_sql "$sql"

    log_success "Warehouse $warehouse_name suspended"
}

# Resume warehouse
resume_warehouse() {
    local warehouse_name="$1"

    log_info "Resuming warehouse: $warehouse_name"

    local sql="ALTER WAREHOUSE $warehouse_name RESUME"
    execute_sql "$sql"

    log_success "Warehouse $warehouse_name resumed"
}

# Resize warehouse
resize_warehouse() {
    local warehouse_name="$1"
    local new_size="$2"

    log_info "Resizing warehouse $warehouse_name to $new_size"

    # Validate size
    local valid_sizes=("X-SMALL" "SMALL" "MEDIUM" "LARGE" "X-LARGE" "2X-LARGE" "3X-LARGE" "4X-LARGE")
    local valid=false
    for size in "${valid_sizes[@]}"; do
        if [[ "${size^^}" == "${new_size^^}" ]]; then
            valid=true
            break
        fi
    done

    if [ "$valid" = false ]; then
        log_error "Invalid warehouse size: $new_size"
        log_error "Valid sizes: ${valid_sizes[*]}"
        return 1
    fi

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would resize $warehouse_name to $new_size"
        return 0
    fi

    local sql="ALTER WAREHOUSE $warehouse_name SET WAREHOUSE_SIZE = $new_size"
    execute_sql "$sql"

    log_success "Warehouse $warehouse_name resized to $new_size"
}

# Drop warehouse
drop_warehouse() {
    local warehouse_name="$1"

    log_warning "⚠️  Dropping warehouse: $warehouse_name"

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would drop warehouse: $warehouse_name"
        return 0
    fi

    # Confirm
    read -p "⚠️  Drop warehouse $warehouse_name? This cannot be undone. (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        log_warning "Skipped dropping $warehouse_name"
        return 0
    fi

    # First suspend
    suspend_warehouse "$warehouse_name"

    local sql="DROP WAREHOUSE $warehouse_name"
    execute_sql "$sql"

    log_success "Warehouse $warehouse_name dropped"
}

# Set auto-suspend
set_auto_suspend() {
    local warehouse_name="$1"
    local timeout_seconds="${2:-60}"

    log_info "Setting auto-suspend for $warehouse_name to ${timeout_seconds}s"

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would set auto-suspend for $warehouse_name"
        return 0
    fi

    local sql="ALTER WAREHOUSE $warehouse_name SET AUTO_SUSPEND = $timeout_seconds"
    execute_sql "$sql"

    log_success "Auto-suspend set for $warehouse_name (${timeout_seconds}s)"
}

# Set auto-resume
set_auto_resume() {
    local warehouse_name="$1"
    local enabled="${2:-true}"

    log_info "Setting auto-resume for $warehouse_name to $enabled"

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would set auto-resume for $warehouse_name"
        return 0
    fi

    local sql="ALTER WAREHOUSE $warehouse_name SET AUTO_RESUME = $enabled"
    execute_sql "$sql"

    log_success "Auto-resume set for $warehouse_name"
}

# Get warehouse usage history
get_warehouse_usage() {
    local warehouse_name="${1:-}"
    local days="${2:-30}"

    log_info "Getting warehouse usage for the last $days days"

    local warehouse_filter=""
    if [ -n "$warehouse_name" ]; then
        warehouse_filter="WHERE WAREHOUSE_NAME = '$warehouse_name'"
    fi

    local sql="
        SELECT
            WAREHOUSE_NAME,
            WAREHOUSE_SIZE,
            SUM(CREDITS_USED) AS TOTAL_CREDITS,
            AVG(CREDITS_USED) AS AVG_CREDITS_PER_HOUR,
            COUNT(DISTINCT DATE_TRUNC('hour', START_TIME)) AS HOURS_ACTIVE,
            COUNT(*) AS QUERY_COUNT
        FROM TABLE(INFORMATION_SCHEMA.WAREHOUSE_LOAD_HISTORY(
            DATE_RANGE_START => DATEADD(day, -$days, CURRENT_DATE()),
            DATE_RANGE_END => CURRENT_DATE()
        ))
        $warehouse_filter
        GROUP BY WAREHOUSE_NAME, WAREHOUSE_SIZE
        ORDER BY TOTAL_CREDITS DESC
    "

    execute_sql "$sql" "json"
}

# Identify idle warehouses
find_idle_warehouses() {
    local threshold_hours="${1:-10}"
    local days="${2:-30}"

    log_info "Finding warehouses with less than $threshold_hours active hours in $days days"

    local sql="
        SELECT
            WAREHOUSE_NAME,
            WAREHOUSE_SIZE,
            STATE,
            SUM(CREDITS_USED) AS TOTAL_CREDITS,
            COUNT(DISTINCT DATE_TRUNC('hour', START_TIME)) AS HOURS_ACTIVE
        FROM TABLE(INFORMATION_SCHEMA.WAREHOUSE_LOAD_HISTORY(
            DATE_RANGE_START => DATEADD(day, -$days, CURRENT_DATE()),
            DATE_RANGE_END => CURRENT_DATE()
        ))
        GROUP BY WAREHOUSE_NAME, WAREHOUSE_SIZE, STATE
        HAVING HOURS_ACTIVE < $threshold_hours
        ORDER BY TOTAL_CREDITS DESC
    "

    execute_sql "$sql" "json"
}

# Find oversized warehouses
find_oversized_warehouses() {
    local utilization_threshold="${1:-30}"

    log_info "Finding warehouses with credit utilization below ${utilization_threshold}%"

    local sql="
        SELECT
            WAREHOUSE_NAME,
            WAREHOUSE_SIZE,
            AVG(CREDITS_USED) AS AVG_CREDITS,
            CASE WAREHOUSE_SIZE
                WHEN 'X-SMALL' THEN 1
                WHEN 'SMALL' THEN 2
                WHEN 'MEDIUM' THEN 4
                WHEN 'LARGE' THEN 8
                WHEN 'X-LARGE' THEN 16
                WHEN '2X-LARGE' THEN 32
                WHEN '3X-LARGE' THEN 64
                WHEN '4X-LARGE' THEN 128
            END AS MAX_CREDITS_PER_HOUR,
            (AVG(CREDITS_USED) / CASE WAREHOUSE_SIZE
                WHEN 'X-SMALL' THEN 1
                WHEN 'SMALL' THEN 2
                WHEN 'MEDIUM' THEN 4
                WHEN 'LARGE' THEN 8
                WHEN 'X-LARGE' THEN 16
                WHEN '2X-LARGE' THEN 32
                WHEN '3X-LARGE' THEN 64
                WHEN '4X-LARGE' THEN 128
            END) * 100 AS UTILIZATION_PERCENT
        FROM TABLE(INFORMATION_SCHEMA.WAREHOUSE_LOAD_HISTORY(
            DATE_RANGE_START => DATEADD(month, -1, CURRENT_DATE()),
            DATE_RANGE_END => CURRENT_DATE()
        ))
        GROUP BY WAREHOUSE_NAME, WAREHOUSE_SIZE
        HAVING UTILIZATION_PERCENT < $utilization_threshold
        ORDER BY UTILIZATION_PERCENT ASC
    "

    execute_sql "$sql" "json"
}

# Process findings from JSON report
process_findings() {
    local findings_file="$1"
    local action="${2:-report}"

    if [ ! -f "$findings_file" ]; then
        log_error "Findings file not found: $findings_file"
        exit 1
    fi

    log_info "Processing Snowflake findings from: $findings_file"

    local findings
    findings=$(jq -c '.findings[] | select(.resource_type == "Snowflake")' "$findings_file" 2>/dev/null) || {
        log_error "No Snowflake findings found"
        return 1
    }

    while IFS= read -r finding; do
        [ -z "$finding" ] && continue

        local resource_id recommendation severity metadata
        resource_id=$(echo "$finding" | jq -r '.resource_id')
        recommendation=$(echo "$finding" | jq -r '.recommendation')
        severity=$(echo "$finding" | jq -r '.severity')
        metadata=$(echo "$finding" | jq -r '.metadata')

        log_info "Processing: $resource_id ($severity)"

        if [[ "$recommendation" == *"Suspend"* ]] || [[ "$recommendation" == *"suspend"* ]]; then
            if [ "$action" = "execute" ]; then
                suspend_warehouse "$resource_id"
            else
                log_info "Would suspend: $resource_id"
            fi
        elif [[ "$recommendation" == *"drop"* ]] || [[ "$recommendation" == *"Drop"* ]]; then
            if [ "$action" = "execute" ]; then
                drop_warehouse "$resource_id"
            else
                log_info "Would drop: $resource_id"
            fi
        elif [[ "$recommendation" == *"Resize"* ]] || [[ "$recommendation" == *"resize"* ]]; then
            if [ "$action" = "execute" ]; then
                local suggested_size
                suggested_size=$(echo "$metadata" | jq -r '.suggested_size // "MEDIUM"')
                resize_warehouse "$resource_id" "$suggested_size"
            else
                log_info "Would resize: $resource_id"
            fi
        elif [[ "$recommendation" == *"auto-suspend"* ]] || [[ "$recommendation" == *"Auto-suspend"* ]]; then
            if [ "$action" = "execute" ]; then
                set_auto_suspend "$resource_id" 60
            else
                log_info "Would set auto-suspend: $resource_id"
            fi
        fi

    done <<< "$findings"

    log_success "Snowflake processing complete"
}

# Generate optimization script from findings
generate_optimization_script() {
    local findings_file="$1"
    local output_file="${2:-./scripts/apply_optimizations.sh}"

    if [ ! -f "$findings_file" ]; then
        log_error "Findings file not found: $findings_file"
        exit 1
    fi

    cat > "$output_file" <<'HEADER'
#!/bin/bash
# Auto-generated Snowflake optimization script
# Generated by Cloud-Zombie Exorcist

set -euo pipefail

export DRY_RUN=false

HEADER

    local findings
    findings=$(jq -c '.findings[] | select(.resource_type == "Snowflake")' "$findings_file")

    while IFS= read -r finding; do
        [ -z "$finding" ] && continue

        local resource_id recommendation
        resource_id=$(echo "$finding" | jq -r '.resource_id')
        recommendation=$(echo "$finding" | jq -r '.recommendation')

        echo "# $recommendation"

        if [[ "$recommendation" == *"Suspend"* ]]; then
            echo "suspend_warehouse \"$resource_id\""
        elif [[ "$recommendation" == *"Resize"* ]]; then
            local size
            size=$(echo "$finding" | jq -r '.metadata.suggested_size // "MEDIUM"')
            echo "resize_warehouse \"$resource_id\" \"$size\""
        elif [[ "$recommendation" == *"auto-suspend"* ]]; then
            echo "set_auto_suspend \"$resource_id\" 60"
        fi

        echo ""
    done <<< "$findings" >> "$output_file"

    chmod +x "$output_file"
    log_success "Optimization script generated: $output_file"
}

# Main execution
main() {
    local command="${1:-help}"
    shift || true

    check_dependencies

    case "$command" in
        suspend)
            suspend_warehouse "$@"
            ;;
        resume)
            resume_warehouse "$@"
            ;;
        resize)
            resize_warehouse "$@"
            ;;
        drop)
            drop_warehouse "$@"
            ;;
        auto-suspend)
            set_auto_suspend "$@"
            ;;
        auto-resume)
            set_auto_resume "$@"
            ;;
        usage)
            get_warehouse_usage "$@"
            ;;
        idle)
            find_idle_warehouses "$@"
            ;;
        oversized)
            find_oversized_warehouses "$@"
            ;;
        process)
            process_findings "$@"
            ;;
        generate-script)
            generate_optimization_script "$@"
            ;;
        help|*)
            echo "Cloud-Zombie Exorcist - Snowflake Optimization Scripts"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  suspend <warehouse>              Suspend warehouse"
            echo "  resume <warehouse>               Resume warehouse"
            echo "  resize <warehouse> <size>        Resize warehouse"
            echo "  drop <warehouse>                 Drop warehouse"
            echo "  auto-suspend <warehouse> [secs]  Set auto-suspend timeout"
            echo "  auto-resume <warehouse> [bool]   Set auto-resume"
            echo "  usage [warehouse] [days]         Get warehouse usage"
            echo "  idle [hours] [days]              Find idle warehouses"
            echo "  oversized [threshold%]           Find oversized warehouses"
            echo "  process <findings.json> [action] Process findings"
            echo "  generate-script <findings.json>  Generate optimization script"
            echo ""
            echo "Environment Variables:"
            echo "  SNOWFLAKE_ACCOUNT     Snowflake account identifier"
            echo "  SNOWFLAKE_USER        Snowflake username"
            echo "  SNOWFLAKE_PASSWORD    Snowflake password"
            echo "  SNOWFLAKE_WAREHOUSE   Admin warehouse for operations"
            echo "  DRY_RUN=true|false    Enable/disable dry run"
            echo ""
            echo "Examples:"
            echo "  $0 suspend WH_IDLE"
            echo "  $0 resize WH_LARGE X-SMALL"
            echo "  $0 process findings.json report"
            echo "  DRY_RUN=false $0 process findings.json execute"
            ;;
    esac
}

main "$@"
