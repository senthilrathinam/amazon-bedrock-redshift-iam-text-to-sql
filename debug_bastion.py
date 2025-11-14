#!/usr/bin/env python3
"""
Debug script for EC2 bastion host creation issues.
"""
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def debug_bastion_creation():
    """Debug why bastion host creation failed."""
    
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    ec2 = boto3.client(
        'ec2', 
        region_name=region,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    iam = boto3.client(
        'iam', 
        region_name=region,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    print(f"🔍 Debugging bastion creation in region: {region}")
    
    # Check 1: Default VPC
    try:
        vpc_response = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
        if vpc_response['Vpcs']:
            vpc_id = vpc_response['Vpcs'][0]['VpcId']
            print(f"✅ Default VPC found: {vpc_id}")
        else:
            print("❌ No default VPC found - this is required for bastion creation")
            return False
    except Exception as e:
        print(f"❌ Error checking VPC: {e}")
        return False
    
    # Check 2: IAM permissions for EC2
    try:
        # Test if we can describe instances
        ec2.describe_instances(MaxResults=5)
        print("✅ EC2 describe permissions OK")
        
        # Test if we can create security groups
        try:
            test_sg = ec2.create_security_group(
                GroupName='test-debug-sg',
                Description='Test security group',
                VpcId=vpc_id
            )
            ec2.delete_security_group(GroupId=test_sg['GroupId'])
            print("✅ EC2 create permissions OK")
        except Exception as e:
            print(f"❌ Cannot create security groups: {e}")
            return False
            
    except Exception as e:
        print(f"❌ EC2 permissions error: {e}")
        return False
    
    # Check 3: IAM role creation permissions
    try:
        # Try to get existing role
        try:
            iam.get_role(RoleName='EC2-SSM-Role')
            print("✅ SSM role already exists")
        except iam.exceptions.NoSuchEntityException:
            print("⚠️  SSM role doesn't exist - will need to create")
            # Test role creation permission
            try:
                test_role = {
                    "Version": "2012-10-17",
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]
                }
                iam.create_role(
                    RoleName='test-debug-role',
                    AssumeRolePolicyDocument=str(test_role).replace("'", '"')
                )
                iam.delete_role(RoleName='test-debug-role')
                print("✅ IAM role creation permissions OK")
            except Exception as e:
                print(f"❌ Cannot create IAM roles: {e}")
                return False
    except Exception as e:
        print(f"❌ IAM permissions error: {e}")
        return False
    
    # Check 4: AMI availability
    try:
        ami_id = 'ami-0c02fb55956c7d316'  # Amazon Linux 2
        ami_response = ec2.describe_images(ImageIds=[ami_id])
        if ami_response['Images']:
            print(f"✅ AMI available: {ami_id}")
        else:
            print(f"❌ AMI not available in {region}: {ami_id}")
            # Find alternative AMI
            alt_response = ec2.describe_images(
                Filters=[
                    {'Name': 'name', 'Values': ['amzn2-ami-hvm-*']},
                    {'Name': 'architecture', 'Values': ['x86_64']},
                    {'Name': 'state', 'Values': ['available']}
                ],
                Owners=['amazon'],
                MaxResults=1
            )
            if alt_response['Images']:
                alt_ami = alt_response['Images'][0]['ImageId']
                print(f"💡 Alternative AMI found: {alt_ami}")
            return False
    except Exception as e:
        print(f"❌ Error checking AMI: {e}")
        return False
    
    # Check 5: Service limits
    try:
        # Check running instances
        instances = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        running_count = sum(len(r['Instances']) for r in instances['Reservations'])
        print(f"✅ Running instances: {running_count}")
        
        if running_count > 15:  # Typical default limit is 20
            print("⚠️  Close to instance limit - may cause creation failure")
            
    except Exception as e:
        print(f"⚠️  Could not check service limits: {e}")
    
    # Check 6: Existing bastion
    try:
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': ['sales-analyst-bastion']},
                {'Name': 'instance-state-name', 'Values': ['running', 'pending']}
            ]
        )
        if response['Reservations']:
            instance = response['Reservations'][0]['Instances'][0]
            print(f"✅ Bastion already exists: {instance['InstanceId']} ({instance['State']['Name']})")
            return True
        else:
            print("ℹ️  No existing bastion found")
    except Exception as e:
        print(f"❌ Error checking existing bastion: {e}")
    
    print("\n🎯 All checks passed - bastion creation should work")
    return True

if __name__ == "__main__":
    debug_bastion_creation()
