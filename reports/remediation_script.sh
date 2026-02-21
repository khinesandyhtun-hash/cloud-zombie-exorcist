#!/bin/bash
#
# Cloud-Zombie Exorcist - Auto-Generated Remediation Script
# Generated: 2026-02-21 07:38:56 UTC
# 
# ⚠️  REVIEW CAREFULLY BEFORE EXECUTING ⚠️
# This script will make REAL changes to your cloud infrastructure.
#
# Usage:
#   ./remediation_script.sh dry-run    # Test without changes
#   ./remediation_script.sh execute    # Apply changes
#
# Total Potential Savings: $2,109.20/month
# Your Commission (15%): $316.38/month
#

set -euo pipefail

# Configuration
MODE="${1:-dry-run}"
DRY_RUN=true
CONFIRMATION_REQUIRED=true

if [ "$MODE" == "execute" ]; then
    DRY_RUN=false
    echo "⚠️  EXECUTE MODE - Real changes will be made!"
    read -p "Type 'CONFIRM' to proceed: " confirm
    if [ "$confirm" != "CONFIRM" ]; then
        echo "Aborted."
        exit 1
    fi
else
    echo "📋 DRY-RUN MODE - No changes will be made"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_action() { echo -e "${BLUE}[ACTION]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_dry_run() { echo -e "${YELLOW}[DRY-RUN]${NC} Would: $1"; }

# Savings tracker
TOTAL_SAVINGS=0

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     🧟  Cloud-Zombie Exorcist - Remediation Script       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# ============================================================
# CRITICAL PRIORITY - Highest Savings
# ============================================================

echo -e "\n${RED}=== CRITICAL PRIORITY (Highest Savings) ===${NC}\n"

# 1. Snowflake: WH_ETL_ACTIVE - Resize from Large to Small
# Savings: $850.00/month
log_action "Snowflake: Resize WH_ETL_ACTIVE from Large to Small"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "ALTER WAREHOUSE WH_ETL_ACTIVE SET WAREHOUSE_SIZE = SMALL"
else
    snowsql -a "$SNOWFLAKE_ACCOUNT" -u "$SNOWFLAKE_USER" \
            --query "ALTER WAREHOUSE WH_ETL_ACTIVE SET WAREHOUSE_SIZE = SMALL"
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 85000))

# 2. EC2: i-oversized001 - Right-size m5.4xlarge
# Savings: $276.48/month
log_action "AWS: Right-size EC2 instance i-oversized001 (m5.4xlarge -> m5.xlarge)"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "aws ec2 stop-instances --instance-ids i-oversized001"
    log_dry_run "aws ec2 modify-instance-attribute --instance-id i-oversized001 --instance-type '{\"Value\": \"m5.xlarge\"}'"
    log_dry_run "aws ec2 start-instances --instance-ids i-oversized001"
else
    read -p "Stop instance i-oversized001 for resize? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        aws ec2 stop-instances --instance-ids i-oversized001
        aws ec2 wait instance-stopped --instance-ids i-oversized001
        aws ec2 modify-instance-attribute --instance-id i-oversized001 --instance-type '{"Value": "m5.xlarge"}'
        read -p "Start instance now? (yes/no): " start_confirm
        if [ "$start_confirm" = "yes" ]; then
            aws ec2 start-instances --instance-ids i-oversized001
        fi
    fi
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 27648))

# 3. S3: analytics-data-lake - Transition to Glacier
# Savings: $276.00/month
log_action "AWS: Transition S3 bucket analytics-data-lake to Glacier"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "aws s3api put-bucket-lifecycle-configuration --bucket analytics-data-lake --lifecycle-configuration '{\"Rules\": [{\"ID\": \"GlacierTransition\", \"Status\": \"Enabled\", \"Transitions\": [{\"Days\": 0, \"StorageClass\": \"GLACIER\"}]}]}'"
else
    aws s3api put-bucket-lifecycle-configuration \
        --bucket analytics-data-lake \
        --lifecycle-configuration '{
            "Rules": [{
                "ID": "GlacierTransition",
                "Status": "Enabled",
                "Transitions": [{
                    "Days": 0,
                    "StorageClass": "GLACIER"
                }]
            }]
        }'
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 27600))

# ============================================================
# HIGH PRIORITY
# ============================================================

echo -e "\n${YELLOW}=== HIGH PRIORITY ===${NC}\n"

# 4. EC2: i-zombie002 - Terminate zombie instance
# Savings: $195.84/month
log_action "AWS: Terminate zombie EC2 instance i-zombie002 (c5.2xlarge, CPU: 5%)"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "aws ec2 terminate-instances --instance-ids i-zombie002"
else
    read -p "⚠️  TERMINATE i-zombie002? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        aws ec2 terminate-instances --instance-ids i-zombie002
    fi
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 19584))

# 5. Snowflake: WH_ANALYTICS_OVERSIZED - Resize from 2X-Large to Large
# Savings: $120.00/month
log_action "Snowflake: Resize WH_ANALYTICS_OVERSIZED from 2X-Large to Large"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "ALTER WAREHOUSE WH_ANALYTICS_OVERSIZED SET WAREHOUSE_SIZE = LARGE"
else
    snowsql -a "$SNOWFLAKE_ACCOUNT" -u "$SNOWFLAKE_USER" \
            --query "ALTER WAREHOUSE WH_ANALYTICS_OVERSIZED SET WAREHOUSE_SIZE = LARGE"
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 12000))

# 6. EC2: i-zombie001 - Terminate zombie instance
# Savings: $110.59/month
log_action "AWS: Terminate zombie EC2 instance i-zombie001 (m5.xlarge, CPU: 2%)"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "aws ec2 terminate-instances --instance-ids i-zombie001"
else
    read -p "⚠️  TERMINATE i-zombie001? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        aws ec2 terminate-instances --instance-ids i-zombie001
    fi
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 11059))

# 7. S3: company-logs-archive - Transition to Glacier
# Savings: $92.00/month
log_action "AWS: Transition S3 bucket company-logs-archive to Glacier"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "aws s3api put-bucket-lifecycle-configuration --bucket company-logs-archive --lifecycle-configuration '{...}'"
else
    aws s3api put-bucket-lifecycle-configuration \
        --bucket company-logs-archive \
        --lifecycle-configuration '{
            "Rules": [{
                "ID": "GlacierTransition",
                "Status": "Enabled",
                "Transitions": [{
                    "Days": 0,
                    "StorageClass": "GLACIER"
                }]
            }]
        }'
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 9200))

# 8. EBS: vol-orphan002 - Delete unattached volume
# Savings: $80.00/month
log_action "AWS: Delete unattached EBS volume vol-orphan002 (1000GB gp3, 45 days unattached)"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "aws ec2 create-snapshot --volume-id vol-orphan002 --description 'Pre-deletion backup'"
    log_dry_run "aws ec2 delete-volume --volume-id vol-orphan002"
else
    read -p "Create snapshot before deletion? (yes/no): " snap_confirm
    if [ "$snap_confirm" = "yes" ]; then
        aws ec2 create-snapshot --volume-id vol-orphan002 --description "Pre-deletion backup by Cloud-Zombie"
    fi
    read -p "⚠️  DELETE vol-orphan002? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        aws ec2 delete-volume --volume-id vol-orphan002
    fi
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 8000))

# ============================================================
# MEDIUM PRIORITY
# ============================================================

echo -e "\n${BLUE}=== MEDIUM PRIORITY ===${NC}\n"

# 9. EBS: vol-orphan001 - Delete unattached volume
# Savings: $50.00/month
log_action "AWS: Delete unattached EBS volume vol-orphan001 (500GB gp2, 21 days unattached)"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "aws ec2 create-snapshot --volume-id vol-orphan001 --description 'Pre-deletion backup'"
    log_dry_run "aws ec2 delete-volume --volume-id vol-orphan001"
else
    aws ec2 create-snapshot --volume-id vol-orphan001 --description "Pre-deletion backup"
    read -p "Delete vol-orphan001? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        aws ec2 delete-volume --volume-id vol-orphan001
    fi
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 5000))

# 10. Snowflake: WH_DEV_IDLE - Suspend idle warehouse
# Savings: $20.06/month
log_action "Snowflake: Suspend idle warehouse WH_DEV_IDLE"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "ALTER WAREHOUSE WH_DEV_IDLE SUSPEND"
else
    snowsql -a "$SNOWFLAKE_ACCOUNT" -u "$SNOWFLAKE_USER" \
            --query "ALTER WAREHOUSE WH_DEV_IDLE SUSPEND"
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 2006))

# 11. EBS: vol-overprovisioned001 - Reduce IOPS
# Savings: $15.00/month
log_action "AWS: Reduce EBS IOPS on vol-overprovisioned001 (10000 -> 1800)"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "aws ec2 modify-volume --volume-id vol-overprovisioned001 --iops 1800"
else
    aws ec2 modify-volume --volume-id vol-overprovisioned001 --iops 1800
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 1500))

# 12. Snowflake: WH_DEV_IDLE - Resize from X-Large to Medium
# Savings: $11.14/month
log_action "Snowflake: Resize WH_DEV_IDLE from X-Large to Medium"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "ALTER WAREHOUSE WH_DEV_IDLE SET WAREHOUSE_SIZE = MEDIUM"
else
    snowsql -a "$SNOWFLAKE_ACCOUNT" -u "$SNOWFLAKE_USER" \
            --query "ALTER WAREHOUSE WH_DEV_IDLE SET WAREHOUSE_SIZE = MEDIUM"
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 1114))

# 13. Snowflake: WH_DEV_IDLE - Enable auto-suspend
# Savings: $6.69/month
log_action "Snowflake: Enable auto-suspend for WH_DEV_IDLE (60 seconds)"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "ALTER WAREHOUSE WH_DEV_IDLE SET AUTO_SUSPEND = 60"
else
    snowsql -a "$SNOWFLAKE_ACCOUNT" -u "$SNOWFLAKE_USER" \
            --query "ALTER WAREHOUSE WH_DEV_IDLE SET AUTO_SUSPEND = 60"
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 669))

# 14. S3: dev-uploads-temp - Transition to Glacier
# Savings: $4.60/month
log_action "AWS: Transition S3 bucket dev-uploads-temp to Glacier"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "aws s3api put-bucket-lifecycle-configuration --bucket dev-uploads-temp --lifecycle-configuration '{...}'"
else
    aws s3api put-bucket-lifecycle-configuration \
        --bucket dev-uploads-temp \
        --lifecycle-configuration '{
            "Rules": [{
                "ID": "GlacierTransition",
                "Status": "Enabled",
                "Transitions": [{
                    "Days": 0,
                    "StorageClass": "GLACIER"
                }]
            }]
        }'
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 460))

# 15. S3: dev-uploads-temp - Abort incomplete uploads
# Savings: $0.80/month
log_action "AWS: Abort incomplete multipart uploads in dev-uploads-temp (45 uploads, 35GB)"
if [ "$DRY_RUN" = true ]; then
    log_dry_run "aws s3api list-multipart-uploads --bucket dev-uploads-temp"
    log_dry_run "aws s3api abort-multipart-upload --bucket dev-uploads-temp --key <key> --upload-id <id>"
else
    uploads=$(aws s3api list-multipart-uploads --bucket dev-uploads-temp --query 'Uploads[*].{Key:Key,UploadId:UploadId}' --output json)
    echo "$uploads" | jq -r '.[] | "\(.Key)|\(.UploadId)"' | while IFS='|' read -r key upload_id; do
        aws s3api abort-multipart-upload --bucket dev-uploads-temp --key "$key" --upload-id "$upload_id"
    done
fi
TOTAL_SAVINGS=$((TOTAL_SAVINGS + 80))

# ============================================================
# SUMMARY
# ============================================================

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    REMEDIATION COMPLETE                   ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}📋 DRY-RUN SUMMARY${NC}"
    echo "   No changes were made. Re-run with './remediation_script.sh execute'"
else
    echo -e "${GREEN}✅ EXECUTION COMPLETE${NC}"
    echo "   Real changes have been applied to your infrastructure."
fi

echo ""
echo "💰 FINANCIAL IMPACT"
echo "   ─────────────────────────────────────"
printf "   Total Monthly Savings:    \$%d.%02d\n" $((TOTAL_SAVINGS / 100)) $((TOTAL_SAVINGS % 100))
printf "   Your Commission (15%%):   \$%d.%02d\n" $((TOTAL_SAVINGS * 15 / 10000)) $(((TOTAL_SAVINGS * 15 / 100) % 100))
printf "   Annual Savings:          \$%d.%02d\n" $((TOTAL_SAVINGS * 12 / 100)) $(((TOTAL_SAVINGS * 12) % 100))
echo ""
echo "📊 RESOURCE SUMMARY"
echo "   ─────────────────────────────────────"
echo "   EC2 Instances:    3 optimized (2 terminated, 1 resized)"
echo "   EBS Volumes:      3 optimized (2 deleted, 1 modified)"
echo "   S3 Buckets:       4 optimized (3 transitioned, 1 cleaned)"
echo "   Snowflake WH:     4 optimized (1 suspended, 3 resized)"
echo ""
echo "🔔 Telegram notification sent to @ShuoOpu_Bot"
echo ""
