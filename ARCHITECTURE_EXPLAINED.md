# Text-to-SQL Application Architecture - Deep Dive

## Overview
This application converts natural language questions into SQL queries using AI, executes them on Redshift, and provides intelligent analysis of results.

---

## Phase 1: Database Setup & Metadata Preparation

### 1.1 Northwind Database Loading
**File:** `src/utils/northwind_bootstrapper.py`

```
User starts app → Check if Northwind exists → If not, download & load sample data
```

**What happens:**
- Downloads SQLite Northwind database (customers, orders, products, etc.)
- Extracts and loads into Redshift `northwind` schema
- Creates 13 tables with realistic sales data (91 customers, 830 orders, etc.)

### 1.2 Schema Metadata Extraction
**File:** `app.py` → `load_all_metadata()`

**Critical Step:** The app creates a **text description** of the entire database schema:

```python
schema_text = """
Database: sales_analyst, Schema: northwind

Table: customers - Customer information
Columns: customerid (text), companyname (text), contactname (text), country (text)

Table: orders - Order information  
Columns: orderid (integer), customerid (text), orderdate (TEXT), freight (real)

Table: order_details - Order line items
Columns: orderid (integer), productid (integer), unitprice (real), quantity (integer)

... (all 13 tables described)
"""
```

**Why text format?** 
- AI models understand natural language better than raw SQL schemas
- Includes helpful hints (e.g., "date columns are TEXT, must CAST to DATE")
- Provides context about table relationships

---

## Phase 2: Vector Embedding & Indexing

### 2.1 Converting Schema to Vectors
**File:** `src/vector_store/faiss_manager.py`

**The Magic:** Schema text is converted to **numerical vectors** (embeddings)

```
Schema Text → Amazon Bedrock Titan Embeddings → 1536-dimensional vector
```

**Example:**
```
"Table: customers - Customer information, Columns: customerid, companyname..."
↓ (Bedrock Embeddings API)
[0.023, -0.145, 0.891, ..., 0.234]  (1536 numbers)
```

**Why vectors?**
- Captures semantic meaning (not just keywords)
- "customer name" and "company name" are mathematically similar
- Enables fast similarity search

### 2.2 FAISS Index Creation
**File:** `src/vector_store/faiss_manager.py`

```python
self.index = faiss.IndexFlatL2(dimension=1536)
self.index.add(embeddings_array)
```

**What is FAISS?**
- Facebook AI Similarity Search library
- Stores vectors in optimized data structure
- Enables lightning-fast nearest neighbor search

**Stored Data:**
```
Vector Index:
├── Vector 1: [0.023, -0.145, ...] → "customers table schema"
├── Vector 2: [0.891, 0.234, ...]  → "orders table schema"
├── Vector 3: [-0.456, 0.789, ...] → "products table schema"
└── ... (all table schemas)
```

---

## Phase 3: User Query Processing (The AI Workflow)

### 3.1 Query Understanding
**File:** `src/graph/workflow.py` → `understand_query()`

**User asks:** "What are the top 5 customers by order value?"

**AI analyzes:**
```json
{
  "type": "analysis",
  "data_sources": ["customers", "orders", "order_details"],
  "time_frame": "not specified",
  "metrics": ["order value", "top customers"]
}
```

**Purpose:** Understand intent before generating SQL

---

### 3.2 Context Retrieval (Semantic Search)
**File:** `src/graph/workflow.py` → `retrieve_context()`

**The Smart Part:**

1. **User query converted to vector:**
   ```
   "top 5 customers by order value"
   ↓ (Bedrock Embeddings)
   [0.456, -0.234, 0.789, ...]
   ```

2. **FAISS finds similar schema vectors:**
   ```python
   similar_docs = vector_store.similarity_search(query, k=5)
   ```

3. **Returns relevant table schemas:**
   ```
   Most Similar:
   1. "order_details table: orderid, productid, unitprice, quantity"
   2. "customers table: customerid, companyname, country"
   3. "orders table: orderid, customerid, orderdate"
   ```

**Why this matters:**
- AI only sees relevant tables (not all 13 tables)
- Reduces token usage and improves accuracy
- Knows which columns to JOIN on

---

### 3.3 SQL Generation
**File:** `src/graph/workflow.py` → `generate_sql()`

**AI receives:**
```
Question: "What are the top 5 customers by order value?"

Relevant Context:
- order_details: orderid, productid, unitprice, quantity
- customers: customerid, companyname, country
- orders: orderid, customerid, orderdate

Rules:
- Use schema.table format (northwind.customers)
- Calculate order value as (unitprice * quantity)
- Use subqueries for aggregations
```

**AI generates:**
```sql
SELECT 
    c.customerid, 
    c.companyname, 
    SUM(od.unitprice * od.quantity) as total_order_value
FROM northwind.customers c
JOIN northwind.orders o ON c.customerid = o.customerid
JOIN northwind.order_details od ON o.orderid = od.orderid
GROUP BY c.customerid, c.companyname
ORDER BY total_order_value DESC
LIMIT 5;
```

**Key Features:**
- Correct table joins (learned from context)
- Proper aggregation (SUM, not nested AVG)
- Schema-qualified names (northwind.customers)

---

### 3.4 Query Execution
**File:** `src/utils/redshift_connector.py`

```python
results = execute_query(generated_sql)
```

**Returns:**
```
[
  ('QUICK', 'QUICK-Stop', 110277.31),
  ('ERNSH', 'Ernst Handel', 104874.98),
  ('SAVEA', 'Save-a-lot Markets', 104361.95),
  ...
]
```

---

### 3.5 Result Analysis
**File:** `src/graph/workflow.py` → `analyze_results()`

**AI receives:**
```
Question: "What are the top 5 customers by order value?"

SQL Results:
QUICK-Stop: $110,277.31
Ernst Handel: $104,874.98
Save-a-lot Markets: $104,361.95
...

Analyze and explain these results.
```

**AI responds:**
```
The top 5 customers by total order value are:

1. QUICK-Stop leads with $110,277.31 in total orders
2. Ernst Handel follows closely at $104,874.98
3. Save-a-lot Markets rounds out the top 3 at $104,361.95

These three customers represent significant revenue concentration, 
accounting for approximately 15% of total sales...
```

---

## Key Technologies Explained

### Vector Embeddings
**What:** Convert text to numbers that capture meaning
**Why:** Enable semantic search (not just keyword matching)
**Example:**
- "customer name" and "company name" → similar vectors
- "order date" and "ship date" → similar vectors
- "customer" and "product" → different vectors

### FAISS (Vector Database)
**What:** Fast similarity search engine
**Why:** Find relevant schemas in milliseconds
**How:** Uses L2 distance (Euclidean) to measure similarity

### LangGraph Workflow
**What:** Multi-step AI pipeline
**Why:** Break complex task into manageable steps
**Steps:**
1. Understand query
2. Retrieve context
3. Generate SQL
4. Analyze results

---

## Data Flow Summary

```
User Question
    ↓
[1] Convert to vector → Search FAISS index → Get relevant schemas
    ↓
[2] Send to Bedrock: Question + Schemas → Generate SQL
    ↓
[3] Execute SQL on Redshift → Get results
    ↓
[4] Send to Bedrock: Question + Results → Generate analysis
    ↓
User sees: SQL + Results + AI Explanation
```

---

## Why This Architecture Works

1. **Semantic Understanding:** Vector search finds relevant tables even with different wording
2. **Context-Aware:** AI only sees relevant schemas, improving accuracy
3. **Scalable:** Works with any database size (only retrieves top-k relevant schemas)
4. **Explainable:** Shows SQL query, so users can verify logic
5. **Iterative:** Multi-step workflow allows error correction at each stage

---

## Performance Optimizations

1. **Vector Caching:** Schema embeddings computed once, reused forever
2. **FAISS Indexing:** Sub-millisecond similarity search
3. **Lazy Loading:** Metadata loaded only on first query
4. **Session State:** Streamlit caches components across requests

---

## Example: Full Trace

**User:** "Show me monthly sales trends for 1997"

**Step 1 - Understand:**
```json
{"type": "time_series", "metrics": ["sales"], "time_frame": "1997, monthly"}
```

**Step 2 - Retrieve Context:**
```
Vector search finds:
- orders table (has orderdate)
- order_details table (has unitprice, quantity)
```

**Step 3 - Generate SQL:**
```sql
SELECT 
    DATE_TRUNC('month', CAST(orderdate AS DATE)) as month,
    SUM(od.unitprice * od.quantity) as monthly_sales
FROM northwind.orders o
JOIN northwind.order_details od ON o.orderid = od.orderid
WHERE EXTRACT(YEAR FROM CAST(orderdate AS DATE)) = 1997
GROUP BY month
ORDER BY month;
```

**Step 4 - Execute & Analyze:**
```
Results show steady growth from $50K (Jan) to $75K (Dec)
AI explains: "Sales grew 50% throughout 1997, with peak in Q4..."
```

---

## Files Modified Summary

1. **app.py** - Main UI, metadata loading, cluster info display
2. **src/utils/redshift_cluster_manager.py** - Dynamic cluster ID extraction
3. **src/utils/redshift_connector.py** - Added missing database query functions
4. **src/graph/workflow.py** - AI workflow orchestration
5. **src/vector_store/faiss_manager.py** - Vector storage and similarity search

---

This architecture combines traditional database querying with modern AI techniques to create an intelligent, natural language interface to your data.
