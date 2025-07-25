#!/usr/bin/env python3
"""
Test script to verify region functionality
"""

import json
import subprocess
import sys

def test_aws_regions():
    """Test getting AWS regions"""
    try:
        # Test AWS CLI region list command
        result = subprocess.run(
            ["aws", "ec2", "describe-regions", "--output", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        if result.returncode == 0:
            regions_data = json.loads(result.stdout)
            regions = [region['RegionName'] for region in regions_data['Regions']]
            print(f"Available AWS regions: {regions}")
            return True
        else:
            print(f"Error getting regions: {result.stderr}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_ec2_instances_in_region(region, profile=None):
    """Test getting EC2 instances in a specific region"""
    try:
        command = ["aws", "ec2", "describe-instances", "--region", region, "--output", "json"]
        if profile:
            command.extend(["--profile", profile])
            
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        if result.returncode == 0:
            instances_data = json.loads(result.stdout)
            instances = []
            for reservation in instances_data.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance.get("InstanceId", "")
                    state = instance.get("State", {}).get("Name", "")
                    instances.append((instance_id, state))
            
            print(f"Found {len(instances)} instances in {region}")
            for instance_id, state in instances:
                print(f"  - {instance_id}: {state}")
            return True
        else:
            print(f"Error getting instances in {region}: {result.stderr}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    print("Testing AWS Region Functionality")
    print("=" * 40)
    
    # Test getting regions
    print("1. Testing region list...")
    if test_aws_regions():
        print("✓ Region list test passed")
    else:
        print("✗ Region list test failed")
    
    # Test getting instances in a few regions
    test_regions = ["us-east-1", "us-west-2", "eu-west-1"]
    
    for region in test_regions:
        print(f"\n2. Testing instances in {region}...")
        if test_ec2_instances_in_region(region):
            print(f"✓ Instance list test passed for {region}")
        else:
            print(f"✗ Instance list test failed for {region}")
    
    print("\nTest completed!") 