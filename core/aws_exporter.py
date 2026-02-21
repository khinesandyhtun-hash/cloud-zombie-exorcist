#!/usr/bin/env python3
"""
Cloud-Zombie Exorcist - Live AWS Data Exporter
Fetches real infrastructure data from AWS for analysis.
"""

import boto3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any


class AWSDataExporter:
    """Export AWS infrastructure data for FinOps analysis."""

    def __init__(self, region: str = None):
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')
        
        # Initialize AWS clients
        self.ec2 = boto3.client('ec2', region_name=self.region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        self.s3 = boto3.client('s3', region_name=self.region)
        
        print(f"✓ Connected to AWS ({self.region})")

    def get_ec2_instances(self) -> List[Dict]:
        """Fetch EC2 instances with metrics."""
        print("Fetching EC2 instances...")
        
        instances = []
        paginator = self.ec2.get_paginator('describe_instances')
        
        for page in paginator.paginate():
            for reservation in page.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    if instance['State']['Name'] == 'terminated':
                        continue
                    
                    instance_id = instance['InstanceId']
                    instance_type = instance.get('InstanceType', 'unknown')
                    launch_time = instance.get('LaunchTime', datetime.utcnow())
                    
                    # Calculate days running
                    if hasattr(launch_time, 'days'):
                        days_running = (datetime.utcnow(launch_time.tzinfo) - launch_time).days
                    else:
                        days_running = 30
                    
                    # Get CloudWatch metrics (last 7 days)
                    metrics = self._get_ec2_metrics(instance_id)
                    
                    # Get pricing (simplified - in production use Pricing API)
                    hourly_cost = self._estimate_ec2_cost(instance_type)
                    
                    instances.append({
                        'InstanceId': instance_id,
                        'InstanceType': instance_type,
                        'AverageCPU': metrics.get('cpu', 0),
                        'AverageNetworkIn': metrics.get('network_in', 0),
                        'AverageNetworkOut': metrics.get('network_out', 0),
                        'DaysRunning': days_running,
                        'HourlyCost': hourly_cost,
                        'State': instance['State']['Name'],
                        'LaunchTime': str(launch_time),
                        'Tags': {t['Key']: t['Value'] for t in instance.get('Tags', [])}
                    })
        
        print(f"  Found {len(instances)} instances")
        return instances

    def _get_ec2_metrics(self, instance_id: str) -> Dict:
        """Get CloudWatch metrics for EC2 instance."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)
        
        metrics = {'cpu': 0, 'network_in': 0, 'network_out': 0}
        
        try:
            # CPU Utilization
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            datapoints = response.get('Datapoints', [])
            if datapoints:
                metrics['cpu'] = sum(d['Average'] for d in datapoints) / len(datapoints) / 100
            
            # Network In
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkIn',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            datapoints = response.get('Datapoints', [])
            if datapoints:
                metrics['network_in'] = sum(d['Average'] for d in datapoints) / len(datapoints)
            
            # Network Out
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkOut',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            datapoints = response.get('Datapoints', [])
            if datapoints:
                metrics['network_out'] = sum(d['Average'] for d in datapoints) / len(datapoints)
                
        except Exception as e:
            print(f"  Warning: Could not fetch metrics for {instance_id}: {e}")
        
        return metrics

    def _estimate_ec2_cost(self, instance_type: str) -> float:
        """Estimate hourly cost for EC2 instance (simplified)."""
        # Simplified pricing - in production use AWS Pricing API
        pricing = {
            't2.micro': 0.0116, 't2.small': 0.023, 't2.medium': 0.0464, 't2.large': 0.0928,
            't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416, 't3.large': 0.0832,
            'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384, 'm5.4xlarge': 0.768,
            'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34, 'c5.4xlarge': 0.68,
            'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504,
        }
        return pricing.get(instance_type, 0.10)

    def get_ebs_volumes(self) -> List[Dict]:
        """Fetch EBS volumes with metrics."""
        print("Fetching EBS volumes...")
        
        volumes = []
        paginator = self.ec2.get_paginator('describe_volumes')
        
        for page in paginator.paginate():
            for volume in page.get('Volumes', []):
                volume_id = volume['VolumeId']
                state = volume['State']
                size_gb = volume['Size']
                volume_type = volume['VolumeType']
                iops = volume.get('IOPS', 0)
                
                # Check attachments
                attachments = volume.get('Attachments', [])
                days_unattached = 0
                
                if not attachments and state == 'available':
                    days_unattached = 30  # Estimate - in production track creation time
                
                # Get IOPS metrics if attached
                avg_iops = 0
                if attachments:
                    avg_iops = self._get_volume_iops(volume_id)
                
                volumes.append({
                    'VolumeId': volume_id,
                    'State': state,
                    'Size': size_gb,
                    'VolumeType': volume_type,
                    'IOPS': iops,
                    'AverageIOPS': avg_iops,
                    'DaysUnattached': days_unattached,
                    'Attachments': len(attachments),
                    'Tags': {t['Key']: t['Value'] for t in volume.get('Tags', [])}
                })
        
        print(f"  Found {len(volumes)} volumes")
        return volumes

    def _get_volume_iops(self, volume_id: str) -> float:
        """Get average IOPS for EBS volume."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)
        
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EBS',
                MetricName='VolumeReadOps',
                Dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            datapoints = response.get('Datapoints', [])
            if datapoints:
                return sum(d['Average'] for d in datapoints) / len(datapoints)
        except:
            pass
        
        return 0

    def get_s3_buckets(self) -> List[Dict]:
        """Fetch S3 buckets with storage metrics."""
        print("Fetching S3 buckets...")
        
        buckets = []
        s3_client = boto3.client('s3', region_name=self.region)
        
        response = s3_client.list_buckets()
        for bucket in response.get('Buckets', []):
            bucket_name = bucket['Name']
            creation_date = bucket['CreationDate']
            
            # Calculate days since last access (estimate)
            days_since_access = (datetime.utcnow() - creation_date).days
            
            # Get bucket size from CloudWatch
            size_gb = self._get_bucket_size(bucket_name)
            
            # Check for incomplete uploads
            incomplete_count, incomplete_size = self._get_incomplete_uploads(bucket_name)
            
            buckets.append({
                'BucketName': bucket_name,
                'SizeGB': size_gb,
                'StorageClass': 'STANDARD',  # Default - would need additional API calls
                'DaysSinceLastAccess': min(days_since_access, 365),
                'IncompleteUploads': incomplete_count,
                'IncompleteUploadSizeGB': incomplete_size,
                'CreationDate': str(creation_date)
            })
        
        print(f"  Found {len(buckets)} buckets")
        return buckets

    def _get_bucket_size(self, bucket_name: str) -> float:
        """Get S3 bucket size in GB from CloudWatch."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName='BucketSizeBytes',
                Dimensions=[
                    {'Name': 'BucketName', 'Value': bucket_name},
                    {'Name': 'StorageType', 'Value': 'StandardStorage'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Average']
            )
            datapoints = response.get('Datapoints', [])
            if datapoints:
                return datapoints[0]['Average'] / (1024 ** 3)  # Convert to GB
        except:
            pass
        
        return 0

    def _get_incomplete_uploads(self, bucket_name: str) -> tuple:
        """Get count and size of incomplete multipart uploads."""
        try:
            response = self.s3.list_multipart_uploads(Bucket=bucket_name)
            uploads = response.get('Uploads', [])
            count = len(uploads)
            size_gb = sum(u.get('Initiated', datetime.utcnow()).timestamp() for u in uploads) / 100000000  # Estimate
            return count, min(size_gb, 100)
        except:
            return 0, 0

    def export_all(self, output_file: str = 'targets/live_aws_data.json') -> Dict:
        """Export all AWS infrastructure data."""
        print("\n🔄 Exporting AWS infrastructure data...\n")
        
        data = {
            'ec2_instances': self.get_ec2_instances(),
            'ebs_volumes': self.get_ebs_volumes(),
            's3_buckets': self.get_s3_buckets(),
            'export_timestamp': datetime.utcnow().isoformat(),
            'region': self.region
        }
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"\n✓ Data exported to: {output_file}")
        print(f"  EC2 Instances: {len(data['ec2_instances'])}")
        print(f"  EBS Volumes: {len(data['ebs_volumes'])}")
        print(f"  S3 Buckets: {len(data['s3_buckets'])}")
        
        return data


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export AWS infrastructure data')
    parser.add_argument('--output', '-o', default='targets/live_aws_data.json',
                        help='Output file path')
    parser.add_argument('--region', '-r', help='AWS region')
    parser.add_argument('--analyze', '-a', action='store_true',
                        help='Run analysis after export')
    
    args = parser.parse_args()
    
    try:
        exporter = AWSDataExporter(region=args.region)
        data = exporter.export_all(args.output)
        
        if args.analyze:
            print("\n🔍 Running FinOps analysis...\n")
            from core.finops_analyzer import FinOpsAnalyzer
            
            analyzer = FinOpsAnalyzer()
            findings = analyzer.analyze(data)
            
            print(f"\n✅ Analysis Complete")
            print(f"   Findings: {len(findings)}")
            print(f"   Potential Savings: ${sum(f.potential_savings_usd for f in findings):,.2f}/month")
            
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure AWS credentials are configured:")
        print("  aws configure")
        print("  Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
