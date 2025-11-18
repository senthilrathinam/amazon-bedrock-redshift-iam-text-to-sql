# .env Configuration Guide

## Quick Setup

### **Step 1: Copy template**
```bash
cp .env.template .env
```

### **Step 2: Edit (optional)**
```bash
nano .env
```

### **Step 3: Done!**
The default values work perfectly for Option 1.

---

## What's in .env

### **Required:**
```bash
AWS_REGION=us-east-1
```

### **Optional (has default):**
```bash
REDSHIFT_PASSWORD=Awsuser123$
```

---

## Option 1 Defaults (Auto-Configured)

When you select **Option 1: Create New Cluster**, these values are automatically set:

| Setting | Default Value | Can Override? |
|---------|--------------|---------------|
| Cluster ID | `sales-analyst-cluster` | ❌ No |
| Database | `sales_analyst` | ❌ No |
| Schema | `northwind` | ❌ No |
| User | `admin` | ❌ No |
| Password | `Awsuser123$` | ✅ Yes |
| Host | `localhost` (via tunnel) | ❌ No |
| Port | `5439` | ❌ No |
| Node Type | `ra3.xlplus` | ❌ No |
| Public Access | `false` (private) | ❌ No |

---

## Why These Defaults?

### **Cluster ID: sales-analyst-cluster**
- Descriptive name
- Easy to identify
- Consistent across deployments

### **Database: sales_analyst**
- Matches the app purpose
- Clear naming convention

### **Schema: northwind**
- Standard sample database
- Well-known structure
- Perfect for demos

### **User: admin**
- Standard admin username
- Full permissions
- Simple to remember

### **Password: Awsuser123$**
- Meets AWS requirements
- Easy to remember
- Can be customized

### **Private Cluster**
- More secure
- Best practice
- Uses bastion host + SSM tunnel

---

## Customizing Password

If you want a different password:

```bash
# Edit .env
nano .env

# Change this line:
REDSHIFT_PASSWORD=MyCustomPass123!

# Requirements:
# - At least 8 characters
# - Must have uppercase letter
# - Must have lowercase letter
# - Must have number
# - Can have special characters: !@#$%^&*()
```

---

## For Options 2 & 3

If you're using **Option 2** or **Option 3**, you don't need to configure anything in `.env`.

You'll enter connection details in the UI:
- Cluster endpoint
- Database name
- Schema name
- Username
- Password

---

## Files Provided

| File | Purpose |
|------|---------|
| `.env.template` | Simple template to copy |
| `.env.option1` | Detailed reference with all defaults |
| `ENV_SETUP.md` | This guide |

---

## Example Setups

### **Minimal (uses all defaults):**
```bash
AWS_REGION=us-east-1
```

### **With custom password:**
```bash
AWS_REGION=us-east-1
REDSHIFT_PASSWORD=MySecurePass123!
```

---

## Verification

After creating `.env`, verify it's correct:

```bash
# Check file exists
ls -la .env

# View contents (safe - no secrets shown in this guide)
cat .env
```

---

## Troubleshooting

### **"File not found" error:**
```bash
# Make sure you're in the right directory
cd /usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql

# Create .env from template
cp .env.template .env
```

### **"Invalid password" error:**
- Check password meets requirements
- Must be 8+ characters
- Must have uppercase, lowercase, number

### **"Region not found" error:**
- Verify AWS_REGION is set
- Use valid region: us-east-1, us-west-2, etc.

---

## Summary

**For Option 1:**
1. Copy `.env.template` to `.env`
2. Optionally change password
3. Run the app
4. Everything else is automatic!

**Total configuration time: 30 seconds** ⚡
