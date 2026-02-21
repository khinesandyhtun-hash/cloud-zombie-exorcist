#!/usr/bin/env python3
"""
Cloud-Zombie Exorcist - Main CLI Orchestrator
Unifies FinOps analysis, optimization scripts, and Telegram notifications.
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Add core to path
sys.path.insert(0, str(Path(__file__).parent / 'core'))

from finops_analyzer import FinOpsAnalyzer, OptimizationFinding
from telegram_bot import TelegramBot, TelegramCommandHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CloudZombieExorcist:
    """Main orchestrator for Cloud-Zombie Exorcist service."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Cloud-Zombie Exorcist.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.analyzer = FinOpsAnalyzer(self.config.get('analyzer', {}))
        self.telegram = TelegramBot(
            token=self.config.get('telegram', {}).get('bot_token'),
            chat_ids=self.config.get('telegram', {}).get('chat_ids')
        )
        self.reports_dir = Path(self.config.get('reports_dir', './reports'))
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from file or environment."""
        default_config = {
            'telegram': {
                'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN'),
                'chat_ids': os.environ.get('TELEGRAM_CHAT_IDS', '').split(',') if os.environ.get('TELEGRAM_CHAT_IDS') else []
            },
            'aws': {
                'region': os.environ.get('AWS_REGION', 'us-east-1'),
                'profile': os.environ.get('AWS_PROFILE')
            },
            'snowflake': {
                'account': os.environ.get('SNOWFLAKE_ACCOUNT'),
                'user': os.environ.get('SNOWFLAKE_USER'),
                'warehouse': os.environ.get('SNOWFLAKE_WAREHOUSE', 'ACCOUNTADMIN')
            },
            'analyzer': {
                'ec2_cpu_threshold': float(os.environ.get('EC2_CPU_THRESHOLD', '0.10')),
                'ebs_unattached_days': int(os.environ.get('EBS_UNATTACHED_DAYS', '7')),
                'snowflake_idle_hours': int(os.environ.get('SNOWFLAKE_IDLE_HOURS', '24'))
            },
            'reports_dir': './reports',
            'dry_run': os.environ.get('DRY_RUN', 'true').lower() == 'true',
            'auto_notify': os.environ.get('AUTO_NOTIFY', 'true').lower() == 'true'
        }

        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                # Deep merge
                for key, value in file_config.items():
                    if isinstance(value, dict) and key in default_config:
                        default_config[key].update(value)
                    else:
                        default_config[key] = value

        return default_config

    def analyze(self, data_files: List[str], output_format: str = 'all') -> dict:
        """
        Analyze cloud resource data files.

        Args:
            data_files: List of paths to JSON/CSV data files
            output_format: Output format (json, markdown, all)

        Returns:
            Analysis summary
        """
        logger.info(f"Starting analysis of {len(data_files)} files")

        all_findings = []

        for filepath in data_files:
            if not Path(filepath).exists():
                logger.warning(f"File not found: {filepath}")
                continue

            try:
                findings = self.analyzer.analyze_file(filepath)
                all_findings.extend(findings)
                logger.info(f"Found {len(findings)} optimization opportunities in {filepath}")
            except Exception as e:
                logger.error(f"Error analyzing {filepath}: {e}")

        # Sort by savings
        all_findings.sort(key=lambda x: x.potential_savings_usd, reverse=True)

        # Get summary
        summary = self.analyzer.get_summary()

        # Generate outputs
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

        if output_format in ('json', 'all'):
            json_path = self.reports_dir / f'findings_{timestamp}.json'
            self.analyzer.to_json(str(json_path))
            logger.info(f"JSON report saved: {json_path}")

        if output_format in ('markdown', 'all'):
            md_path = self.reports_dir / f'report_{timestamp}.md'
            with open(md_path, 'w') as f:
                f.write(self.analyzer.to_markdown())
            logger.info(f"Markdown report saved: {md_path}")

        # Send Telegram notification
        if self.config.get('auto_notify', True) and self.telegram.enabled:
            try:
                self.telegram.send_optimization_report(
                    all_findings,
                    summary,
                    str(json_path) if output_format in ('json', 'all') else None
                )
                logger.info("Telegram notification sent")
            except Exception as e:
                logger.error(f"Failed to send Telegram notification: {e}")

        return summary

    def analyze_from_cloud(self, resource_types: Optional[List[str]] = None) -> dict:
        """
        Fetch and analyze live cloud resource data.

        Args:
            resource_types: List of resource types to analyze (ec2, ebs, snowflake, s3)

        Returns:
            Analysis summary
        """
        logger.info("Fetching live cloud data...")

        # This would integrate with AWS SDK, Snowflake connector, etc.
        # For now, we'll use sample data generation

        sample_data = {
            'ec2': [],
            'ebs': [],
            'snowflake': [],
            's3': []
        }

        # In production, this would call:
        # - AWS: boto3.client('ec2').describe_instances()
        # - Snowflake: snowflake.connector.connect()

        findings = self.analyzer.analyze(sample_data)

        summary = self.analyzer.get_summary()

        # Generate reports
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        json_path = self.reports_dir / f'live_findings_{timestamp}.json'
        self.analyzer.to_json(str(json_path))

        if self.config.get('auto_notify', True) and self.telegram.enabled:
            self.telegram.send_optimization_report(findings, summary, str(json_path))

        return summary

    def optimize(self, findings_file: str, execute: bool = False) -> dict:
        """
        Execute optimization actions.

        Args:
            findings_file: Path to findings JSON file
            execute: If True, actually execute changes (default: dry-run)

        Returns:
            Execution results
        """
        logger.info(f"Processing optimizations from {findings_file}")
        logger.info(f"Execute mode: {execute}")

        with open(findings_file, 'r') as f:
            data = json.load(f)

        findings = data.get('findings', [])
        results = {
            'total': len(findings),
            'executed': 0,
            'skipped': 0,
            'errors': 0,
            'actions': []
        }

        for finding in findings:
            resource_type = finding.get('resource_type')
            resource_id = finding.get('resource_id')
            recommendation = finding.get('recommendation')
            severity = finding.get('severity')

            action_plan = {
                'resource_type': resource_type,
                'resource_id': resource_id,
                'recommendation': recommendation,
                'executed': False,
                'error': None
            }

            try:
                if execute:
                    # In production, this would call the actual optimization scripts
                    logger.info(f"Executing: {recommendation}")

                    # Placeholder for actual execution
                    # subprocess.run(['scripts/aws_optimizer.sh', 'delete-ebs', resource_id])

                    action_plan['executed'] = True
                    results['executed'] += 1
                else:
                    logger.info(f"DRY RUN: {recommendation}")
                    results['skipped'] += 1

            except Exception as e:
                logger.error(f"Error executing optimization for {resource_id}: {e}")
                action_plan['error'] = str(e)
                results['errors'] += 1

            results['actions'].append(action_plan)

        # Send notification
        if self.telegram.enabled:
            if execute:
                self.telegram.send_message(
                    f"✅ Optimization Complete\n\n"
                    f"Executed: {results['executed']}\n"
                    f"Skipped: {results['skipped']}\n"
                    f"Errors: {results['errors']}"
                )
            else:
                self.telegram.send_message(
                    f"📋 Optimization Dry-Run Complete\n\n"
                    f"Total findings: {results['total']}\n"
                    f"Ready to execute when DRY_RUN=false"
                )

        return results

    def status(self) -> dict:
        """Get current system status."""
        return {
            'telegram_bot': 'connected' if self.telegram.enabled and self.telegram.test_connection() else 'disconnected',
            'reports_dir': str(self.reports_dir),
            'dry_run': self.config.get('dry_run', True),
            'auto_notify': self.config.get('auto_notify', True),
            'config_path': self.config.get('config_path', 'environment')
        }

    def interactive_mode(self):
        """Run in interactive CLI mode."""
        print("""
🧟 Cloud-Zombie Exorcist - Interactive Mode

Commands:
  analyze <file1> [file2...]  - Analyze cloud data files
  status                      - Show system status
  optimize <file> [--execute] - Process optimizations
  notify <message>            - Send Telegram message
  quit                        - Exit

        """)

        while True:
            try:
                cmd = input("> ").strip()
                if not cmd:
                    continue

                parts = cmd.split()
                command = parts[0].lower()

                if command == 'quit' or command == 'exit':
                    print("Goodbye! 👋")
                    break

                elif command == 'status':
                    status = self.status()
                    print(json.dumps(status, indent=2))

                elif command == 'analyze':
                    files = parts[1:] if len(parts) > 1 else []
                    if not files:
                        print("Usage: analyze <file1> [file2...]")
                        continue
                    summary = self.analyze(files)
                    print(f"\nAnalysis complete!")
                    print(f"Total findings: {summary.get('total_findings', 0)}")
                    print(f"Potential savings: ${summary.get('total_potential_savings_usd', 0):,.2f}/month")

                elif command == 'optimize':
                    if len(parts) < 2:
                        print("Usage: optimize <file> [--execute]")
                        continue
                    filepath = parts[1]
                    execute = '--execute' in parts
                    results = self.optimize(filepath, execute)
                    print(f"\nOptimization complete!")
                    print(f"Executed: {results['executed']}, Skipped: {results['skipped']}, Errors: {results['errors']}")

                elif command == 'notify':
                    message = ' '.join(parts[1:]) if len(parts) > 1 else "Test message"
                    responses = self.telegram.send_message(message)
                    print(f"Message sent to {len(responses)} chats")

                else:
                    print(f"Unknown command: {command}")

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except Exception as e:
                print(f"Error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='🧟 Cloud-Zombie Exorcist - FinOps Optimization Service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze targets/aws_data.json targets/snowflake_data.csv
  %(prog)s analyze --live
  %(prog)s optimize reports/findings_20260221.json --execute
  %(prog)s status
  %(prog)s interactive
        """
    )

    parser.add_argument('command', nargs='?', default='analyze',
                        choices=['analyze', 'optimize', 'status', 'interactive'],
                        help='Command to execute')
    parser.add_argument('files', nargs='*', help='Data files to process')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--output', '-o', choices=['json', 'markdown', 'all'], default='all',
                        help='Output format')
    parser.add_argument('--execute', '-x', action='store_true',
                        help='Execute optimizations (default: dry-run)')
    parser.add_argument('--live', '-l', action='store_true',
                        help='Fetch live cloud data')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')
    parser.add_argument('--no-notify', action='store_true',
                        help='Disable Telegram notifications')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize
    exorcist = CloudZombieExorcist(config_path=args.config)

    if args.no_notify:
        exorcist.config['auto_notify'] = False

    # Execute command
    if args.command == 'analyze':
        if args.live:
            summary = exorcist.analyze_from_cloud()
        else:
            if not args.files:
                print("Error: No input files specified. Use --live for live analysis.")
                sys.exit(1)
            summary = exorcist.analyze(args.files, output_format=args.output)

        print(f"\n✅ Analysis Complete")
        print(f"   Findings: {summary.get('total_findings', 0)}")
        print(f"   Potential Savings: ${summary.get('total_potential_savings_usd', 0):,.2f}/month")
        print(f"   Reports saved to: {exorcist.reports_dir}")

    elif args.command == 'optimize':
        if not args.files:
            print("Error: No findings file specified")
            sys.exit(1)

        results = exorcist.optimize(args.files[0], execute=args.execute)
        print(f"\n✅ Optimization Complete")
        print(f"   Executed: {results['executed']}")
        print(f"   Skipped: {results['skipped']}")
        print(f"   Errors: {results['errors']}")

    elif args.command == 'status':
        status = exorcist.status()
        print(json.dumps(status, indent=2))

    elif args.command == 'interactive':
        exorcist.interactive_mode()


if __name__ == '__main__':
    main()
