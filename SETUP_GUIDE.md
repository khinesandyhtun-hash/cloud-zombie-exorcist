# 🚀 Cloud-Zombie Exorcist - Production Setup Guide

## Step 1: Configure AWS Credentials

### Option A: AWS CLI Configuration
```bash
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region name: us-east-1
# - Default output format: json
```

### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="YOUR_SECRET_KEY"
export AWS_REGION="us-east-1"
```

### Option C: IAM Role (for EC2/Lambda)
```bash
# If running on EC2, attach IAM role with these permissions:
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeVolumes",
                "ec2:StopInstances",
                "ec2:TerminateInstances",
                "ec2:ModifyInstanceAttribute",
                "ec2:DeleteVolume",
                "ec2:CreateSnapshot",
                "ec2:ModifyVolume",
                "s3:GetBucketLifecycle",
                "s3:PutBucketLifecycleConfiguration",
                "s3:ListMultipartUploads",
                "s3:AbortMultipartUpload"
            ],
            "Resource": "*"
        }
    ]
}
```

## Step 2: Configure Snowflake Credentials

### Option A: Environment Variables
```bash
export SNOWFLAKE_ACCOUNT="your-account-id"
export SNOWFLAKE_USER="your-username"
export SNOWFLAKE_PASSWORD="your-password"
export SNOWFLAKE_WAREHOUSE="ACCOUNTADMIN"
```

### Option B: Snowflake Config File
Create `~/.snowsql/config`:
```ini
[connections.cloud_zombie]
accountname = your-account-id
username = your-username
password = your-password
dbname = SNOWFLAKE
schemaname = INFORMATION_SCHEMA
warehouse = ACCOUNTADMIN
```

## Step 3: Test Live Data Connection

### Test AWS Connection
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Test EC2 access
aws ec2 describe-instances --max-items 5

# Test EBS access
aws ec2 describe-volumes --max-items 5

# Test S3 access
aws s3 ls
```

### Test Snowflake Connection
```bash
# Using snowsql
snowsql -a $SNOWFLAKE_ACCOUNT -u $SNOWFLAKE_USER -q "SHOW WAREHOUSES"

# Or test via Python
python3 -c "
import snowflake.connector
conn = snowflake.connector.connect(
    user='$SNOWFLAKE_USER',
    password='$SNOWFLAKE_PASSWORD',
    account='$SNOWFLAKE_ACCOUNT'
)
print(conn.cursor().execute('SELECT CURRENT_VERSION()').fetchone())
"
```

## Step 4: Run Live Analysis

### Full Live Scan
```bash
cd /root/Zay/agents/cloud-zombie-exorcist

# Run with live AWS data
python3 cloud_zombie_cli.py analyze --live

# Or use the run.sh menu
./run.sh
# Select option 3: Run with live AWS data
```

### Analyze Specific Resource Types
```bash
# Create data export from AWS
python3 -c "
import boto3
import json
from datetime import datetime, timedelta

ec2 = boto3.client('ec2')

# Export EC2 instances
instances = ec2.describe_instances()['Reservations']
ec2_data = []
for r in instances:
    for i in r['Instances']:
        ec2_data.append({
            'InstanceId': i['InstanceId'],
            'InstanceType': i['InstanceType'],
            'State': i['State']['Name'],
            'LaunchTime': str(i['LaunchTime'])
        })

with open('targets/live_ec2.json', 'w') as f:
    json.dump({'ec2_instances': ec2_data}, f, indent=2)

print(f'Exported {len(ec2_data)} instances')
"

# Analyze the exported data
python3 cloud_zombie_cli.py analyze targets/live_ec2.json
```

## Step 5: Schedule Automated Analysis

### Option A: Cron Job
```bash
# Edit crontab
crontab -e

# Add daily analysis at 6 AM
0 6 * * * cd /root/Zay/agents/cloud-zombie-exorcist && \
    /usr/bin/python3 cloud_zombie_cli.py analyze --live >> /var/log/cloud-zombie.log 2>&1
```

### Option B: Systemd Service
Create `/etc/systemd/system/cloud-zombie.service`:
```ini
[Unit]
Description=Cloud-Zombie Exorcist Daily Analysis
After=network.target

[Service]
Type=oneshot
User=root
WorkingDirectory=/root/Zay/agents/cloud-zombie-exorcist
Environment=TELEGRAM_BOT_TOKEN=YOUR_TOKEN
Environment=TELEGRAM_CHAT_IDS=YOUR_CHAT_ID
Environment=AWS_REGION=us-east-1
ExecStart=/usr/bin/python3 cloud_zombie_cli.py analyze --live
```

Create `/etc/systemd/system/cloud-zombie.timer`:
```ini
[Unit]
Description=Run Cloud-Zombie Analysis Daily
Requires=cloud-zombie.service

[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable the timer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cloud-zombie.timer
sudo systemctl start cloud-zombie.timer
```

## Step 6: Execute Optimizations Safely

### Phase 1: Dry-Run (Recommended First)
```bash
# Review what would happen
./reports/remediation_script.sh dry-run
```

### Phase 2: Execute Low-Risk Actions
```bash
# Start with S3 transitions and EBS snapshots
export DRY_RUN=false
./scripts/aws_optimizer.sh s3-glacier my-bucket
./scripts/aws_optimizer.sh s3-cleanup my-bucket
```

### Phase 3: Execute Medium-Risk Actions
```bash
# Stop zombie instances (can be restarted)
./scripts/aws_optimizer.sh stop-ec2 i-zombie123

# Delete unattached volumes (after snapshot)
./scripts/aws_optimizer.sh delete-ebs vol-orphan456
```

### Phase 4: Execute High-Risk Actions
```bash
# Terminate instances (REQUIRES CONFIRMATION)
export CONFIRMATION_REQUIRED=true
./scripts/aws_optimizer.sh terminate-ec2 i-zombie789

# Resize Snowflake warehouses
export SNOWFLAKE_ACCOUNT=xxx
export SNOWFLAKE_USER=xxx
./scripts/snowflake_optimizer.sh resize WH_IDLE X-SMALL
```

## Step 7: Monitor and Report

### View Latest Report
```bash
cat reports/report_$(ls -t reports/*.md | head -1 | xargs basename)
```

### Send Manual Telegram Update
```bash
python3 -c "
from core.telegram_bot import TelegramBot
bot = TelegramBot()
bot.send_message('📊 Weekly optimization summary:\\n\\n- Zombies eliminated: 5\\n- Savings achieved: \$1,234/month\\n- Commission earned: \$185/month')
"
```

### Generate Client Invoice
```bash
# Calculate commission from savings
python3 -c "
import json
with open('reports/findings_latest.json') as f:
    data = json.load(f)
    
savings = data['summary']['total_potential_savings_usd']
commission = savings * 0.15  # 15%

print(f'Monthly Savings: \${savings:,.2f}')
print(f'Your Commission (15%): \${commission:,.2f}')
print(f'Annual Commission: \${commission * 12:,.2f}')
"
```

## Step 8: GitHub Actions Automation

### Enable GitHub Actions
1. Go to your repository on GitHub
2. Click **Settings** → **Actions** → **General**
3. Enable Actions

### Add Repository Secrets
```
TELEGRAM_BOT_TOKEN     → 8596689578:AAHXbFWpSEPi9QcoV5RUuSl_EpcTRnH-M-Q
TELEGRAM_CHAT_IDS      → 1707504118
AWS_ACCESS_KEY_ID      → YOUR_KEY
AWS_SECRET_ACCESS_KEY  → YOUR_SECRET
AWS_REGION             → us-east-1
SNOWFLAKE_ACCOUNT      → your-account
SNOWFLAKE_USER         → your-user
SNOWFLAKE_PASSWORD     → your-password
```

### Trigger Manual Analysis
1. Go to **Actions** tab
2. Select **Cloud-Zombie Analysis**
3. Click **Run workflow**
4. Choose action: `analyze` or `optimize`
5. Set dry_run: `true` (recommended first)

## Troubleshooting

### AWS Permission Denied
```bash
# Check IAM permissions
aws iam get-user
aws sts get-caller-identity

# Test specific permission
aws ec2 describe-instances --region us-east-1
```

### Snowflake Connection Failed
```bash
# Test connection
snowsql -- diagnose

# Check account format (should be like: abc12345.us-east-1)
echo $SNOWFLAKE_ACCOUNT
```

### Telegram Bot Not Sending
```bash
# Test bot API
curl "https://api.telegram.org/botYOUR_TOKEN/getMe"

# Check chat ID
python3 -c "from core.telegram_bot import TelegramBot; print(TelegramBot().test_connection())"
```

## Best Practices

1. **Always start with dry-run** - Never execute without testing first
2. **Backup before delete** - Scripts create snapshots automatically
3. **Stage optimizations** - Start with low-risk actions
4. **Monitor after changes** - Watch for application impact
5. **Document everything** - Keep audit logs for compliance
6. **Client communication** - Send reports before and after

## Commission Tracking Template

```markdown
# Client Optimization Report

## Before Optimization
- Monthly Spend: \$X,XXX.XX
- Resource Count: XXX

## After Optimization  
- Monthly Spend: \$X,XXX.XX
- Resource Count: XXX
- Savings: \$X,XXX.XX/month

## Commission (15%)
- Monthly: \$XXX.XX
- Annual: \$X,XXX.XX

## Actions Taken
- Terminated: X zombie instances
- Resized: X oversized instances
- Deleted: X unattached volumes
- Transitioned: X S3 buckets to Glacier
- Suspended: X idle warehouses
```

---

**Ready to go live!** 🚀

Run `./run.sh` and select option 3 for live AWS analysis.
