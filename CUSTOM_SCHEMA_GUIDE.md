# Using Your Own Redshift Schema - Quick Guide

## Overview
The app now **automatically discovers and vectorizes ANY schema** you point it to. No manual configuration needed!

---

## How It Works

### 1. Automatic Schema Discovery
When you start the app, it:
1. Connects to your Redshift cluster
2. Queries `information_schema.tables` for all tables in your schema
3. Queries `information_schema.columns` for all columns in each table
4. Builds a text description of your entire schema
5. Converts it to vector embeddings
6. Stores in FAISS index for fast semantic search

### 2. What Gets Vectorized

For each table, the app captures:
- Table name
- All column names
- Data types (integer, text, date, etc.)
- Nullable status

**Example output:**
```
Database: mydb, Schema: sales

Table: customers
Columns: customer_id (integer), name (character varying), email (character varying), created_at (timestamp without time zone)

Table: orders
Columns: order_id (integer), customer_id (integer), order_date (date), total_amount (numeric)
```

This text is then converted to vectors for AI querying.

---

## Setup Instructions

### Step 1: Update Your .env File

```bash
# Point to your existing cluster
REDSHIFT_HOST=your-cluster.xxx.us-east-1.redshift.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DATABASE=your_database_name
REDSHIFT_SCHEMA=your_schema_name    # ← NEW: Specify your schema
REDSHIFT_USER=your_username
REDSHIFT_PASSWORD=your_password

# AWS credentials
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### Step 2: Restart the App

```bash
streamlit run app.py
```

### Step 3: Automatic Vectorization

The app will:
- ✅ Connect to your cluster
- ✅ Discover all tables in `your_schema_name`
- ✅ Extract column metadata
- ✅ Create vector embeddings
- ✅ Display: "Indexed X columns for AI querying"

**That's it!** No code changes needed.

---

## Example: Using Your Own Schema

### Scenario: E-commerce Database

**Your .env:**
```bash
REDSHIFT_DATABASE=ecommerce_prod
REDSHIFT_SCHEMA=public
```

**Your tables:**
- `users` (user_id, email, signup_date)
- `products` (product_id, name, price, category)
- `transactions` (transaction_id, user_id, product_id, amount, date)

**What happens:**
1. App discovers these 3 tables
2. Extracts all column info
3. Creates schema description
4. Vectorizes it
5. You can now ask: "What's the average transaction amount per user?"

**AI will:**
1. Search vectors for relevant tables (finds `transactions`, `users`)
2. Generate SQL with proper JOINs
3. Execute and analyze results

---

## Multiple Schemas?

Currently supports **one schema at a time**. To switch schemas:

1. Update `REDSHIFT_SCHEMA` in `.env`
2. Restart the app
3. New schema will be vectorized

**Future enhancement:** Support multiple schemas simultaneously by vectorizing each separately.

---

## Performance Considerations

### Small Schemas (< 50 tables)
- Vectorization takes ~5-10 seconds
- All tables indexed at once

### Large Schemas (50-500 tables)
- Vectorization takes ~30-60 seconds
- Still fast because it's one-time operation
- Queries remain instant (FAISS search is milliseconds)

### Very Large Schemas (500+ tables)
- Consider splitting into multiple schemas
- Or use table filtering (future feature)

---

## What If My Schema Changes?

The app caches metadata in session state. To refresh:

1. **Option 1:** Restart the app
2. **Option 2:** Clear browser cache and refresh
3. **Option 3:** Add a "Refresh Metadata" button (future feature)

---

## Troubleshooting

### "No tables found in schema 'xyz'"
- Check schema name spelling in `.env`
- Verify user has SELECT permission on `information_schema`
- Ensure schema exists: `SELECT * FROM information_schema.schemata;`

### "Error loading metadata"
- Check Redshift connection
- Verify credentials have read access
- Check firewall/security group rules

### Queries not working well
- Ensure table/column names are descriptive
- Add comments to tables in Redshift (future: will be included in vectors)
- Complex schemas may need manual hints in the schema text

---

## Advanced: Custom Schema Descriptions

Want to add hints for the AI? Edit `app.py` → `load_all_metadata()`:

```python
# Add custom hints
schema_parts.append("HINT: Use CAST(date_column AS DATE) for date operations\n")
schema_parts.append("HINT: customer_id is the primary key for customers table\n")
```

These hints will be vectorized and help the AI generate better SQL.

---

## Files Modified

1. **app.py** - Dynamic metadata loading function
2. **.env.example** - Added `REDSHIFT_SCHEMA` parameter

**To deploy:**
```bash
# Copy updated file to EC2
scp app.py ec2-user@<EC2_IP>:/path/to/app.py

# Update .env on EC2
nano .env
# Add: REDSHIFT_SCHEMA=your_schema_name

# Restart app
streamlit run app.py
```

---

## Summary

✅ **Automatic**: Just point to your cluster + schema
✅ **Fast**: One-time vectorization, instant queries
✅ **Flexible**: Works with any schema structure
✅ **Scalable**: Handles 10 to 500+ tables
✅ **No code changes**: Pure configuration

Your existing Redshift data is now AI-queryable!
