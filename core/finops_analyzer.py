#!/usr/bin/env python3
"""
Cloud-Zombie Exorcist - FinOps Analysis Engine
Identifies underutilized cloud resources and optimization opportunities.
"""

import json
import csv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class OptimizationFinding:
    """Represents a cloud optimization opportunity."""
    resource_type: str
    resource_id: str
    issue: str
    current_cost_usd: float
    potential_savings_usd: float
    recommendation: str
    severity: str  # low, medium, high, critical
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any]


class FinOpsAnalyzer:
    """Analyzes cloud usage logs to identify cost optimization opportunities."""

    # Thresholds for identifying underutilized resources
    EC2_CPU_LOW_THRESHOLD = 0.10  # 10% CPU utilization
    EC2_NETWORK_LOW_THRESHOLD = 1000  # bytes
    EBS_UNATTACHED_DAYS = 7
    SNOWFLAKE_IDLE_HOURS = 24
    SNOWFLAKE_OVERSIZED_THRESHOLD = 0.30  # 30% average credit usage

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.findings: List[OptimizationFinding] = []
        self.analysis_timestamp = datetime.utcnow()

    def analyze_ec2_instances(self, logs: List[Dict]) -> List[OptimizationFinding]:
        """Analyze EC2 instances for underutilization."""
        findings = []

        for instance in logs:
            instance_id = instance.get('InstanceId', instance.get('instance_id', 'unknown'))
            instance_type = instance.get('InstanceType', instance.get('instance_type', 'unknown'))

            # Get metrics
            avg_cpu = float(instance.get('AverageCPU', instance.get('avg_cpu', 0)))
            avg_network = float(instance.get('AverageNetworkIn', instance.get('avg_network_in', 0)))
            days_running = int(instance.get('DaysRunning', instance.get('days_running', 0)))
            hourly_cost = float(instance.get('HourlyCost', instance.get('hourly_cost', 0)))

            # Check for zombie instances (very low utilization)
            if avg_cpu < self.EC2_CPU_LOW_THRESHOLD and avg_network < self.EC2_NETWORK_LOW_THRESHOLD:
                monthly_cost = hourly_cost * 24 * 30
                potential_savings = monthly_cost * 0.8  # Assume 80% can be saved

                severity = 'critical' if monthly_cost > 500 else 'high' if monthly_cost > 100 else 'medium'

                findings.append(OptimizationFinding(
                    resource_type='EC2',
                    resource_id=instance_id,
                    issue='Zombie instance - extremely low utilization',
                    current_cost_usd=monthly_cost,
                    potential_savings_usd=potential_savings,
                    recommendation=f'Terminate or downsize {instance_type} instance',
                    severity=severity,
                    confidence=0.95,
                    metadata={
                        'instance_type': instance_type,
                        'avg_cpu_percent': avg_cpu * 100,
                        'days_running': days_running,
                        'hourly_cost': hourly_cost,
                        'action': 'terminate' if days_running > 30 else 'resize'
                    }
                ))

            # Check for oversized instances
            elif avg_cpu < 0.30 and instance_type.startswith(('m5.', 'm4.', 'c5.', 'c4.')):
                monthly_cost = hourly_cost * 24 * 30
                potential_savings = monthly_cost * 0.5  # Right-sizing saves ~50%

                findings.append(OptimizationFinding(
                    resource_type='EC2',
                    resource_id=instance_id,
                    issue='Oversized instance - low CPU for instance class',
                    current_cost_usd=monthly_cost,
                    potential_savings_usd=potential_savings,
                    recommendation=f'Right-size {instance_type} to smaller instance',
                    severity='medium',
                    confidence=0.85,
                    metadata={
                        'instance_type': instance_type,
                        'avg_cpu_percent': avg_cpu * 100,
                        'suggested_action': 'rightsize',
                        'hourly_cost': hourly_cost
                    }
                ))

        return findings

    def analyze_ebs_volumes(self, volumes: List[Dict]) -> List[OptimizationFinding]:
        """Analyze EBS volumes for unattached or underutilized storage."""
        findings = []

        for volume in volumes:
            volume_id = volume.get('VolumeId', volume.get('volume_id', 'unknown'))
            state = volume.get('State', volume.get('state', 'unknown'))
            size_gb = int(volume.get('Size', volume.get('size_gb', 0)))
            volume_type = volume.get('VolumeType', volume.get('volume_type', 'gp2'))

            # Cost per GB-month by volume type
            cost_per_gb = {'gp3': 0.08, 'gp2': 0.10, 'io1': 0.125, 'io2': 0.125, 'st1': 0.045, 'sc1': 0.025}
            monthly_cost = size_gb * cost_per_gb.get(volume_type, 0.10)

            # Check for unattached volumes
            if state == 'available' or volume.get('Attachments', []):
                days_unattached = int(volume.get('DaysUnattached', volume.get('days_unattached', 0)))

                if days_unattached >= self.EBS_UNATTACHED_DAYS:
                    findings.append(OptimizationFinding(
                        resource_type='EBS',
                        resource_id=volume_id,
                        issue=f'Unattached EBS volume for {days_unattached} days',
                        current_cost_usd=monthly_cost,
                        potential_savings_usd=monthly_cost,
                        recommendation=f'Delete unattached {size_gb}GB {volume_type} volume',
                        severity='high' if monthly_cost > 50 else 'medium',
                        confidence=0.98,
                        metadata={
                            'size_gb': size_gb,
                            'volume_type': volume_type,
                            'days_unattached': days_unattached,
                            'action': 'delete'
                        }
                    ))

            # Check for underutilized IOPS (io1/io2 volumes)
            if volume_type in ('io1', 'io2'):
                avg_iops = float(volume.get('AverageIOPS', volume.get('avg_iops', 0)))
                provisioned_iops = int(volume.get('IOPS', volume.get('provisioned_iops', 0)))

                if provisioned_iops > 0 and avg_iops / provisioned_iops < 0.20:
                    potential_savings = monthly_cost * 0.6

                    findings.append(OptimizationFinding(
                        resource_type='EBS',
                        resource_id=volume_id,
                        issue='Over-provisioned IOPS on io1/io2 volume',
                        current_cost_usd=monthly_cost,
                        potential_savings_usd=potential_savings,
                        recommendation=f'Reduce provisioned IOPS from {provisioned_iops} to {int(avg_iops * 1.2)}',
                        severity='medium',
                        confidence=0.80,
                        metadata={
                            'provisioned_iops': provisioned_iops,
                            'avg_iops': avg_iops,
                            'action': 'modify_iops'
                        }
                    ))

        return findings

    def analyze_snowflake_warehouses(self, warehouses: List[Dict]) -> List[OptimizationFinding]:
        """Analyze Snowflake warehouses for optimization opportunities."""
        findings = []

        # Credit cost per warehouse size (approximate hourly)
        warehouse_costs = {
            'X-Small': 1, 'Small': 2, 'Medium': 4, 'Large': 8,
            'X-Large': 16, '2X-Large': 32, '3X-Large': 64, '4X-Large': 128
        }

        for wh in warehouses:
            wh_name = wh.get('name', wh.get('warehouse_name', 'unknown'))
            wh_size = wh.get('size', wh.get('warehouse_size', 'Medium'))
            state = wh.get('state', wh.get('status', 'RUNNING'))

            # Get usage metrics
            credits_used = float(wh.get('credits_used', wh.get('total_credits', 0)))
            query_count = int(wh.get('query_count', wh.get('total_queries', 0)))
            hours_active = float(wh.get('hours_active', wh.get('active_hours', 0)))
            analysis_period_days = int(wh.get('analysis_period_days', 30))

            hourly_cost = warehouse_costs.get(wh_size, 4)
            total_cost = credits_used * 2.0  # Approximate $2 per credit
            monthly_cost = total_cost / max(analysis_period_days, 1) * 30

            # Check for idle warehouses
            if hours_active < 10 and query_count < 5 and analysis_period_days >= 7:
                findings.append(OptimizationFinding(
                    resource_type='Snowflake',
                    resource_id=wh_name,
                    issue='Idle warehouse - minimal query activity',
                    current_cost_usd=monthly_cost,
                    potential_savings_usd=monthly_cost * 0.9,
                    recommendation=f'Suspend or drop warehouse {wh_name}',
                    severity='high',
                    confidence=0.92,
                    metadata={
                        'warehouse_size': wh_size,
                        'current_state': state,
                        'hours_active': hours_active,
                        'query_count': query_count,
                        'credits_used': credits_used,
                        'action': 'suspend'
                    }
                ))

            # Check for oversized warehouses
            avg_credit_usage = wh.get('avg_credit_usage_per_hour', credits_used / max(hours_active, 1))
            max_credit_rate = warehouse_costs.get(wh_size, 4)

            if hours_active > 0 and avg_credit_usage / max_credit_rate < self.SNOWFLAKE_OVERSIZED_THRESHOLD:
                potential_savings = monthly_cost * 0.5

                # Suggest smaller size
                sizes = ['X-Small', 'Small', 'Medium', 'Large', 'X-Large', '2X-Large', '3X-Large', '4X-Large']
                current_idx = sizes.index(wh_size) if wh_size in sizes else 2
                suggested_size = sizes[max(0, current_idx - 2)]

                findings.append(OptimizationFinding(
                    resource_type='Snowflake',
                    resource_id=wh_name,
                    issue='Oversized warehouse - low credit utilization',
                    current_cost_usd=monthly_cost,
                    potential_savings_usd=potential_savings,
                    recommendation=f'Resize {wh_name} from {wh_size} to {suggested_size}',
                    severity='medium',
                    confidence=0.78,
                    metadata={
                        'current_size': wh_size,
                        'suggested_size': suggested_size,
                        'avg_credit_usage': avg_credit_usage,
                        'utilization_percent': (avg_credit_usage / max_credit_rate) * 100,
                        'action': 'resize'
                    }
                ))

            # Check for warehouses without auto-suspend
            auto_suspend = wh.get('auto_suspend_minutes', wh.get('auto_suspend', None))
            if auto_suspend is None or auto_suspend == 0:
                wasted_cost = monthly_cost * 0.3  # Estimate 30% waste without auto-suspend

                findings.append(OptimizationFinding(
                    resource_type='Snowflake',
                    resource_id=wh_name,
                    issue='No auto-suspend configured - credits wasted',
                    current_cost_usd=monthly_cost,
                    potential_savings_usd=wasted_cost,
                    recommendation=f'Enable auto-suspend (60 seconds recommended) for {wh_name}',
                    severity='medium',
                    confidence=0.95,
                    metadata={
                        'auto_suspend_minutes': auto_suspend,
                        'action': 'configure_auto_suspend'
                    }
                ))

        return findings

    def analyze_s3_storage(self, buckets: List[Dict]) -> List[OptimizationFinding]:
        """Analyze S3 buckets for optimization opportunities."""
        findings = []

        storage_costs = {'STANDARD': 0.023, 'STANDARD_IA': 0.0125, 'GLACIER': 0.004, 'DEEP_ARCHIVE': 0.00099}

        for bucket in buckets:
            bucket_name = bucket.get('BucketName', bucket.get('bucket_name', 'unknown'))
            size_gb = float(bucket.get('SizeGB', bucket.get('size_gb', 0)))
            storage_class = bucket.get('StorageClass', bucket.get('storage_class', 'STANDARD'))

            monthly_cost = size_gb * storage_costs.get(storage_class, 0.023)

            # Check for old objects that could be archived
            days_since_last_access = int(bucket.get('DaysSinceLastAccess', bucket.get('days_since_access', 0)))

            if days_since_last_access > 90 and storage_class == 'STANDARD':
                potential_savings = monthly_cost * 0.8  # Glacier is ~80% cheaper

                findings.append(OptimizationFinding(
                    resource_type='S3',
                    resource_id=bucket_name,
                    issue=f'Cold storage - no access for {days_since_last_access} days',
                    current_cost_usd=monthly_cost,
                    potential_savings_usd=potential_savings,
                    recommendation=f'Transition {bucket_name} to Glacier storage class',
                    severity='medium' if monthly_cost < 100 else 'high',
                    confidence=0.88,
                    metadata={
                        'size_gb': size_gb,
                        'current_class': storage_class,
                        'days_since_access': days_since_last_access,
                        'action': 'transition_to_glacier'
                    }
                ))

            # Check for incomplete multipart uploads
            incomplete_uploads = int(bucket.get('IncompleteUploads', bucket.get('incomplete_uploads', 0)))
            incomplete_size_gb = float(bucket.get('IncompleteUploadSizeGB', bucket.get('incomplete_size_gb', 0)))

            if incomplete_size_gb > 10:
                wasted_cost = incomplete_size_gb * storage_costs.get(storage_class, 0.023)

                findings.append(OptimizationFinding(
                    resource_type='S3',
                    resource_id=f'{bucket_name}/incomplete-uploads',
                    issue=f'{incomplete_uploads} incomplete multipart uploads wasting {incomplete_size_gb:.1f}GB',
                    current_cost_usd=wasted_cost,
                    potential_savings_usd=wasted_cost,
                    recommendation=f'Abort incomplete uploads in {bucket_name}',
                    severity='low',
                    confidence=0.95,
                    metadata={
                        'incomplete_uploads': incomplete_uploads,
                        'wasted_gb': incomplete_size_gb,
                        'action': 'abort_incomplete_uploads'
                    }
                ))

        return findings

    def load_json_logs(self, filepath: str) -> Dict[str, List]:
        """Load cloud logs from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Support various JSON structures
        if isinstance(data, dict):
            return {
                'ec2': data.get('ec2_instances', data.get('EC2', [])),
                'ebs': data.get('ebs_volumes', data.get('EBS', [])),
                'snowflake': data.get('snowflake_warehouses', data.get('snowflake', [])),
                's3': data.get('s3_buckets', data.get('S3', []))
            }
        return {'ec2': data, 'ebs': [], 'snowflake': [], 's3': []}

    def load_csv_logs(self, filepath: str, resource_type: str) -> List[Dict]:
        """Load cloud logs from CSV file."""
        results = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(dict(row))
        return results

    def analyze(self, data: Dict[str, List]) -> List[OptimizationFinding]:
        """Run full analysis on provided cloud data."""
        self.findings = []

        if data.get('ec2'):
            self.findings.extend(self.analyze_ec2_instances(data['ec2']))

        if data.get('ebs'):
            self.findings.extend(self.analyze_ebs_volumes(data['ebs']))

        if data.get('snowflake'):
            self.findings.extend(self.analyze_snowflake_warehouses(data['snowflake']))

        if data.get('s3'):
            self.findings.extend(self.analyze_s3_storage(data['s3']))

        # Sort by potential savings (highest first)
        self.findings.sort(key=lambda x: x.potential_savings_usd, reverse=True)

        return self.findings

    def analyze_file(self, filepath: str) -> List[OptimizationFinding]:
        """Analyze cloud logs from a file."""
        path = Path(filepath)

        if path.suffix == '.json':
            data = self.load_json_logs(filepath)
        elif path.suffix == '.csv':
            # Try to auto-detect resource type from filename
            name_lower = path.name.lower()
            if 'ec2' in name_lower:
                data = {'ec2': self.load_csv_logs(filepath, 'ec2'), 'ebs': [], 'snowflake': [], 's3': []}
            elif 'ebs' in name_lower or 'volume' in name_lower:
                data = {'ec2': [], 'ebs': self.load_csv_logs(filepath, 'ebs'), 'snowflake': [], 's3': []}
            elif 'snowflake' in name_lower or 'warehouse' in name_lower:
                data = {'ec2': [], 'ebs': [], 'snowflake': self.load_csv_logs(filepath, 'snowflake'), 's3': []}
            elif 's3' in name_lower or 'bucket' in name_lower:
                data = {'ec2': [], 'ebs': [], 'snowflake': [], 's3': self.load_csv_logs(filepath, 's3')}
            else:
                data = {'ec2': self.load_csv_logs(filepath, 'ec2'), 'ebs': [], 'snowflake': [], 's3': []}
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        return self.analyze(data)

    def get_summary(self) -> Dict:
        """Get analysis summary statistics."""
        if not self.findings:
            return {'total_findings': 0}

        total_savings = sum(f.potential_savings_usd for f in self.findings)
        total_current_cost = sum(f.current_cost_usd for f in self.findings)

        by_severity = {}
        by_type = {}
        for f in self.findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
            by_type[f.resource_type] = by_type.get(f.resource_type, 0) + 1

        return {
            'total_findings': len(self.findings),
            'total_potential_savings_usd': round(total_savings, 2),
            'total_current_cost_usd': round(total_current_cost, 2),
            'savings_percentage': round((total_savings / max(total_current_cost, 1)) * 100, 1),
            'by_severity': by_severity,
            'by_resource_type': by_type,
            'analysis_timestamp': self.analysis_timestamp.isoformat()
        }

    def to_json(self, filepath: Optional[str] = None) -> str:
        """Export findings to JSON."""
        output = {
            'summary': self.get_summary(),
            'findings': [asdict(f) for f in self.findings],
            'generated_at': datetime.utcnow().isoformat()
        }

        json_str = json.dumps(output, indent=2)

        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)

        return json_str

    def to_markdown(self) -> str:
        """Export findings to Markdown report."""
        summary = self.get_summary()

        md = ["# 🧟 Cloud-Zombie Exorcist - Optimization Report\n"]
        md.append(f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")

        md.append("## 📊 Summary\n")
        md.append(f"- **Total Findings:** {summary.get('total_findings', 0)}")
        md.append(f"- **Current Monthly Cost:** ${summary.get('total_current_cost_usd', 0):,.2f}")
        md.append(f"- **Potential Savings:** ${summary.get('total_potential_savings_usd', 0):,.2f}")
        md.append(f"- **Savings Percentage:** {summary.get('savings_percentage', 0)}%\n")

        if summary.get('by_severity'):
            md.append("### By Severity\n")
            for severity, count in summary['by_severity'].items():
                emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(severity, '⚪')
                md.append(f"- {emoji} **{severity.title()}:** {count}")

        md.append("\n## 🔍 Detailed Findings\n")

        for i, f in enumerate(self.findings, 1):
            severity_emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(f.severity, '⚪')
            md.append(f"### {i}. {severity_emoji} {f.resource_type}: {f.resource_id}\n")
            md.append(f"- **Issue:** {f.issue}")
            md.append(f"- **Current Cost:** ${f.current_cost_usd:,.2f}/month")
            md.append(f"- **Potential Savings:** ${f.potential_savings_usd:,.2f}/month")
            md.append(f"- **Confidence:** {f.confidence * 100:.0f}%")
            md.append(f"- **Recommendation:** {f.recommendation}\n")

        return "\n".join(md)


if __name__ == '__main__':
    # Example usage
    analyzer = FinOpsAnalyzer()

    # Sample test data
    sample_ec2 = [
        {'InstanceId': 'i-zombie123', 'InstanceType': 'm5.xlarge', 'AverageCPU': 0.02,
         'AverageNetworkIn': 500, 'DaysRunning': 45, 'HourlyCost': 0.192},
        {'InstanceId': 'i-oversized456', 'InstanceType': 'c5.2xlarge', 'AverageCPU': 0.15,
         'AverageNetworkIn': 5000, 'DaysRunning': 30, 'HourlyCost': 0.34}
    ]

    sample_ebs = [
        {'VolumeId': 'vol-orphan789', 'State': 'available', 'Size': 500,
         'VolumeType': 'gp2', 'DaysUnattached': 21}
    ]

    sample_snowflake = [
        {'name': 'WH_IDLE', 'size': 'X-Large', 'state': 'RUNNING', 'credits_used': 5.2,
         'query_count': 2, 'hours_active': 3, 'analysis_period_days': 14}
    ]

    findings = analyzer.analyze({
        'ec2': sample_ec2,
        'ebs': sample_ebs,
        'snowflake': sample_snowflake,
        's3': []
    })

    print(f"Found {len(findings)} optimization opportunities")
    print(f"Total potential savings: ${sum(f.potential_savings_usd for f in findings):,.2f}/month")
