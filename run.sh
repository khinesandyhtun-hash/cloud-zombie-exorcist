#!/bin/bash
#
# Cloud-Zombie Exorcist - Quick Launch Script
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║     🧟  Cloud-Zombie Exorcist - FinOps Service          ║"
    echo "║          Identify & Eliminate Cloud Waste                ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is required but not installed${NC}"
        exit 1
    fi
}

install_deps() {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    python3 -m pip install -q -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

show_menu() {
    echo ""
    echo "Select an action:"
    echo "  1) Analyze sample data"
    echo "  2) Analyze custom data file"
    echo "  3) Run with live AWS data (requires credentials)"
    echo "  4) Process optimizations (dry-run)"
    echo "  5) Execute optimizations (LIVE)"
    echo "  6) Interactive mode"
    echo "  7) System status"
    echo "  8) Test Telegram bot"
    echo "  9) View reports"
    echo "  0) Exit"
    echo ""
}

analyze_sample() {
    echo -e "${BLUE}Analyzing sample cloud data...${NC}"
    python3 cloud_zombie_cli.py analyze targets/sample_cloud_data.json
}

analyze_custom() {
    read -p "Enter path to data file: " filepath
    if [ -f "$filepath" ]; then
        python3 cloud_zombie_cli.py analyze "$filepath"
    else
        echo -e "${RED}File not found: $filepath${NC}"
    fi
}

analyze_live() {
    echo -e "${YELLOW}Checking AWS credentials...${NC}"
    if aws sts get-caller-identity &>/dev/null; then
        echo -e "${GREEN}✓ AWS credentials valid${NC}"
        python3 cloud_zombie_cli.py analyze --live
    else
        echo -e "${RED}AWS credentials not configured. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY${NC}"
    fi
}

process_optimizations() {
    local latest_report
    latest_report=$(ls -t reports/*.json 2>/dev/null | head -1)

    if [ -z "$latest_report" ]; then
        echo -e "${RED}No findings report found. Run analysis first.${NC}"
        return
    fi

    echo -e "${BLUE}Processing optimizations from: $latest_report${NC}"
    echo -e "${YELLOW}Mode: DRY-RUN (no changes will be made)${NC}"
    python3 cloud_zombie_cli.py optimize "$latest_report"
}

execute_optimizations() {
    local latest_report
    latest_report=$(ls -t reports/*.json 2>/dev/null | head -1)

    if [ -z "$latest_report" ]; then
        echo -e "${RED}No findings report found. Run analysis first.${NC}"
        return
    fi

    echo -e "${RED}⚠️  WARNING: This will make REAL changes to your infrastructure!${NC}"
    read -p "Type 'CONFIRM' to proceed: " confirm
    if [ "$confirm" != "CONFIRM" ]; then
        echo -e "${YELLOW}Aborted${NC}"
        return
    fi

    echo -e "${RED}Executing optimizations from: $latest_report${NC}"
    python3 cloud_zombie_cli.py optimize "$latest_report" --execute
}

interactive_mode() {
    python3 cloud_zombie_cli.py interactive
}

show_status() {
    python3 cloud_zombie_cli.py status
}

test_telegram() {
    if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
        echo -e "${BLUE}Testing Telegram bot...${NC}"
        python3 core/telegram_bot.py "$TELEGRAM_BOT_TOKEN"
    else
        echo -e "${RED}TELEGRAM_BOT_TOKEN not set${NC}"
    fi
}

view_reports() {
    echo ""
    echo "Available reports:"
    ls -lah reports/ 2>/dev/null || echo "No reports yet"
    echo ""

    local latest_md
    latest_md=$(ls -t reports/*.md 2>/dev/null | head -1)
    if [ -n "$latest_md" ]; then
        echo -e "${BLUE}Latest report preview:${NC}"
        head -30 "$latest_md"
    fi
}

# Main
print_banner
check_python

# Install deps if needed
if [ ! -d ".venv" ] && [ "${1:-}" != "--skip-deps" ]; then
    if [ -f "requirements.txt" ]; then
        install_deps
    fi
fi

# Handle command line args
if [ $# -gt 0 ]; then
    case "$1" in
        analyze)
            analyze_sample
            exit 0
            ;;
        interactive)
            interactive_mode
            exit 0
            ;;
        status)
            show_status
            exit 0
            ;;
        *)
            echo "Unknown command: $1"
            exit 1
            ;;
    esac
fi

# Interactive menu
while true; do
    show_menu
    read -p "Enter choice [0-9]: " choice

    case $choice in
        1) analyze_sample ;;
        2) analyze_custom ;;
        3) analyze_live ;;
        4) process_optimizations ;;
        5) execute_optimizations ;;
        6) interactive_mode ;;
        7) show_status ;;
        8) test_telegram ;;
        9) view_reports ;;
        0)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
done
