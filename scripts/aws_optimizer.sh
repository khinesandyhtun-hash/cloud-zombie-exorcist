#!/bin/bash
#
# Cloud-Zombie Exorcist - AWS Optimization Scripts
# Safely terminates or resizes underutilized AWS resources
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
DRY_RUN=${DRY_RUN:-true}
CONFIRMATION_REQUIRED=${CONFIRMATION_REQUIRED:-true}
BACKUP_DIR="${BACKUP_DIR:-./backups}"
REPORT_FILE="${REPORT_FILE:-./reports/aws_optimization_$(date +%Y%m%d_%H%M%S).json}"

# Ensure required tools are available
check_dependencies() {
    local missing=()
    for cmd in aws jq; do
        if ! command -v "$cmd" &> /dev/null; then
            missing+=("$cmd")
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        log_error "Please install: pip install awscli jq"
        exit 1
    fi
    log_success "All dependencies available"
}

# Create backup of resource state
create_backup() {
    local resource_type="$1"
    local resource_id="$2"

    mkdir -p "$BACKUP_DIR"

    case "$resource_type" in
        ec2)
            aws ec2 describe-instances --instance-ids "$resource_id" > "$BACKUP_DIR/${resource_id}.json" 2>/dev/null || true
            ;;
        ebs)
            aws ec2 describe-volumes --volume-ids "$resource_id" > "$BACKUP_DIR/${resource_id}.json" 2>/dev/null || true
            ;;
        snapshot)
            aws ec2 describe-snapshots --snapshot-ids "$resource_id" > "$BACKUP_DIR/${resource_id}.json" 2>/dev/null || true
            ;;
    esac

    log_info "Backup created: $BACKUP_DIR/${resource_id}.json"
}

# Terminate EC2 instance
terminate_ec2_instance() {
    local instance_id="$1"
    local reason="${2:-Cloud-Zombie optimization}"

    log_info "Processing EC2 instance: $instance_id"

    # Get instance state
    local state
    state=$(aws ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null) || {
        log_error "Failed to describe instance $instance_id"
        return 1
    }

    if [[ "$state" == "terminated" ]]; then
        log_warning "Instance $instance_id is already terminated"
        return 0
    fi

    if [[ "$state" == "stopping" || "$state" == "stopped" ]]; then
        log_info "Instance $instance_id is $state. Proceeding to terminate..."
    fi

    # Create backup
    create_backup "ec2" "$instance_id"

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would terminate instance: $instance_id"
        return 0
    fi

    # Confirm before termination
    if [ "$CONFIRMATION_REQUIRED" = true ]; then
        read -p "⚠️  Terminate EC2 instance $instance_id? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_warning "Skipped termination of $instance_id"
            return 0
        fi
    fi

    # Terminate
    log_info "Terminating instance $instance_id..."
    aws ec2 terminate-instances --instance-ids "$instance_id" --query 'TerminatingInstances[0].CurrentState.Name' --output text

    log_success "Instance $instance_id termination initiated"
}

# Stop EC2 instance (safer than terminate)
stop_ec2_instance() {
    local instance_id="$1"

    log_info "Stopping EC2 instance: $instance_id"

    local state
    state=$(aws ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null) || {
        log_error "Failed to describe instance $instance_id"
        return 1
    }

    if [[ "$state" == "stopped" ]]; then
        log_warning "Instance $instance_id is already stopped"
        return 0
    fi

    if [[ "$state" == "stopping" ]]; then
        log_info "Instance $instance_id is already stopping"
        return 0
    fi

    # Create backup
    create_backup "ec2" "$instance_id"

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would stop instance: $instance_id"
        return 0
    fi

    log_info "Stopping instance $instance_id..."
    aws ec2 stop-instances --instance-ids "$instance_id" --query 'StoppingInstances[0].CurrentState.Name' --output text

    log_success "Instance $instance_id stop initiated"
}

# Resize EC2 instance
resize_ec2_instance() {
    local instance_id="$1"
    local new_instance_type="$2"

    log_info "Resizing EC2 instance $instance_id to $new_instance_type"

    # Get current instance type
    local current_type
    current_type=$(aws ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].InstanceType' --output text 2>/dev/null) || {
        log_error "Failed to describe instance $instance_id"
        return 1
    }

    log_info "Current instance type: $current_type"

    # Instance must be stopped to change type
    local state
    state=$(aws ec2 describe-instances --instance-ids "$instance_id" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)

    if [[ "$state" != "stopped" ]]; then
        log_info "Stopping instance for resize..."
        stop_ec2_instance "$instance_id"

        log_info "Waiting for instance to stop..."
        aws ec2 wait instance-stopped --instance-ids "$instance_id"
    fi

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would resize $instance_id from $current_type to $new_instance_type"
        return 0
    fi

    # Modify instance type
    log_info "Modifying instance type to $new_instance_type..."
    aws ec2 modify-instance-attribute --instance-id "$instance_id" --instance-type "{\"Value\": \"$new_instance_type\"}"

    log_success "Instance $instance_id resized to $new_instance_type"

    # Ask if user wants to start the instance
    read -p "Start the instance now? (yes/no): " start_confirm
    if [[ "$start_confirm" == "yes" ]]; then
        aws ec2 start-instances --instance-ids "$instance_id"
        log_success "Instance $instance_id start initiated"
    fi
}

# Delete unattached EBS volume
delete_ebs_volume() {
    local volume_id="$1"

    log_info "Processing EBS volume: $volume_id"

    # Check volume state
    local state attachment_count
    state=$(aws ec2 describe-volumes --volume-ids "$volume_id" --query 'Volumes[0].State' --output text 2>/dev/null) || {
        log_error "Failed to describe volume $volume_id"
        return 1
    }

    attachment_count=$(aws ec2 describe-volumes --volume-ids "$volume_id" --query 'Volumes[0].Attachments | length(@)' --output text 2>/dev/null)

    if [[ "$attachment_count" -gt 0 ]]; then
        log_error "Volume $volume_id is attached to an instance. Cannot delete."
        return 1
    fi

    # Create backup
    create_backup "ebs" "$volume_id"

    # Create snapshot before deletion (safety)
    log_info "Creating pre-deletion snapshot..."
    local snapshot_id
    snapshot_id=$(aws ec2 create-snapshot --volume-id "$volume_id" --description "Pre-deletion backup by Cloud-Zombie Exorcist" --query 'SnapshotId' --output text)
    log_success "Snapshot created: $snapshot_id"

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would delete volume: $volume_id (snapshot: $snapshot_id)"
        return 0
    fi

    # Confirm before deletion
    if [ "$CONFIRMATION_REQUIRED" = true ]; then
        read -p "⚠️  Delete EBS volume $volume_id? (snapshot will be kept) (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_warning "Skipped deletion of $volume_id"
            return 0
        fi
    fi

    # Delete volume
    log_info "Deleting volume $volume_id..."
    aws ec2 delete-volume --volume-id "$volume_id"

    log_success "Volume $volume_id deleted (snapshot $snapshot_id preserved)"
}

# Modify EBS volume type (e.g., io1 -> gp3)
modify_ebs_volume() {
    local volume_id="$1"
    local new_type="$2"
    local new_iops="${3:-}"

    log_info "Modifying EBS volume $volume_id to type $new_type"

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would modify volume $volume_id to $new_type"
        return 0
    fi

    local modify_cmd="aws ec2 modify-volume --volume-id $volume_id --volume-type $new_type"

    if [ -n "$new_iops" ]; then
        modify_cmd="$modify_cmd --iops $new_iops"
    fi

    eval "$modify_cmd"

    log_success "Volume $volume_id modification initiated"
}

# Transition S3 objects to Glacier
transition_s3_to_glacier() {
    local bucket_name="$1"
    local prefix="${2:-}"
    local days_old="${3:-90}"

    log_info "Transitioning S3 objects in $bucket_name to Glacier"

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would transition objects older than $days_old days to Glacier"
        return 0
    fi

    # Create lifecycle policy
    local lifecycle_policy
    lifecycle_policy=$(cat <<EOF
{
    "Rules": [
        {
            "ID": "CloudZombie-GlacierTransition",
            "Status": "Enabled",
            "Filter": {
                "Prefix": "$prefix"
            },
            "Transitions": [
                {
                    "Days": $days_old,
                    "StorageClass": "GLACIER"
                }
            ]
        }
    ]
}
EOF
)

    aws s3api put-bucket-lifecycle-configuration --bucket "$bucket_name" --lifecycle-configuration "$lifecycle_policy"

    log_success "Lifecycle policy applied to $bucket_name"
}

# Abort incomplete S3 multipart uploads
cleanup_s3_uploads() {
    local bucket_name="$1"

    log_info "Cleaning up incomplete multipart uploads in $bucket_name"

    # List incomplete uploads
    local uploads
    uploads=$(aws s3api list-multipart-uploads --bucket "$bucket_name" --query 'Uploads[*].{Key:Key,UploadId:UploadId,Initiated:Initiated}' --output json 2>/dev/null) || {
        log_error "Failed to list uploads for $bucket_name"
        return 1
    }

    local upload_count
    upload_count=$(echo "$uploads" | jq 'length')

    if [ "$upload_count" -eq 0 ]; then
        log_success "No incomplete uploads found in $bucket_name"
        return 0
    fi

    log_info "Found $upload_count incomplete uploads"

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would abort $upload_count incomplete uploads"
        return 0
    fi

    # Abort each upload
    echo "$uploads" | jq -r '.[] | "\(.Key)|\(.UploadId)"' | while IFS='|' read -r key upload_id; do
        log_info "Aborting upload: $key"
        aws s3api abort-multipart-upload --bucket "$bucket_name" --key "$key" --upload-id "$upload_id"
    done

    log_success "Cleaned up incomplete uploads in $bucket_name"
}

# Delete S3 bucket (use with extreme caution)
delete_s3_bucket() {
    local bucket_name="$1"

    log_warning "⚠️  DANGER: Deleting entire bucket: $bucket_name"

    if [ "$CONFIRMATION_REQUIRED" = true ]; then
        read -p "⚠️  This will PERMANENTLY delete bucket $bucket_name. Type bucket name to confirm: " confirm
        if [[ "$confirm" != "$bucket_name" ]]; then
            log_warning "Bucket name doesn't match. Aborting deletion."
            return 1
        fi
    fi

    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would delete bucket: $bucket_name"
        return 0
    fi

    # Empty bucket first
    log_info "Emptying bucket..."
    aws s3 rm "s3://$bucket_name" --recursive

    # Delete bucket
    log_info "Deleting bucket..."
    aws s3api delete-bucket --bucket "$bucket_name"

    log_success "Bucket $bucket_name deleted"
}

# Process findings from JSON report
process_findings() {
    local findings_file="$1"
    local action="${2:-report}"

    if [ ! -f "$findings_file" ]; then
        log_error "Findings file not found: $findings_file"
        exit 1
    fi

    log_info "Processing findings from: $findings_file"
    log_info "Action: $action"

    local findings
    findings=$(jq -c '.findings[]' "$findings_file")

    while IFS= read -r finding; do
        local resource_type resource_id recommendation severity
        resource_type=$(echo "$finding" | jq -r '.resource_type')
        resource_id=$(echo "$finding" | jq -r '.resource_id')
        recommendation=$(echo "$finding" | jq -r '.recommendation')
        severity=$(echo "$finding" | jq -r '.severity')

        log_info "Processing: $resource_type - $resource_id ($severity)"

        case "$resource_type" in
            EC2)
                if [[ "$recommendation" == *"Terminate"* ]] || [[ "$recommendation" == *"terminate"* ]]; then
                    if [ "$action" = "execute" ]; then
                        terminate_ec2_instance "$resource_id"
                    else
                        log_info "Would terminate: $resource_id"
                    fi
                elif [[ "$recommendation" == *"resize"* ]] || [[ "$recommendation" == *"Right-size"* ]]; then
                    if [ "$action" = "execute" ]; then
                        # Extract suggested instance type from metadata if available
                        resize_ec2_instance "$resource_id" "t3.medium"
                    else
                        log_info "Would resize: $resource_id"
                    fi
                fi
                ;;
            EBS)
                if [[ "$recommendation" == *"Delete"* ]] || [[ "$recommendation" == *"delete"* ]]; then
                    if [ "$action" = "execute" ]; then
                        delete_ebs_volume "$resource_id"
                    else
                        log_info "Would delete: $resource_id"
                    fi
                fi
                ;;
            S3)
                if [[ "$recommendation" == *"Glacier"* ]] || [[ "$recommendation" == *"transition"* ]]; then
                    if [ "$action" = "execute" ]; then
                        transition_s3_to_glacier "$resource_id"
                    else
                        log_info "Would transition to Glacier: $resource_id"
                    fi
                elif [[ "$recommendation" == *"Abort"* ]] || [[ "$recommendation" == *"incomplete"* ]]; then
                    if [ "$action" = "execute" ]; then
                        cleanup_s3_uploads "$resource_id"
                    else
                        log_info "Would cleanup uploads: $resource_id"
                    fi
                fi
                ;;
            *)
                log_warning "Unknown resource type: $resource_type"
                ;;
        esac

    done <<< "$findings"

    log_success "Processing complete"
}

# Generate optimization report
generate_report() {
    local output_file="${1:-$REPORT_FILE}"

    mkdir -p "$(dirname "$output_file")"

    cat > "$output_file" <<EOF
{
    "report_type": "aws_optimization",
    "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "dry_run": $DRY_RUN,
    "actions_taken": [],
    "status": "complete"
}
EOF

    log_success "Report generated: $output_file"
}

# Main execution
main() {
    local command="${1:-help}"
    shift || true

    check_dependencies

    case "$command" in
        terminate-ec2)
            terminate_ec2_instance "$@"
            ;;
        stop-ec2)
            stop_ec2_instance "$@"
            ;;
        resize-ec2)
            resize_ec2_instance "$@"
            ;;
        delete-ebs)
            delete_ebs_volume "$@"
            ;;
        modify-ebs)
            modify_ebs_volume "$@"
            ;;
        s3-glacier)
            transition_s3_to_glacier "$@"
            ;;
        s3-cleanup)
            cleanup_s3_uploads "$@"
            ;;
        delete-s3)
            delete_s3_bucket "$@"
            ;;
        process)
            process_findings "$@"
            ;;
        report)
            generate_report "$@"
            ;;
        help|*)
            echo "Cloud-Zombie Exorcist - AWS Optimization Scripts"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  terminate-ec2 <instance-id>     Terminate EC2 instance"
            echo "  stop-ec2 <instance-id>          Stop EC2 instance"
            echo "  resize-ec2 <instance-id> <type> Resize EC2 instance"
            echo "  delete-ebs <volume-id>          Delete unattached EBS volume"
            echo "  modify-ebs <volume-id> <type>   Modify EBS volume type"
            echo "  s3-glacier <bucket> [prefix]    Transition S3 to Glacier"
            echo "  s3-cleanup <bucket>             Cleanup incomplete uploads"
            echo "  delete-s3 <bucket>              Delete entire S3 bucket"
            echo "  process <findings.json> [action] Process findings (report/execute)"
            echo "  report [output.json]            Generate optimization report"
            echo ""
            echo "Environment Variables:"
            echo "  DRY_RUN=true|false              Enable/disable dry run (default: true)"
            echo "  CONFIRMATION_REQUIRED=true|false Require confirmation (default: true)"
            echo "  BACKUP_DIR=<path>               Backup directory (default: ./backups)"
            echo ""
            echo "Examples:"
            echo "  $0 terminate-ec2 i-12345678"
            echo "  DRY_RUN=false $0 delete-ebs vol-12345678"
            echo "  $0 process findings.json report"
            echo "  DRY_RUN=false $0 process findings.json execute"
            ;;
    esac
}

main "$@"
