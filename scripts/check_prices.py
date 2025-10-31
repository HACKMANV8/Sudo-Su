#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('ecommerce_v2.csv')
print("PRICE BY CATEGORY:")
print("=" * 70)
print("\nAverage purchase amount by category:")
for cat in sorted(df['product_category'].unique()):
    subset = df[df['product_category'] == cat]['purchase_amount']
    print(f"  {cat:15s}: Mean=${subset.mean():.2f}, Std=${subset.std():.2f}, Range=${subset.min():.2f}-${subset.max():.2f}")

print("\nDetailed breakdown:")
print(df.groupby('product_category')['purchase_amount'].agg(['mean', 'std', 'min', 'max']).round(2))

print("\nExpected pattern:")
print("  Electronics should be most expensive (~$800)")
print("  Food should be cheapest (~$50)")
print("  Clothing should be mid-range (~$150)")

