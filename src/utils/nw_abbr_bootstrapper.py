"""
Bootstrapper for the nw_abbr (Northwind Abbreviated) schema.
Creates cryptic/abbreviated tables from existing northwind data,
adds COMMENT ON metadata (business glossary + [FK:] relationship hints).
"""
import traceback
import streamlit as st
from .redshift_connector_iam import get_redshift_connection

NW_ABBR_SCHEMA = "nw_abbr"

# Column mapping: northwind_table -> (abbr_table, [(nw_col, abbr_col), ...])
TABLE_MAP = {
    "categories": ("t_cat_ref", [
        ("categoryid", "cat_id"), ("categoryname", "cat_nm"),
        ("description", "cat_desc"), ("picture", "cat_pic"),
    ]),
    "customers": ("t_cust_mst", [
        ("customerid", "cust_id"), ("companyname", "cmpny_nm"),
        ("contactname", "cntct_nm"), ("contacttitle", "cntct_ttl"),
        ("address", "addr"), ("city", "cty"), ("region", "rgn"),
        ("postalcode", "pstl_cd"), ("country", "cntry_cd"),
        ("phone", "phn"), ("fax", "fx"),
    ]),
    "employees": ("t_emp_mst", [
        ("employeeid", "emp_id"), ("lastname", "lst_nm"),
        ("firstname", "frst_nm"), ("title", "ttl"),
        ("titleofcourtesy", "ttl_crtsy"), ("birthdate", "brth_dt"),
        ("hiredate", "hr_dt"), ("address", "addr"), ("city", "cty"),
        ("region", "rgn"), ("postalcode", "pstl_cd"),
        ("country", "cntry_cd"), ("homephone", "hm_phn"),
        ("extension", "ext"), ("photo", "pht"), ("notes", "nts"),
        ("reportsto", "rpts_to"), ("photopath", "pht_pth"),
    ]),
    "order_details": ("t_ord_dtl", [
        ("orderid", "ord_id"), ("productid", "prd_id"),
        ("unitprice", "unt_prc"), ("quantity", "qty"), ("discount", "dscnt"),
    ]),
    "orders": ("t_ord_hdr", [
        ("orderid", "ord_id"), ("customerid", "cust_id"),
        ("employeeid", "emp_id"), ("orderdate", "ord_dt"),
        ("requireddate", "req_dt"), ("shippeddate", "shp_dt"),
        ("shipvia", "shp_via"), ("freight", "frght"),
        ("shipname", "shp_nm"), ("shipaddress", "shp_addr"),
        ("shipcity", "shp_cty"), ("shipregion", "shp_rgn"),
        ("shippostalcode", "shp_pstl_cd"), ("shipcountry", "shp_cntry"),
    ]),
    "products": ("t_prd_mst", [
        ("productid", "prd_id"), ("productname", "prd_nm"),
        ("supplierid", "sup_id"), ("categoryid", "cat_id"),
        ("quantityperunit", "qty_per_unt"), ("unitprice", "unt_prc"),
        ("unitsinstock", "unts_stk"), ("unitsonorder", "unts_ord"),
        ("reorderlevel", "reord_lvl"), ("discontinued", "discont"),
    ]),
    "shippers": ("t_shp_ref", [
        ("shipperid", "shp_id"), ("companyname", "cmpny_nm"), ("phone", "phn"),
    ]),
    "suppliers": ("t_sup_mst", [
        ("supplierid", "sup_id"), ("companyname", "cmpny_nm"),
        ("contactname", "cntct_nm"), ("contacttitle", "cntct_ttl"),
        ("address", "addr"), ("city", "cty"), ("region", "rgn"),
        ("postalcode", "pstl_cd"), ("country", "cntry_cd"),
        ("phone", "phn"), ("fax", "fx"), ("homepage", "hmepg"),
    ]),
}

# Table-level COMMENT ON
TABLE_COMMENTS = {
    "t_cat_ref": "Product Categories Reference - Lookup table for product category classifications",
    "t_cust_mst": "Customer Master - Contains all customer records including company details, contacts, and addresses",
    "t_emp_mst": "Employee Master - Contains employee records including personal details, hire dates, and reporting structure",
    "t_ord_dtl": "Order Details / Line Items - Contains individual line items for each order with product, quantity, price, and discount",
    "t_ord_hdr": "Order Header - Contains order-level information including customer, employee, dates, and shipping details",
    "t_prd_mst": "Product Master - Contains product catalog with pricing, stock levels, and category/supplier references",
    "t_shp_ref": "Shipper Reference - Lookup table for shipping/carrier companies",
    "t_sup_mst": "Supplier Master - Contains supplier/vendor records including company details and contacts",
}

# Column-level COMMENT ON (includes [FK:] hints for relationships)
COLUMN_COMMENTS = {
    "t_cat_ref": {
        "cat_id": "Category ID - Unique identifier for the product category",
        "cat_nm": "Category Name - Display name of the product category (e.g., Beverages, Dairy Products)",
        "cat_desc": "Category Description - Detailed description of what products belong in this category",
        "cat_pic": "Category Picture - Image/photo path for the category",
    },
    "t_cust_mst": {
        "cust_id": "Customer ID - Unique identifier for the customer",
        "cmpny_nm": "Company Name - Official registered name of the customer company",
        "cntct_nm": "Contact Name - Primary contact person at the customer company",
        "cntct_ttl": "Contact Title - Job title of the primary contact",
        "addr": "Address - Street address of the customer",
        "cty": "City - City where the customer is located",
        "rgn": "Region - State/province/region of the customer",
        "pstl_cd": "Postal Code - ZIP/postal code of the customer",
        "cntry_cd": "Country - Country where the customer is located",
        "phn": "Phone - Customer phone number",
        "fx": "Fax - Customer fax number",
    },
    "t_emp_mst": {
        "emp_id": "Employee ID - Unique identifier for the employee",
        "lst_nm": "Last Name - Employee surname/family name",
        "frst_nm": "First Name - Employee given name",
        "ttl": "Title - Job title of the employee",
        "ttl_crtsy": "Title of Courtesy - Honorific (Mr., Ms., Dr., etc.)",
        "brth_dt": "Birth Date - Employee date of birth",
        "hr_dt": "Hire Date - Date the employee was hired",
        "addr": "Address - Employee home address",
        "cty": "City - City where the employee lives",
        "rgn": "Region - State/province/region of the employee",
        "pstl_cd": "Postal Code - Employee ZIP/postal code",
        "cntry_cd": "Country - Country where the employee is located",
        "hm_phn": "Home Phone - Employee home phone number",
        "ext": "Extension - Employee phone extension number",
        "pht": "Photo - Employee photo path",
        "nts": "Notes - Additional notes about the employee",
        "rpts_to": "Reports To - Employee ID of the manager this employee reports to [FK: t_emp_mst.emp_id]",
        "pht_pth": "Photo Path - File path to the employee photo",
    },
    "t_ord_dtl": {
        "ord_id": "Order ID - References the parent order in Order Header [FK: t_ord_hdr.ord_id]",
        "prd_id": "Product ID - References the product being ordered [FK: t_prd_mst.prd_id]",
        "unt_prc": "Unit Price - Price per unit at the time of the order",
        "qty": "Quantity - Number of units ordered",
        "dscnt": "Discount - Discount percentage applied to this line item (0.0 to 1.0)",
    },
    "t_ord_hdr": {
        "ord_id": "Order ID - Unique identifier for the order",
        "cust_id": "Customer ID - References the customer who placed the order [FK: t_cust_mst.cust_id]",
        "emp_id": "Employee ID - References the employee who processed the order [FK: t_emp_mst.emp_id]",
        "ord_dt": "Order Date - Date when the order was placed",
        "req_dt": "Required Date - Date by which the customer requested delivery",
        "shp_dt": "Shipped Date - Actual date the order was shipped",
        "shp_via": "Ship Via - References the shipping company used [FK: t_shp_ref.shp_id]",
        "frght": "Freight - Shipping cost/freight charges for the order",
        "shp_nm": "Ship Name - Name of the recipient for shipping",
        "shp_addr": "Ship Address - Delivery street address",
        "shp_cty": "Ship City - Delivery city",
        "shp_rgn": "Ship Region - Delivery state/province/region",
        "shp_pstl_cd": "Ship Postal Code - Delivery ZIP/postal code",
        "shp_cntry": "Ship Country - Delivery country",
    },
    "t_prd_mst": {
        "prd_id": "Product ID - Unique identifier for the product",
        "prd_nm": "Product Name - Display name of the product",
        "sup_id": "Supplier ID - References the supplier/vendor of this product [FK: t_sup_mst.sup_id]",
        "cat_id": "Category ID - References the product category [FK: t_cat_ref.cat_id]",
        "qty_per_unt": "Quantity Per Unit - Description of the product packaging (e.g., 24 bottles x 250ml)",
        "unt_prc": "Unit Price - Current list price per unit",
        "unts_stk": "Units In Stock - Current inventory quantity",
        "unts_ord": "Units On Order - Quantity currently on order from supplier",
        "reord_lvl": "Reorder Level - Minimum stock level that triggers a reorder",
        "discont": "Discontinued - Whether the product is discontinued (1=yes, 0=no)",
    },
    "t_shp_ref": {
        "shp_id": "Shipper ID - Unique identifier for the shipping company",
        "cmpny_nm": "Company Name - Name of the shipping/carrier company",
        "phn": "Phone - Shipper phone number",
    },
    "t_sup_mst": {
        "sup_id": "Supplier ID - Unique identifier for the supplier",
        "cmpny_nm": "Company Name - Official name of the supplier company",
        "cntct_nm": "Contact Name - Primary contact person at the supplier",
        "cntct_ttl": "Contact Title - Job title of the supplier contact",
        "addr": "Address - Supplier street address",
        "cty": "City - City where the supplier is located",
        "rgn": "Region - State/province/region of the supplier",
        "pstl_cd": "Postal Code - Supplier ZIP/postal code",
        "cntry_cd": "Country - Country where the supplier is located",
        "phn": "Phone - Supplier phone number",
        "fx": "Fax - Supplier fax number",
        "hmepg": "Homepage - Supplier website URL",
    },
}


def check_nw_abbr_exists():
    """Check if nw_abbr schema and tables already exist with data."""
    try:
        conn = get_redshift_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'nw_abbr' AND table_type = 'BASE TABLE'")
        count = cur.fetchone()[0]
        if count < 8:
            return False
        cur.execute("SELECT COUNT(*) FROM nw_abbr.t_ord_hdr")
        rows = cur.fetchone()[0]
        conn.close()
        return rows > 0
    except:
        return False


def bootstrap_nw_abbr(northwind_schema="northwind", show_progress=False):
    """Create nw_abbr schema from existing northwind data with full COMMENT ON metadata."""
    if show_progress:
        progress = st.progress(0, text="Creating abbreviated schema...")

    conn = get_redshift_connection()
    try:
        cur = conn.cursor()

        # 1. Create schema
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {NW_ABBR_SCHEMA}")
        conn.commit()
        if show_progress:
            progress.progress(0.1, text="Schema created...")

        # 2. Create tables and copy data from northwind
        tables = list(TABLE_MAP.items())
        for i, (nw_table, (abbr_table, col_map)) in enumerate(tables):
            cur.execute(f"DROP TABLE IF EXISTS {NW_ABBR_SCHEMA}.{abbr_table}")

            # Build SELECT with column aliases
            select_cols = ", ".join(f"{nw} AS {abbr}" for nw, abbr in col_map)
            cur.execute(f"CREATE TABLE {NW_ABBR_SCHEMA}.{abbr_table} AS SELECT {select_cols} FROM {northwind_schema}.{nw_table}")
            conn.commit()

            pct = 0.1 + (0.6 * (i + 1) / len(tables))
            if show_progress:
                progress.progress(pct, text=f"Created {abbr_table}...")

        # 3. Add table-level COMMENT ON
        for abbr_table, comment in TABLE_COMMENTS.items():
            cur.execute(f"COMMENT ON TABLE {NW_ABBR_SCHEMA}.{abbr_table} IS %s", (comment,))
        conn.commit()
        if show_progress:
            progress.progress(0.8, text="Added table comments...")

        # 4. Add column-level COMMENT ON (with [FK:] hints)
        for abbr_table, cols in COLUMN_COMMENTS.items():
            for col, comment in cols.items():
                cur.execute(f"COMMENT ON COLUMN {NW_ABBR_SCHEMA}.{abbr_table}.{col} IS %s", (comment,))
        conn.commit()
        if show_progress:
            progress.progress(0.95, text="Added column comments with relationship hints...")

        conn.close()

        if show_progress:
            progress.progress(1.0, text="Done!")
        return True

    except Exception as e:
        conn.close()
        if show_progress:
            st.error(f"❌ Error: {e}")
        traceback.print_exc()
        return False
