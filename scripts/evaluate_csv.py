#!/usr/bin/env python3
"""Evaluate the generated CSV file"""

import json
import pandas as pd
from pathlib import Path

# Read the CSV
csv_path = "test.csv"
df = pd.read_csv(csv_path)

print("=" * 70)
print("CSV FILE EVALUATION")
print("=" * 70)

# Basic info
print(f"\n[Basic Info]")
print(f"  Shape: {df.shape[0]} rows × {df.shape[1]} columns")
print(f"  Columns: {', '.join(df.columns)}")

# Schema validation
schema_file = "examples/example_schema_samples.json"
schema_data = json.load(open(schema_file))
schema = schema_data[0]  # First schema (hr_employees)

print(f"\n[Schema Match]")
print(f"  Expected schema: {schema['name']}")
expected_fields = {f["name"] for f in schema["fields"]}
actual_fields = set(df.columns)
print(f"  Expected fields: {sorted(expected_fields)}")
print(f"  Actual fields: {sorted(actual_fields)}")
print(f"  Match: {'OK' if expected_fields == actual_fields else 'FAIL'}")

# Field analysis
print(f"\n[Field Analysis]")

# employee_id
print(f"\n  1. employee_id (string, unique)")
print(f"     Unique values: {df['employee_id'].nunique()}/{len(df)}")
print(f"     Duplicates: {df['employee_id'].duplicated().sum()}")
print(f"     Sample values: {list(df['employee_id'].head(5))}")

# role
print(f"\n  2. role (category)")
role_counts = df['role'].value_counts().to_dict()
print(f"     Distribution:")
for role, count in sorted(role_counts.items()):
    pct = (count / len(df)) * 100
    print(f"       {role}: {count} ({pct:.1f}%)")
expected_roles = set(schema["fields"][1]["categories"])
actual_roles = set(df['role'].unique())
print(f"     Valid roles: {'OK' if actual_roles.issubset(expected_roles) else 'FAIL'}")
print(f"     Unexpected: {sorted(actual_roles - expected_roles) if actual_roles - expected_roles else 'None'}")

# salary
print(f"\n  3. salary (int)")
print(f"     Mean: {df['salary'].mean():,.0f}")
print(f"     Std: {df['salary'].std():,.0f}")
print(f"     Min: {df['salary'].min():,}")
print(f"     Max: {df['salary'].max():,}")
print(f"     Median: {df['salary'].median():,.0f}")
print(f"     Null values: {df['salary'].isnull().sum()}")

# start_date
print(f"\n  4. start_date (datetime)")
df['start_date_parsed'] = pd.to_datetime(df['start_date'], errors='coerce')
null_dates = df['start_date_parsed'].isnull().sum()
print(f"     Null values: {null_dates}")
if null_dates == 0:
    print(f"     Date range: {df['start_date_parsed'].min()} to {df['start_date_parsed'].max()}")
    print(f"     Valid format: OK")

# Data quality
print(f"\n[Data Quality]")
total_null = df.isnull().sum().sum()
print(f"  Total null values: {total_null}")
print(f"  Duplicate rows: {df.duplicated().sum()}")

# Summary
print(f"\n[Summary]")
issues = []
if df['employee_id'].duplicated().any():
    issues.append("Non-unique employee_ids")
if not actual_roles.issubset(expected_roles):
    issues.append("Invalid role values")
if null_dates > 0:
    issues.append("Invalid date values")
if total_null > 0:
    issues.append(f"{total_null} null values")

if issues:
    print(f"  Issues found: {len(issues)}")
    for issue in issues:
        print(f"    - {issue}")
else:
    print(f"  [OK] No major issues detected")

print("\n" + "=" * 70)

