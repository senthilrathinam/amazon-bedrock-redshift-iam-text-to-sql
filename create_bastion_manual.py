#!/usr/bin/env python3
"""
Manual bastion host creation script.
"""
import boto3
import os
import time
from dotenv import load_dotenv

load_dotenv()

def create_bastion_manual():
    """Manually create bastion host with detailed error handling."""
    
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
    
    try:
        print("🚀 Creating bastion host manually...")
        
        # Step 1: Get VPC
        vpc_response = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
        vpc_id = vpc_response['Vpcs'][0]['VpcId']
        print(f"Using VPC: {vpc_id}")
        
        # Step 2: Create IAM role
        print("Creating IAM role...")
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            iam.create_role(
                RoleName='EC2-SSM-Role',
                AssumeRolePolicyDocument=str(trust_policy).replace("'", '"')
            )
            print("✅ Created IAM role")
        except iam.exceptions.EntityAlreadyExistsException:
            print("✅ IAM role already exists")
        
        # Attach policy
        iam.attach_role_policy(
            RoleName='EC2-SSM-Role',
            PolicyArn='arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
        )
        
        # Create instance profile
        try:
            iam.create_instance_profile(InstanceProfileName='EC2-SSM-Role')
            time.sleep(2)
            iam.add_role_to_instance_profile(
                InstanceProfileName='EC2-SSM-Role',
                RoleName='EC2-SSM-Role'
            )
            print("✅ Created instance profile")
        except iam.exceptions.EntityAlreadyExistsException:
            print("✅ Instance profile already exists")
        
        # Step 3: Find suitable AMI
        print("Finding AMI...")
        try:
            # Try default AMI first
            ami_response = ec2.describe_images(ImageIds=['ami-0c02fb55956c7d316'])
            ami_id = 'ami-0c02fb55956c7d316'
            print(f"✅ Using default AMI: {ami_id}")
        except:
            # Find Amazon Linux 2 AMI
            ami_response = ec2.describe_images(
                Filters=[
                    {'Name': 'name', 'Values': ['amzn2-ami-hvm-*']},
                    {'Name': 'architecture', 'Values': ['x86_64']},
                    {'Name': 'state', 'Values': ['available']}
                ],
                Owners=['amazon'],
                MaxResults=1
            )
            ami_id = ami_response['Images'][0]['ImageId']
            print(f"✅ Using alternative AMI: {ami_id}")
        
        # Step 4: Create security group
        print("Creating security group...")
        try:
            sg_response = ec2.create_security_group(
                GroupName='sales-analyst-bastion-sg',
                Description='Security group for sales analyst bastion host',
                VpcId=vpc_id
            )
            sg_id = sg_response['GroupId']
            print(f"✅ Created security group: {sg_id}")
        except Exception as e:
            if 'already exists' in str(e):
                sg_response = ec2.describe_security_groups(
                    Filters=[
                        {'Name': 'group-name', 'Values': ['sales-analyst-bastion-sg']},
                        {'Name': 'vpc-id', 'Values': [vpc_id]}
                    ]
                )
                sg_id = sg_response['SecurityGroups'][0]['GroupId']
                print(f"✅ Using existing security group: {sg_id}")
            else:
                raise e
        
        # Step 5: Create instance
        print("Creating EC2 instance...")
        
        user_data = '''#!/bin/bash
yum update -y
yum install -y amazon-ssm-agent
systemctl enable amazon-ssm-agent
systemctl restart amazon-ssm-agent
'''
        
        response = ec2.run_instances(
            ImageId=ami_id,
            MinCount=1,
            MaxCount=1,
            InstanceType='t3.micro',
            SecurityGroupIds=[sg_id],
            IamInstanceProfile={'Name': 'EC2-SSM-Role'},
            UserData=user_data,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': 'sales-analyst-bastion'}]
                }
            ]
        )
        
        instance_id = response['Instances'][0]['InstanceId']
        print(f"✅ Created instance: {instance_id}")
        
        # Step 6: Wait for instance
        print("Waiting for instance to be running...")
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        print("✅ Instance is running")
        
        print(f"\n🎉 Bastion host created successfully!")
        print(f"Instance ID: {instance_id}")
        print(f"Security Group: {sg_id}")
        print("\nWait 2-3 minutes for SSM agent to initialize, then restart the app.")
        
        return instance_id
        
    except Exception as e:
        print(f"❌ Error creating bastion: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    create_bastion_manual()
