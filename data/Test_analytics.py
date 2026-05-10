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

#---------------------------------------
# Testing Calclulations
#---------------------------------------
from src.calculations import (
    compare_months,
    compare_members,
    daily_average,
    weekly_average,
    overall_monthly_average,
    category_percentage,
    savings_rate,
    running_balance,
    net_worth
)

TEST_MONTH2 = '2026-04'
TEST_ACCOUNT_ID = 1
TEST_CATEGORY_ID = 7  # Grocery

print("\n" + "="*50)
print("6. COMPARE MONTHS")
print("="*50)
result = compare_months(TEST_MONTH2, TEST_MONTH)
print(result)

print("\n" + "="*50)
print("7. COMPARE MEMBERS")
print("="*50)
result = compare_members(TEST_MONTH)
for row in result:
    print(row)

print("\n" + "="*50)
print("8. DAILY AVERAGE - Member 1")
print("="*50)
result = daily_average(TEST_MEMBER_ID, TEST_MONTH)
print(f"Daily average: {result}")

print("\n" + "="*50)
print("9. WEEKLY AVERAGE - Member 1")
print("="*50)
result = weekly_average(TEST_MEMBER_ID, TEST_MONTH)
print(f"Weekly average: {result}")

print("\n" + "="*50)
print("10. OVERALL MONTHLY AVERAGE - Member 1")
print("="*50)
result = overall_monthly_average(TEST_MEMBER_ID)
print(f"Overall monthly average: {result}")

print("\n" + "="*50)
print("11. CATEGORY PERCENTAGE - Grocery")
print("="*50)
result = category_percentage(TEST_CATEGORY_ID, TEST_MONTH)
print(f"Grocery % of total spend: {result}%")

print("\n" + "="*50)
print("12. SAVINGS RATE")
print("="*50)
result = savings_rate(TEST_MONTH)
print(f"Savings rate: {result}%")

print("\n" + "="*50)
print("13. RUNNING BALANCE - SBI Savings")
print("="*50)
result = running_balance(TEST_ACCOUNT_ID)
for row in result:
    print(row)

print("\n" + "="*50)
print("14. NET WORTH")
print("="*50)
result = net_worth()
print(f"Total net worth: {result}")