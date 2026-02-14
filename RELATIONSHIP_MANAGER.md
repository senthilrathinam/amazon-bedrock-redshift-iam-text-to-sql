# Relationship Manager — User Guide

## Why This Exists

When you ask a natural language question like *"What are the top 5 products by total quantity ordered?"*, the AI needs to generate SQL that JOINs the `products` table with the `order_details` table. To write the correct JOIN condition (`products.productid = order_details.productid`), the AI needs to **know** that these two columns are related.

In traditional databases, this information comes from **foreign key (FK) constraints** defined on the tables:

```sql
ALTER TABLE order_details ADD FOREIGN KEY (productid) REFERENCES products(productid);
```

**The problem:** Many data warehouses — especially Amazon Redshift — don't enforce or even define these constraints. Redshift treats PK/FK as informational only, so teams often skip them entirely. This means:

- The database has **no metadata** describing how tables relate to each other
- The AI has to **guess** join conditions from column names alone
- With descriptive names (`orders.customerid` → `customers.customerid`), guessing often works
- With cryptic/abbreviated names (`t_ord_hdr.cust_id` → `t_cust_mst.cust_id`), guessing fails

**Real example from this project:** Both the `northwind` and `nw_abbr` schemas in this application have **zero constraints** — no primary keys, no foreign keys, no unique constraints. Yet every multi-table query requires correct JOINs across 2-5 tables.

## What the Relationship Manager Does

The Relationship Manager solves this by collecting table relationship information from **4 sources** and merging them into a single, deduplicated set of join mappings that the AI uses when generating SQL.

### The 4 Sources (in priority order, lowest to highest)

```
┌─────────────────────────────────────────────────────────────────┐
│                    RELATIONSHIP SOURCES                         │
│                                                                 │
│  Priority 1 (lowest):  FK Constraints                          │
│  ✅ Auto-discovered from information_schema                     │
│  If your tables have FK constraints defined, they're picked     │
│  up automatically. No action needed.                            │
│                                                                 │
│  Priority 2:  COMMENT ON [FK:] Patterns                        │
│  📝 Parsed from Redshift column comments                        │
│  Add [FK: target_table.target_column] to any column comment     │
│  and the relationship is auto-detected during indexing.          │
│                                                                 │
│  Priority 3:  relationships.yaml File                           │
│  🔧 Version-controlled config file in the project root          │
│  Define relationships in YAML for teams that manage config      │
│  in Git. Loaded at indexing time.                                │
│                                                                 │
│  Priority 4 (highest):  UI Edits                                │
│  🔧 Added via the Streamlit sidebar panel                       │
│  Saved to the same relationships.yaml file. Overrides all       │
│  other sources if there's a duplicate.                           │
└─────────────────────────────────────────────────────────────────┘
```

When the same relationship exists in multiple sources (e.g., both COMMENT ON and YAML define `orders.customerid → customers.customerid`), the **higher priority source wins**. This means you can override auto-discovered relationships with manual ones if needed.

## How It Works Behind the Scenes

When the application indexes your schema (during setup or when you click "Re-index Schema"), this is what happens:

```
1. Query information_schema for FK constraints
   └─ Found: 0 (typical for Redshift)

2. Query pg_description for column comments containing [FK: ...]
   └─ Found: 8 (if you added [FK:] hints to comments)

3. Load relationships.yaml from project root
   └─ Found: 8 (pre-configured for northwind and nw_abbr)

4. Merge all sources, deduplicate by (source_table, source_col, target_table, target_col)
   └─ Result: 8 unique relationships (YAML wins on duplicates)

5. Build relationship map and inject into each table's FAISS document:

   BEFORE (without Relationship Manager):
   ┌──────────────────────────────────────────────────────────┐
   │ Schema: nw_abbr, Table: nw_abbr.t_ord_hdr               │
   │ Columns: ord_id (Order ID, integer) | cust_id            │
   │ (Customer ID - References the customer, varchar) | ...   │
   └──────────────────────────────────────────────────────────┘
   The AI sees column descriptions but has no explicit join paths.

   AFTER (with Relationship Manager):
   ┌──────────────────────────────────────────────────────────┐
   │ Schema: nw_abbr, Table: nw_abbr.t_ord_hdr               │
   │ Columns: ord_id (Order ID, integer) | cust_id            │
   │ (Customer ID - References the customer, varchar) | ...   │
   │ Relationships: cust_id -> nw_abbr.t_cust_mst.cust_id    │
   │ (Order placed by customer); emp_id ->                    │
   │ nw_abbr.t_emp_mst.emp_id (Order processed by employee); │
   │ Referenced by nw_abbr.t_ord_dtl.ord_id (Line item        │
   │ belongs to order)                                        │
   └──────────────────────────────────────────────────────────┘
   The AI now has explicit, unambiguous join paths.

6. These enriched documents are embedded and stored in the FAISS vector store.
   When a user asks a question, semantic search retrieves the relevant tables
   WITH their relationship metadata, and the AI generates correct JOINs.
```

## How to Use It

### Scenario 1: You have descriptive column names (like `northwind`)

Tables have names like `customers`, `orders`, `products` with columns like `customerid`, `orderid`, `productid`.

**What to do:** Add entries to `relationships.yaml` in the project root:

```yaml
northwind:
  - source: orders.customerid
    target: customers.customerid
    description: "Order placed by customer"
  - source: order_details.orderid
    target: orders.orderid
    description: "Line item belongs to order"
  - source: order_details.productid
    target: products.productid
    description: "Line item references product"
```

**Why it helps:** Even though the AI can often guess these joins from column names, providing explicit relationships eliminates guesswork. The AI won't accidentally join on the wrong column when multiple tables have similar column names.

### Scenario 2: You have cryptic/abbreviated names (like `nw_abbr`)

Tables have names like `t_ord_hdr`, `t_cust_mst`, `t_prd_mst` with columns like `cust_id`, `prd_id`, `shp_via`.

**What to do:** You have three options (use any combination):

**Option A — Add `[FK:]` hints to Redshift column comments:**

```sql
COMMENT ON COLUMN nw_abbr.t_ord_hdr.cust_id IS 
  'Customer ID - References the customer who placed the order [FK: t_cust_mst.cust_id]';

COMMENT ON COLUMN nw_abbr.t_ord_dtl.prd_id IS 
  'Product ID - References the product being ordered [FK: t_prd_mst.prd_id]';

COMMENT ON COLUMN nw_abbr.t_prd_mst.cat_id IS 
  'Category ID - References the product category [FK: t_cat_ref.cat_id]';
```

The `[FK: table.column]` pattern is automatically parsed during schema indexing. The rest of the comment (before the `[FK:]` tag) serves as the business glossary description.

**Option B — Add entries to `relationships.yaml`:**

```yaml
nw_abbr:
  - source: t_ord_hdr.cust_id
    target: t_cust_mst.cust_id
    description: "Order placed by customer"
  - source: t_ord_dtl.ord_id
    target: t_ord_hdr.ord_id
    description: "Line item belongs to order"
```

**Option C — Use the Streamlit UI:**

1. Open the app and connect to your schema
2. In the sidebar, scroll to **🔗 Manage Relationships**
3. You'll see all currently detected relationships with origin badges:
   - ✅ = from FK constraints in the database
   - 📝 = from `COMMENT ON` metadata with `[FK:]` pattern
   - 🔧 = from `relationships.yaml` or UI edits
4. Expand **➕ Add Relationship**
5. Select source table → source column → target table → target column from the dropdowns
6. Add an optional description (e.g., "Order placed by customer")
7. Click **Add Relationship** — the schema re-indexes automatically
8. Your new relationship is saved to `relationships.yaml` and takes effect immediately

### Scenario 3: Only a subject matter expert (SME) knows the join logic

This is the hardest case. Tables like `t_inv.c_ref_01` need to join to `t_cust.c_id`, but nothing in the column names, data types, or existing comments reveals this.

**What to do:** The SME needs to provide the mapping once, using any of the three methods above. The recommended approach:

1. Have the SME fill out a simple spreadsheet:

   | Source Table | Source Column | Target Table | Target Column | Description |
   |---|---|---|---|---|
   | t_inv | c_ref_01 | t_cust | c_id | Invoice customer reference |
   | t_inv | c_prod_ref | t_prod | c_prod_id | Invoice product reference |

2. Convert to `relationships.yaml` format and commit to the repo
3. Or have the SME use the UI directly — it saves to the same YAML file

Once defined, these relationships persist across app restarts and are version-controllable in Git.

## Example: What Happens Without vs. With the Relationship Manager

**Question:** *"Which employees generated the most revenue by country, including the product categories they sold?"*

This question requires JOINing 5 tables: employees → orders → order_details → products → categories.

### Without Relationship Manager (cryptic schema `nw_abbr`)

The AI receives this context for `t_ord_hdr`:
```
Schema: nw_abbr, Table: nw_abbr.t_ord_hdr (Order Header)
Columns: ord_id (Order ID, integer) | cust_id (Customer ID, varchar) | emp_id (Employee ID, integer) | ...
```

No `Relationships:` section. The AI must guess that `emp_id` joins to `t_emp_mst.emp_id`. With cryptic names, it might:
- Join on the wrong column
- Miss a table entirely
- Generate invalid SQL

### With Relationship Manager (cryptic schema `nw_abbr`)

The AI receives this enriched context:
```
Schema: nw_abbr, Table: nw_abbr.t_ord_hdr (Order Header)
Columns: ord_id (Order ID, integer) | cust_id (Customer ID, varchar) | emp_id (Employee ID, integer) | ...
Relationships: cust_id -> nw_abbr.t_cust_mst.cust_id (Order placed by customer);
  emp_id -> nw_abbr.t_emp_mst.emp_id (Order processed by employee);
  shp_via -> nw_abbr.t_shp_ref.shp_id (Order shipped via carrier);
  Referenced by nw_abbr.t_ord_dtl.ord_id (Line item belongs to order)
```

The AI now generates correct SQL with a 5-table JOIN chain:
```sql
SELECT e.emp_id, e.cntry_cd, c.cat_nm, SUM(od.unt_prc * od.qty * (1 - od.dscnt)) as revenue
FROM nw_abbr.t_emp_mst e
JOIN nw_abbr.t_ord_hdr oh ON e.emp_id = oh.emp_id        -- from Relationships
JOIN nw_abbr.t_ord_dtl od ON oh.ord_id = od.ord_id        -- from Relationships
JOIN nw_abbr.t_prd_mst p ON od.prd_id = p.prd_id          -- from Relationships
JOIN nw_abbr.t_cat_ref c ON p.cat_id = c.cat_id           -- from Relationships
GROUP BY e.emp_id, e.cntry_cd, c.cat_nm
ORDER BY revenue DESC;
```

Every JOIN condition came directly from the relationship metadata — no guessing.

## Files Reference

| File | Purpose |
|---|---|
| `src/utils/relationship_manager.py` | Core module — merges 4 sources, builds relationship map |
| `relationships.yaml` | Config file — define relationships here or let the UI save them |
| `app.py` (sidebar panel) | UI — view, add, delete relationships; re-index schema |
| `test_relationships.py` | End-to-end test — validates all sample queries on both schemas |

## Quick Start Checklist

1. ☐ Check if your tables have FK constraints (most Redshift tables don't)
2. ☐ If no FK constraints, add relationships via one of:
   - `[FK: table.column]` in Redshift `COMMENT ON` metadata
   - Entries in `relationships.yaml`
   - The **🔗 Manage Relationships** panel in the sidebar
3. ☐ Click **🔄 Re-index Schema** after making changes
4. ☐ Test with sample questions to verify JOINs are correct
5. ☐ Commit `relationships.yaml` to version control for your team
