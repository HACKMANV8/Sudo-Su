#!/usr/bin/env python3
"""Evaluate the e-commerce fraud dataset"""

import pandas as pd

df = pd.read_csv('ecommerce_transactions.csv')

print("=" * 70)
print("ECOMMERCE FRAUD DATASET EVALUATION")
print("=" * 70)

print(f"\n[Basic Info]")
print(f"  Shape: {df.shape[0]} rows × {df.shape[1]} columns")
print(f"  Columns: {', '.join(df.columns)}")

print(f"\n[Sample Data]")
print(df.head(10))

print(f"\n[Field Statistics]")
print(f"\n1. customer_age:")
print(f"   Mean: {df['customer_age'].mean():.1f}")
print(f"   Std: {df['customer_age'].std():.1f}")
print(f"   Range: {df['customer_age'].min()} - {df['customer_age'].max()}")

print(f"\n2. purchase_amount:")
print(f"   Mean: ${df['purchase_amount'].mean():.2f}")
print(f"   Std: ${df['purchase_amount'].std():.2f}")
print(f"   Range: ${df['purchase_amount'].min():.2f} - ${df['purchase_amount'].max():.2f}")
print(f"   Median: ${df['purchase_amount'].median():.2f}")

print(f"\n3. product_category distribution:")
cat_dist = df['product_category'].value_counts()
for cat, count in cat_dist.items():
    print(f"   {cat}: {count} ({count/len(df)*100:.1f}%)")

print(f"\n4. payment_method distribution:")
pay_dist = df['payment_method'].value_counts()
for pm, count in pay_dist.items():
    print(f"   {pm}: {count} ({count/len(df)*100:.1f}%)")

print(f"\n5. is_fraud (fraud detection label):")
fraud_count = df['is_fraud'].sum()
print(f"   Fraud cases: {fraud_count} ({fraud_count/len(df)*100:.1f}%)")
print(f"   Legitimate: {len(df) - fraud_count} ({(len(df) - fraud_count)/len(df)*100:.1f}%)")

print(f"\n6. transaction_time:")
df['transaction_time'] = pd.to_datetime(df['transaction_time'])
print(f"   Date range: {df['transaction_time'].min()} to {df['transaction_time'].max()}")

print(f"\n7. transaction_id (uniqueness):")
print(f"   Unique IDs: {df['transaction_id'].nunique()}/{len(df)}")
print(f"   Duplicates: {df['transaction_id'].duplicated().sum()}")

# Fraud patterns
print(f"\n[Fraud Patterns]")
fraud_df = df[df['is_fraud'] == 1]
if len(fraud_df) > 0:
    print(f"   Average fraud amount: ${fraud_df['purchase_amount'].mean():.2f}")
    print(f"   Average fraud customer age: {fraud_df['customer_age'].mean():.1f}")
    print(f"   Top fraud categories:")
    fraud_cats = fraud_df['product_category'].value_counts().head(3)
    for cat, count in fraud_cats.items():
        print(f"      {cat}: {count}")

print("\n" + "=" * 70)

