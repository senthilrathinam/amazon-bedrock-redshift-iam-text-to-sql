#!/usr/bin/env python3
"""
Setup IAM role for EC2 instance to run the application.
"""
import boto3
import json
import time

def create_iam_role_and_policy():
    """Create IAM role with all necessary permissions."""
    
    iam = boto3.client('iam')
    ec2 = boto3.client('ec2')
    
    role_name = 'BedrockRedshiftAnalystRole'
    policy_name = 'BedrockRedshiftAnalystPolicy'
    instance_profile_name = 'BedrockRedshiftAnalystProfile'
    
    # Trust policy for EC2
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Permissions policy
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:ListFoundationModels"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "redshift:DescribeClusters",
                    "redshift:CreateCluster",
                    "redshift:DeleteCluster",
                    "redshift:ModifyCluster"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:DescribeInstances",
                    "ec2:DescribeVpcs",
                    "ec2:DescribeSecurityGroups",
                    "ec2:CreateSecurityGroup",
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:AuthorizeSecurityGroupEgress",
                    "ec2:RunInstances",
                    "ec2:TerminateInstances"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "iam:CreateRole",
                    "iam:AttachRolePolicy",
                    "iam:CreateInstanceProfile",
                    "iam:AddRoleToInstanceProfile",
                    "iam:GetRole",
                    "iam:PassRole"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ssm:DescribeInstanceInformation",
                    "ssm:StartSession"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        # Create IAM role
        print("Creating IAM role...")
        try:
            iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description='Role for Bedrock Redshift Analyst application'
            )
            print(f"✅ Created role: {role_name}")
        except iam.exceptions.EntityAlreadyExistsException:
            print(f"✅ Role {role_name} already exists")
        
        # Create and attach policy
        print("Creating policy...")
        try:
            policy_response = iam.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(permissions_policy),
                Description='Policy for Bedrock Redshift Analyst application'
            )
            policy_arn = policy_response['Policy']['Arn']
            print(f"✅ Created policy: {policy_name}")
        except iam.exceptions.EntityAlreadyExistsException:
            # Get existing policy ARN
            account_id = boto3.client('sts').get_caller_identity()['Account']
            policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
            print(f"✅ Policy {policy_name} already exists")
        
        # Attach policy to role
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )
        print("✅ Attached policy to role")
        
        # Create instance profile
        try:
            iam.create_instance_profile(InstanceProfileName=instance_profile_name)
            print(f"✅ Created instance profile: {instance_profile_name}")
        except iam.exceptions.EntityAlreadyExistsException:
            print(f"✅ Instance profile {instance_profile_name} already exists")
        
        # Add role to instance profile
        try:
            iam.add_role_to_instance_profile(
                InstanceProfileName=instance_profile_name,
                RoleName=role_name
            )
            print("✅ Added role to instance profile")
        except iam.exceptions.LimitExceededException:
            print("✅ Role already in instance profile")
        
        # Wait for propagation
        print("Waiting for IAM propagation...")
        time.sleep(10)
        
        return instance_profile_name
        
    except Exception as e:
        print(f"❌ Error creating IAM resources: {e}")
        return None

def attach_role_to_instance(instance_id, instance_profile_name):
    """Attach IAM role to EC2 instance."""
    
    ec2 = boto3.client('ec2')
    
    try:
        # Check if instance already has a role
        response = ec2.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        
        if 'IamInstanceProfile' in instance:
            print(f"✅ Instance {instance_id} already has IAM role attached")
            return True
        
        # Attach the instance profile
        ec2.associate_iam_instance_profile(
            IamInstanceProfile={'Name': instance_profile_name},
            InstanceId=instance_id
        )
        
        print(f"✅ Attached IAM role to instance {instance_id}")
        print("⚠️  You may need to restart the EC2 instance for changes to take effect")
        return True
        
    except Exception as e:
        print(f"❌ Error attaching role to instance: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up IAM role for Bedrock Redshift Analyst...")
    
    # Create IAM resources
    instance_profile_name = create_iam_role_and_policy()
    
    if instance_profile_name:
        # Attach to your EC2 instance
        instance_id = "i-06a9a29e2fda7b461"
        success = attach_role_to_instance(instance_id, instance_profile_name)
        
        if success:
            print("\n🎉 Setup complete!")
            print("Next steps:")
            print("1. Restart your EC2 instance (optional but recommended)")
            print("2. Update application files to use IAM role authentication")
            print("3. Remove AWS credentials from .env file")
        else:
            print("\n❌ Failed to attach role to instance")
    else:
        print("\n❌ Failed to create IAM resources")
