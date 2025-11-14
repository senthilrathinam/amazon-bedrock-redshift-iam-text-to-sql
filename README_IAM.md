# Amazon Bedrock & Amazon Redshift Sales Analyst (IAM Authentication)

**Enhanced version with IAM role-based authentication for secure EC2 deployment**

## 🎯 Key Features

- ✅ **IAM Role Authentication** - No AWS credentials needed
- ✅ **EC2 Optimized** - Designed for production EC2 deployment
- ✅ **Enhanced Security** - No access keys or tokens in configuration
- ✅ **Auto Setup** - One-command IAM role creation and attachment
- ✅ **Production Ready** - Follows AWS security best practices

## 🚀 Quick Start

### Prerequisites
- EC2 instance (t3.medium or larger, 30GB storage)
- IAM permissions to create roles and attach to EC2
- Python 3.11+

### Installation

```bash
# Clone the repository
git clone https://github.com/senthilrathinam/amazon-bedrock-redshift-iam-text-to-sql.git
cd amazon-bedrock-redshift-iam-text-to-sql

# Run complete setup (creates IAM role, attaches to EC2, migrates files)
python setup_iam_complete.py

# Start the application
streamlit run app.py
```

## 🔧 Configuration

Only Redshift connection details needed in `.env`:

```bash
AWS_REGION=us-east-1
REDSHIFT_HOST=localhost
REDSHIFT_PORT=5439
REDSHIFT_DATABASE=sales_analyst
REDSHIFT_USER=admin
REDSHIFT_PASSWORD=Awsuser123$
```

**No AWS credentials required!** The application uses the EC2 instance's IAM role.

## 🏗️ Architecture

```
EC2 Instance (with IAM Role)
    ↓
IAM Role → Bedrock API (Claude 3 Sonnet, Titan Embed)
    ↓
SSM Tunnel → Bastion Host → Private Redshift Cluster
```

## 📋 What's Different from Original?

| Feature | Original | IAM Version |
|---------|----------|-------------|
| Authentication | Access Keys + Secret + Token | IAM Role |
| Credential Management | Manual .env file | Automatic |
| Security | Credentials in files | Instance Profile |
| Token Expiration | Yes (1-12 hours) | No expiration |
| Setup Complexity | Manual credential rotation | One-time setup |

## 🔐 IAM Permissions

The setup script creates a role with these permissions:
- `bedrock:InvokeModel` - For AI/ML operations
- `redshift:*` - For cluster management
- `ec2:*` - For bastion host creation
- `ssm:*` - For secure tunneling

## 📚 Documentation

For detailed application functionality, see [README.md](README.md)

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a PR.

## 📄 License

MIT-0 License - See LICENSE file for details.

## 🙏 Credits

Based on the original [Amazon Bedrock Redshift Text-to-SQL POC](https://github.com/aws-samples/genai-quickstart-pocs)

Enhanced with IAM role authentication by Senthil Kamala Rathinam
