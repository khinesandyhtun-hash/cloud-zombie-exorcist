# 🧟 Cloud-Zombie Exorcist - Quick Reference

## One-Liner Commands

```bash
# Quick start - analyze sample data
./run.sh analyze

# Interactive mode
./run.sh interactive

# Analyze custom data
python3 cloud_zombie_cli.py analyze my_cloud_data.json

# Check status
python3 cloud_zombie_cli.py status
```

## Environment Setup

```bash
# Required
export TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
export TELEGRAM_CHAT_IDS="YOUR_CHAT_ID"

# Optional (for live AWS analysis)
export AWS_ACCESS_KEY_ID="YOUR_KEY"
export AWS_SECRET_ACCESS_KEY="YOUR_SECRET"
export AWS_REGION="us-east-1"

# Optional (for Snowflake)
export SNOWFLAKE_ACCOUNT="your-account"
export SNOWFLAKE_USER="your-user"
export SNOWFLAKE_PASSWORD="your-password"
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `analyze <files...>` | Analyze cloud data files |
| `analyze --live` | Fetch and analyze live cloud data |
| `optimize <file>` | Process optimizations (dry-run) |
| `optimize <file> --execute` | Execute optimizations (LIVE) |
| `status` | Show system status |
| `interactive` | Interactive CLI mode |

## Telegram Bot

- **Bot**: @ShuoOpu_Bot
- **Commands**: `/start`, `/help`, `/analyze`, `/optimize`, `/status`, `/report`

## Optimization Thresholds

| Resource | Threshold | Action |
|----------|-----------|--------|
| EC2 CPU | < 10% | Terminate/Resize |
| EBS Unattached | > 7 days | Delete |
| Snowflake Idle | < 10 hrs/month | Suspend |
| S3 Cold Storage | > 90 days no access | Glacier |

## Commission Calculator

```
Monthly Savings × 15% = Your Commission

Example:
$10,000/month savings → $1,500/month commission
$50,000/month savings → $7,500/month commission
```

## File Locations

```
/root/Zay/agents/cloud-zombie-exorcist/
├── reports/           # Generated reports
├── targets/           # Input data files
├── core/              # Python modules
├── scripts/           # Bash optimization scripts
└── workflows/         # GitHub Actions
```

## Troubleshooting

```bash
# Test Python modules
python3 -c "from core.finops_analyzer import FinOpsAnalyzer; print('OK')"

# Test Telegram
python3 -c "from core.telegram_bot import TelegramBot; print(TelegramBot().test_connection())"

# Test AWS CLI
aws sts get-caller-identity

# View logs
tail -f reports/*.json
```
