import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics import (
    monthly_summary,
    member_spend_breakdown,
    category_spend_breakdown,
    budget_status,
    spending_trend
)

TEST_MONTH = '2026-05'
TEST_MEMBER_ID = 1

print("\n" + "="*50)
print("1. MONTHLY SUMMARY")
print("="*50)
result = monthly_summary(TEST_MONTH)
print(result)

print("\n" + "="*50)
print("2. MEMBER SPEND BREAKDOWN")
print("="*50)
result = member_spend_breakdown(TEST_MONTH)
for row in result:
    print(row)

print("\n" + "="*50)
print("3. CATEGORY SPEND BREAKDOWN")
print("="*50)
result = category_spend_breakdown(TEST_MONTH)
for row in result:
    print(row)

print("\n" + "="*50)
print("4. BUDGET STATUS")
print("="*50)
result = budget_status(TEST_MONTH)
for row in result:
    print(row)

print("\n" + "="*50)
print("5. SPENDING TREND - Member 1")
print("="*50)
result = spending_trend(TEST_MEMBER_ID, 6)
for row in result:
    print(row)