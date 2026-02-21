# 🧟 Cloud-Zombie Exorcist

**FinOps Cost Optimization Service for Cloud Infrastructure**

A comprehensive agent that identifies and eliminates cloud waste (zombie resources) across AWS and Snowflake, with automated Telegram notifications and GitHub Actions integration.

---

## 🎯 Value Proposition

- **Identify Waste**: Find underutilized EC2 instances, unattached EBS volumes, idle Snowflake warehouses
- **Automated Reports**: Daily/weekly optimization reports via Telegram
- **Safe Execution**: Dry-run mode with confirmation before any changes
- **Commission Model**: Optimize client infrastructure, earn 10-20% of savings

---

## 📁 Project Structure

```
cloud-zombie-exorcist/
├── core/
│   ├── finops_analyzer.py    # FinOps analysis engine
│   └── telegram_bot.py       # Telegram integration
├── scripts/
│   ├── aws_optimizer.sh      # AWS optimization scripts
│   └── snowflake_optimizer.sh # Snowflake optimization scripts
├── workflows/
│   └── cloud-zombie-analysis.yml  # GitHub Actions workflow
├── config/
│   └── config.example.json   # Configuration template
├── reports/                  # Generated reports
├── tests/                    # Unit tests
├── cloud_zombie_cli.py       # Main CLI orchestrator
└── README.md                 # This file
```

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or navigate to the agent directory
cd /root/Zay/agents/cloud-zombie-exorcist

# Install Python dependencies
pip install requests boto3 snowflake-connector-python

# Make scripts executable
chmod +x scripts/*.sh
```

### 2. Configuration

Create a configuration file:

```bash
cp config/config.example.json config/config.json
```

Edit `config/config.json`:

```json
{
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_ids": ["YOUR_CHAT_ID"]
  },
  "aws": {
    "region": "us-east-1"
  },
  "snowflake": {
    "account": "your-account",
    "user": "your-username"
  },
  "reports_dir": "./reports",
  "dry_run": true,
  "auto_notify": true
}
```

### 3. Set Environment Variables

```bash
export TELEGRAM_BOT_TOKEN="8596689578:AAHXbFWpSEPi9QcoV5RUuSl_EpcTRnH-M-Q"
export TELEGRAM_CHAT_IDS="1707504118"
export AWS_REGION="us-east-1"
export DRY_RUN="true"
```

### 4. Run Analysis

```bash
# Analyze data files
python cloud_zombie_cli.py analyze targets/sample_data.json

# Analyze with live cloud data (requires AWS credentials)
python cloud_zombie_cli.py analyze --live

# Interactive mode
python cloud_zombie_cli.py interactive
```

---

## 📊 Features

### FinOps Analysis Engine

| Resource Type | Detection | Action |
|--------------|-----------|--------|
| EC2 Instances | CPU < 10%, Network < 1KB | Terminate/Resize |
| EBS Volumes | Unattached > 7 days | Delete/Snapshot |
| Snowflake Warehouses | Idle > 24hrs, Low credit usage | Suspend/Resize |
| S3 Storage | No access > 90 days | Transition to Glacier |

### Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show help |
| `/analyze` | Trigger analysis |
| `/optimize` | Execute optimizations |
| `/status` | System status |
| `/report` | Generate report |

### Optimization Scripts

**AWS Scripts:**
```bash
# Dry-run (default)
./scripts/aws_optimizer.sh terminate-ec2 i-12345678

# Execute with confirmation
DRY_RUN=false ./scripts/aws_optimizer.sh delete-ebs vol-12345678

# Process findings from analysis
./scripts/aws_optimizer.sh process reports/findings.json report
DRY_RUN=false ./scripts/aws_optimizer.sh process reports/findings.json execute
```

**Snowflake Scripts:**
```bash
# Set credentials
export SNOWFLAKE_ACCOUNT="your-account"
export SNOWFLAKE_USER="your-user"

# Suspend idle warehouse
./scripts/snowflake_optimizer.sh suspend WH_IDLE

# Resize oversized warehouse
./scripts/snowflake_optimizer.sh resize WH_LARGE X-SMALL

# Process findings
./scripts/snowflake_optimizer.sh process reports/findings.json report
```

---

## 🔧 GitHub Actions Integration

### Setup Secrets

In your GitHub repository, add these secrets:

```
TELEGRAM_BOT_TOKEN     -> Your Telegram bot token
TELEGRAM_CHAT_IDS      -> Comma-separated chat IDs
AWS_ACCESS_KEY_ID      -> AWS access key
AWS_SECRET_ACCESS_KEY  -> AWS secret key
AWS_REGION             -> AWS region
SNOWFLAKE_ACCOUNT      -> Snowflake account
SNOWFLAKE_USER         -> Snowflake username
SNOWFLAKE_PASSWORD     -> Snowflake password
```

### Scheduled Analysis

The workflow runs:
- **Daily at 6 AM UTC** - Automated analysis and report
- **On push** to `targets/*.json` or `targets/*.csv`
- **Manual trigger** via workflow_dispatch

---

## 📈 Business Model

### Commission Structure

| Monthly Savings | Your Commission (15%) |
|----------------|----------------------|
| $10,000        | $1,500/month         |
| $50,000        | $7,500/month         |
| $100,000       | $15,000/month        |
| $500,000       | $75,000/month        |

### Service Tiers

1. **Basic** - Analysis only (reports via Telegram)
2. **Standard** - Analysis + Safe optimizations (stop instances, snapshot volumes)
3. **Premium** - Full optimization + Continuous monitoring

---

## 📝 Sample Data Format

### EC2 Instances (JSON)

```json
{
  "ec2_instances": [
    {
      "InstanceId": "i-zombie123",
      "InstanceType": "m5.xlarge",
      "AverageCPU": 0.02,
      "AverageNetworkIn": 500,
      "DaysRunning": 45,
      "HourlyCost": 0.192
    }
  ]
}
```

### Snowflake Warehouses (JSON)

```json
{
  "snowflake_warehouses": [
    {
      "name": "WH_IDLE",
      "size": "X-Large",
      "state": "RUNNING",
      "credits_used": 5.2,
      "query_count": 2,
      "hours_active": 3,
      "analysis_period_days": 14
    }
  ]
}
```

---

## 🔐 Security Best Practices

1. **Never commit credentials** - Use environment variables or secrets
2. **Dry-run by default** - Always test before executing
3. **Backup before delete** - Scripts create snapshots automatically
4. **Confirmation required** - Critical actions need explicit approval
5. **Audit logging** - All actions are logged for compliance

---

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/

# Test Telegram bot
python core/telegram_bot.py YOUR_BOT_TOKEN

# Test analyzer with sample data
python core/finops_analyzer.py
```

---

## 📞 Telegram Bot Info

- **Bot Username**: @ShuoOpu_Bot
- **Bot ID**: 1707504118
- **Token**: Store securely in environment/secrets

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Credits

Created for ethical FinOps cost optimization services.

**Remember**: Always operate within cloud provider terms of service and with proper authorization from infrastructure owners.
