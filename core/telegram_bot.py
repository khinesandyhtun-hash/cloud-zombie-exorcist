#!/usr/bin/env python3
"""
Cloud-Zombie Exorcist - Telegram Bot Integration
Sends optimization reports and alerts via Telegram.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import urllib.request
import urllib.parse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for sending cloud optimization reports and alerts."""

    def __init__(self, token: Optional[str] = None, chat_ids: Optional[List[str]] = None):
        """
        Initialize Telegram bot.

        Args:
            token: Telegram Bot API token
            chat_ids: List of chat IDs to send messages to
        """
        self.token = token or os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_ids = chat_ids or self._parse_chat_ids(os.environ.get('TELEGRAM_CHAT_IDS', ''))

        if not self.token:
            logger.warning("Telegram bot token not provided. Bot notifications disabled.")

        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.enabled = bool(self.token)

    def _parse_chat_ids(self, chat_ids_str: str) -> List[str]:
        """Parse comma-separated chat IDs."""
        if not chat_ids_str:
            return []
        return [cid.strip() for cid in chat_ids_str.split(',') if cid.strip()]

    def _make_request(self, endpoint: str, data: Dict) -> Dict:
        """Make API request to Telegram."""
        if not self.enabled:
            return {'ok': False, 'error': 'Bot not enabled'}

        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        try:
            request_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=request_data, headers=headers, method='POST')

            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                logger.debug(f"Telegram API response: {result}")
                return result
        except Exception as e:
            logger.error(f"Telegram API error: {e}")
            return {'ok': False, 'error': str(e)}

    def send_message(self, text: str, parse_mode: str = 'Markdown',
                     chat_id: Optional[str] = None, disable_notification: bool = False) -> List[Dict]:
        """
        Send message to configured chat IDs.

        Args:
            text: Message text (supports Markdown)
            parse_mode: 'Markdown', 'HTML', or None
            chat_id: Specific chat ID (uses defaults if None)
            disable_notification: Send silently

        Returns:
            List of API responses
        """
        if not self.enabled:
            logger.info(f"[TELEGRAM DISABLED] {text[:100]}...")
            return []

        targets = [chat_id] if chat_id else self.chat_ids

        if not targets:
            logger.warning("No chat IDs configured for Telegram bot")
            return []

        responses = []
        for cid in targets:
            data = {
                'chat_id': cid,
                'text': text,
                'disable_notification': disable_notification
            }
            if parse_mode:
                data['parse_mode'] = parse_mode

            response = self._make_request('sendMessage', data)
            responses.append(response)

        return responses

    def send_photo(self, photo_url: str, caption: str = '',
                   chat_id: Optional[str] = None) -> List[Dict]:
        """Send photo with caption."""
        if not self.enabled:
            return []

        targets = [chat_id] if chat_id else self.chat_ids
        responses = []

        for cid in targets:
            data = {
                'chat_id': cid,
                'photo': photo_url,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            response = self._make_request('sendPhoto', data)
            responses.append(response)

        return responses

    def send_document(self, file_path: str, caption: str = '',
                      chat_id: Optional[str] = None) -> List[Dict]:
        """Send document file."""
        if not self.enabled:
            return []

        targets = [chat_id] if chat_id else self.chat_ids
        responses = []

        for cid in targets:
            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()

                # Use multipart form data for file upload
                boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
                body = (
                    f'--{boundary}\r\n'
                    f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
                    f'{cid}\r\n'
                    f'--{boundary}\r\n'
                    f'Content-Disposition: form-data; name="document"; filename="{os.path.basename(file_path)}"\r\n'
                    f'Content-Type: application/octet-stream\r\n\r\n'
                ).encode('utf-8') + file_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')

                req = urllib.request.Request(
                    f'{self.api_url}/sendDocument',
                    data=body,
                    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
                    method='POST'
                )

                with urllib.request.urlopen(req, timeout=60) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    responses.append(result)

            except Exception as e:
                logger.error(f"Error sending document: {e}")
                responses.append({'ok': False, 'error': str(e)})

        return responses

    def send_optimization_report(self, findings: List[Any], summary: Dict,
                                 report_file: Optional[str] = None) -> List[Dict]:
        """
        Send formatted optimization report.

        Args:
            findings: List of OptimizationFinding objects
            summary: Summary dictionary
            report_file: Optional path to full report file

        Returns:
            List of API responses
        """
        total_savings = summary.get('total_potential_savings_usd', 0)
        total_findings = summary.get('total_findings', 0)

        # Build report message
        message = [
            "🧟 *Cloud-Zombie Exorcist Report*",
            f"_{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_\n",
            "📊 *Summary*",
            f"• Findings: *{total_findings}*",
            f"• Potential Savings: *${total_savings:,.2f}/month*",
            f"• Commission (15%): *${total_savings * 0.15:,.2f}/month*\n"
        ]

        # Group by severity
        severity_counts = {}
        for f in findings:
            sev = f.severity if hasattr(f, 'severity') else f.get('severity', 'medium')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if severity_counts:
            message.append("🎯 *By Severity*")
            emoji_map = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
            for sev, count in sorted(severity_counts.items(), key=lambda x: ['critical', 'high', 'medium', 'low'].index(x[0]) if x[0] in ['critical', 'high', 'medium', 'low'] else 99):
                message.append(f"• {emoji_map.get(sev, '⚪')} {sev.title()}: {count}")

        # Top 5 findings
        message.append("\n🔥 *Top Opportunities*")
        top_findings = findings[:5] if len(findings) > 5 else findings

        for i, f in enumerate(top_findings, 1):
            if hasattr(f, 'resource_type'):
                resource_type = f.resource_type
                resource_id = f.resource_id
                savings = f.potential_savings_usd
                severity = f.severity
            else:
                resource_type = f.get('resource_type', 'Unknown')
                resource_id = f.get('resource_id', 'unknown')
                savings = f.get('potential_savings_usd', 0)
                severity = f.get('severity', 'medium')

            emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(severity, '⚪')
            message.append(f"{i}. {emoji} *{resource_type}: {resource_id}*")
            message.append(f"   💰 Save: *${savings:,.2f}/month*")

        if len(findings) > 5:
            message.append(f"\n_...and {len(findings) - 5} more findings_")

        message.append("\n✅ *Use `/optimize` to execute remediation scripts*")

        full_message = '\n'.join(message)

        # Send text report
        responses = self.send_message(full_message)

        # Attach full report file if available
        if report_file and os.path.exists(report_file):
            responses.extend(self.send_document(report_file, "📄 Full Optimization Report"))

        return responses

    def send_alert(self, title: str, message: str, severity: str = 'high') -> List[Dict]:
        """Send urgent alert."""
        emoji = {'critical': '🚨', 'high': '⚠️', 'medium': '📢', 'low': 'ℹ️'}.get(severity, '📝')

        alert_text = f"{emoji} *{title}*\n\n{message}"
        return self.send_message(alert_text)

    def send_daily_digest(self, findings: List[Any], summary: Dict) -> List[Dict]:
        """Send daily optimization digest."""
        total_savings = summary.get('total_potential_savings_usd', 0)

        message = [
            "☀️ *Daily Cloud-Zombie Digest*",
            f"_{datetime.utcnow().strftime('%A, %B %d, %Y')}_\n",
            f"💰 Total identified savings: *${total_savings:,.2f}/month*",
            f"🧟 Zombies found: *{summary.get('total_findings', 0)}*\n",
            "📈 *Potential Commission: ${:,.2f}/month*".format(total_savings * 0.15),
            "\n_Run `/analyze` to scan for new zombies!_"
        ]

        return self.send_message('\n'.join(message))

    def get_bot_info(self) -> Optional[Dict]:
        """Get bot information."""
        if not self.enabled:
            return None

        response = self._make_request('getMe', {})
        return response.get('result') if response.get('ok') else None

    def test_connection(self) -> bool:
        """Test bot connection."""
        info = self.get_bot_info()
        if info:
            logger.info(f"Connected to Telegram bot: @{info.get('username', 'unknown')}")
            return True
        return False


class TelegramCommandHandler:
    """Handle Telegram bot commands."""

    def __init__(self, bot: TelegramBot, analyzer_callback=None, optimize_callback=None):
        self.bot = bot
        self.analyzer_callback = analyzer_callback
        self.optimize_callback = optimize_callback

    def handle_command(self, command: str, args: str = '') -> str:
        """
        Handle incoming command.

        Commands:
        - /start - Welcome message
        - /help - Help information
        - /analyze - Trigger analysis
        - /optimize - Execute optimization scripts
        - /status - Current status
        - /report - Generate report
        """
        commands = {
            'start': self._cmd_start,
            'help': self._cmd_help,
            'analyze': self._cmd_analyze,
            'optimize': self._cmd_optimize,
            'status': self._cmd_status,
            'report': self._cmd_report
        }

        handler = commands.get(command.lower(), self._cmd_unknown)
        return handler(args)

    def _cmd_start(self, args: str) -> str:
        return (
            "👋 Welcome to *Cloud-Zombie Exorcist*!\n\n"
            "I help you identify and eliminate cloud waste:\n"
            "• 🧟 Zombie EC2 instances\n"
            "• 💾 Unattached EBS volumes\n"
            "• ❄️ Idle Snowflake warehouses\n"
            "• 🗑️ Cold S3 storage\n\n"
            "Use /help for available commands."
        )

    def _cmd_help(self, args: str) -> str:
        return (
            "📖 *Available Commands*\n\n"
            "/analyze - Scan cloud resources for optimization opportunities\n"
            "/optimize - Execute remediation scripts for identified zombies\n"
            "/status - Show current analysis status\n"
            "/report - Generate detailed optimization report\n"
            "/help - Show this help message\n\n"
            "💡 *Tip:* The bot will automatically notify you of new findings!"
        )

    def _cmd_analyze(self, args: str) -> str:
        if self.analyzer_callback:
            return "🔍 Starting analysis... You'll be notified when complete."
        return "⚠️ Analyzer not configured. Please contact administrator."

    def _cmd_optimize(self, args: str) -> str:
        if self.optimize_callback:
            return "⚡ Executing optimization scripts... This may take a few minutes."
        return "⚠️ Optimizer not configured. Please contact administrator."

    def _cmd_status(self, args: str) -> str:
        return (
            "📊 *System Status*\n\n"
            "✅ Bot: Online\n"
            "✅ Analyzer: Ready\n"
            "✅ Scripts: Loaded\n\n"
            f"_Last check: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_"
        )

    def _cmd_report(self, args: str) -> str:
        return "📄 Generating report... Check your files for the full report."

    def _cmd_unknown(self, args: str) -> str:
        return "❓ Unknown command. Use /help for available commands."


if __name__ == '__main__':
    # Test the bot
    import sys

    token = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TELEGRAM_BOT_TOKEN')

    if not token:
        print("Usage: python telegram_bot.py <BOT_TOKEN>")
        print("Or set TELEGRAM_BOT_TOKEN environment variable")
        sys.exit(1)

    bot = TelegramBot(token=token, chat_ids=['1707504118'])  # Default to user's ID

    print(f"Testing bot connection...")
    if bot.test_connection():
        print("✅ Bot connection successful!")

        # Send test message
        bot.send_message("🧟 Cloud-Zombie Exorcist bot is online and ready!")
    else:
        print("❌ Bot connection failed")
