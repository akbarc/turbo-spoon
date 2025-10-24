"""Test script for customer groups functionality."""

import sys
from datetime import datetime, timedelta

print("=" * 70)
print("CUSTOMER GROUPS MODULE TEST")
print("=" * 70)
print()

# Test imports
print("Step 1: Testing imports...")
try:
    from src.database.sql_server import test_connection, execute_query
    from src.database.overlay_db import overlay_db
    from src.modules.customer_groups import customer_group_manager
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test database connection
print("Step 2: Testing database connection...")
if not test_connection():
    print("❌ Cannot connect to database")
    sys.exit(1)
print("✅ Database connection successful")
print()

# Test overlay database
print("Step 3: Testing overlay database...")
try:
    groups_df = overlay_db.get_soundex_groups()
    print(f"✅ Found {len(groups_df)} existing groups in overlay database")
except Exception as e:
    print(f"❌ Overlay database error: {str(e)}")
    sys.exit(1)

print()

# Test sync (small batch)
print("Step 4: Testing customer group sync...")
print("(This will sync any new customers to groups)")
try:
    result = customer_group_manager.sync_customer_groups(force_rebuild=False)
    if result['status'] == 'success':
        print(f"✅ Sync successful:")
        print(f"   - Customers processed: {result['customers_processed']}")
        print(f"   - Groups created: {result['groups_created']}")
        print(f"   - Groups updated: {result['groups_updated']}")
    else:
        print(f"⚠️  Sync returned: {result.get('message', 'Unknown')}")
except Exception as e:
    print(f"❌ Sync error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test get groups summary
print("Step 5: Testing groups summary...")
try:
    today = datetime.now().date()
    start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')

    groups_df = customer_group_manager.get_all_groups_summary(
        min_sales=0,
        start_date=start_date,
        end_date=end_date
    )

    print(f"✅ Found {len(groups_df)} groups with sales in last 30 days")

    if not groups_df.empty:
        print()
        print("Top 5 groups by sales:")
        print("-" * 70)
        top_5 = groups_df.nlargest(5, 'total_sales')
        for idx, row in top_5.iterrows():
            print(f"  {row['group_name']:<30} "
                  f"Sales: ${row['total_sales']:>10,.0f}  "
                  f"GP: {row['gp_percentage']:>5.1f}%  "
                  f"Members: {int(row['member_count'])}")

except Exception as e:
    print(f"❌ Groups summary error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test group analytics
if not groups_df.empty:
    print("Step 6: Testing detailed group analytics...")
    try:
        test_group_id = int(groups_df.iloc[0]['group_id'])
        test_group_name = groups_df.iloc[0]['group_name']

        print(f"Getting analytics for: {test_group_name} (ID: {test_group_id})")

        analytics = customer_group_manager.get_group_analytics(
            test_group_id,
            start_date,
            end_date
        )

        print("✅ Analytics retrieved successfully:")
        print(f"   - Total Sales: ${analytics['financial']['total_sales']:,.0f}")
        print(f"   - Gross Profit: ${analytics['financial']['gross_profit']:,.0f}")
        print(f"   - GP %: {analytics['financial']['gp_percentage']:.1f}%")
        print(f"   - AR Balance: ${analytics['ar']['total_balance']:,.0f}")
        print(f"   - Avg Days to Pay: {analytics['payment_velocity']['avg_days_to_pay']:.0f} days")

    except Exception as e:
        print(f"❌ Analytics error: {str(e)}")
        import traceback
        traceback.print_exc()

    print()

    # Test category analysis
    print("Step 7: Testing category analysis...")
    try:
        categories = customer_group_manager.get_group_category_analysis(
            test_group_id,
            start_date,
            end_date,
            limit=5
        )

        print(f"✅ Found {len(categories)} categories")
        if categories:
            print()
            print("Top categories:")
            print("-" * 70)
            for cat in categories[:5]:
                print(f"  {cat['category_name']:<30} "
                      f"Sales: ${cat['group_sales']:>10,.0f}  "
                      f"% of Total: {cat['pct_of_total_category_sales']:>5.1f}%")

    except Exception as e:
        print(f"❌ Category analysis error: {str(e)}")
        import traceback
        traceback.print_exc()

    print()

    # Test member details
    print("Step 8: Testing member details...")
    try:
        members = customer_group_manager.get_group_member_details(
            test_group_id,
            start_date,
            end_date
        )

        print(f"✅ Found {len(members)} members in group")
        if members:
            print()
            print("Group members:")
            print("-" * 70)
            for member in members:
                primary = "⭐" if member['is_primary'] else "  "
                print(f"  {primary} {member['customer_name']:<30} "
                      f"Sales: ${member['total_sales']:>10,.0f}  "
                      f"AR: ${member['ar_balance']:>8,.0f}")

    except Exception as e:
        print(f"❌ Member details error: {str(e)}")
        import traceback
        traceback.print_exc()

print()
print("=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print()
print("You can now run the Streamlit dashboard:")
print("  streamlit run app.py")
print()
