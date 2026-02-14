"""
Relationship manager that merges join metadata from 4 sources:
1. FK constraints (from information_schema)
2. COMMENT ON [FK:] patterns (from pg_description)
3. YAML config file (relationships.yaml)
4. UI edits (saved to relationships.yaml)

Priority: UI/YAML overrides > COMMENT ON > FK constraints
"""
import os
import re
import yaml
from typing import Dict, List, Optional

YAML_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "relationships.yaml")
FK_PATTERN = re.compile(r'\[FK:\s*(\w+)\.(\w+)\]', re.IGNORECASE)


def _load_yaml(path: str = YAML_PATH) -> dict:
    if os.path.exists(path):
        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_yaml(data: dict, path: str = YAML_PATH):
    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def get_fk_relationships(execute_query_func, schema: str) -> List[dict]:
    """Source 1: FK constraints from information_schema."""
    try:
        rows = execute_query_func(
            "SELECT tc.table_name, kcu.column_name, ccu.table_name, ccu.column_name "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name "
            "JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name "
            "WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = %s",
            (schema,)
        )
        return [{"source_table": r[0], "source_column": r[1],
                 "target_table": r[2], "target_column": r[3],
                 "origin": "fk_constraint"} for r in (rows or [])]
    except:
        return []


def get_comment_relationships(execute_query_func, schema: str) -> List[dict]:
    """Source 2: Parse [FK: table.column] from COMMENT ON metadata."""
    try:
        rows = execute_query_func(
            "SELECT c.table_name, c.column_name, d.description "
            "FROM information_schema.columns c "
            "LEFT JOIN (SELECT cl.oid, cl.relname, ns.nspname FROM pg_catalog.pg_class cl "
            "JOIN pg_catalog.pg_namespace ns ON cl.relnamespace = ns.oid WHERE cl.relkind = 'r') t "
            "ON t.relname = c.table_name AND t.nspname = c.table_schema "
            "LEFT JOIN pg_catalog.pg_description d ON t.oid = d.objoid AND d.objsubid = c.ordinal_position "
            "WHERE c.table_schema = %s AND d.description IS NOT NULL",
            (schema,)
        )
        rels = []
        for table, col, desc in (rows or []):
            match = FK_PATTERN.search(desc)
            if match:
                rels.append({"source_table": table, "source_column": col,
                             "target_table": match.group(1), "target_column": match.group(2),
                             "origin": "comment_fk"})
        return rels
    except:
        return []


def get_yaml_relationships(schema: str) -> List[dict]:
    """Source 3 & 4: Relationships from YAML file (includes UI-saved ones)."""
    data = _load_yaml()
    rels = []
    for entry in data.get(schema, []):
        src_parts = entry["source"].split(".")
        tgt_parts = entry["target"].split(".")
        if len(src_parts) == 2 and len(tgt_parts) == 2:
            rels.append({"source_table": src_parts[0], "source_column": src_parts[1],
                         "target_table": tgt_parts[0], "target_column": tgt_parts[1],
                         "description": entry.get("description", ""),
                         "origin": "yaml"})
    return rels


def save_yaml_relationship(schema: str, source_table: str, source_col: str,
                           target_table: str, target_col: str, description: str = ""):
    """Save a relationship to YAML (used by UI)."""
    data = _load_yaml()
    if schema not in data:
        data[schema] = []
    entry = {"source": f"{source_table}.{source_col}",
             "target": f"{target_table}.{target_col}",
             "description": description}
    # Avoid duplicates
    for existing in data[schema]:
        if existing["source"] == entry["source"] and existing["target"] == entry["target"]:
            existing["description"] = description
            _save_yaml(data)
            return
    data[schema].append(entry)
    _save_yaml(data)


def delete_yaml_relationship(schema: str, source: str, target: str):
    """Delete a relationship from YAML."""
    data = _load_yaml()
    if schema in data:
        data[schema] = [e for e in data[schema]
                        if not (e["source"] == source and e["target"] == target)]
        _save_yaml(data)


def get_all_relationships(execute_query_func, schema: str) -> List[dict]:
    """Merge all 4 sources. YAML/UI overrides duplicates from other sources."""
    fk_rels = get_fk_relationships(execute_query_func, schema)
    comment_rels = get_comment_relationships(execute_query_func, schema)
    yaml_rels = get_yaml_relationships(schema)

    # Deduplicate: key = (source_table, source_column, target_table, target_column)
    seen = {}
    # Priority order: FK (lowest) -> comment -> yaml (highest)
    for rel in fk_rels + comment_rels + yaml_rels:
        key = (rel["source_table"], rel["source_column"],
               rel["target_table"], rel["target_column"])
        seen[key] = rel  # later entries override earlier ones
    return list(seen.values())


def build_relationship_map(relationships: List[dict], schema: str) -> Dict[str, List[str]]:
    """Convert relationship list to the fk_map format used by load_metadata."""
    fk_map = {}
    for rel in relationships:
        src_tbl = rel["source_table"]
        tgt_tbl = rel["target_table"]
        desc = rel.get("description", "")
        desc_suffix = f" ({desc})" if desc else ""

        fk_map.setdefault(src_tbl, []).append(
            f"{rel['source_column']} -> {schema}.{tgt_tbl}.{rel['target_column']}{desc_suffix}")
        fk_map.setdefault(tgt_tbl, []).append(
            f"Referenced by {schema}.{src_tbl}.{rel['source_column']}{desc_suffix}")
    return fk_map
