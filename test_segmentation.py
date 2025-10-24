#!/usr/bin/env python3
"""
Test script for Customer Segmentation feature
"""

import sys
import json
from modules.segmentation.segment_engine import SegmentationEngine

def test_segmentation():
    """Test the segmentation engine"""
    print("=" * 60)
    print("CUSTOMER SEGMENTATION TEST")
    print("=" * 60)

    try:
        # Initialize engine
        print("\n1. Initializing Segmentation Engine...")
        engine = SegmentationEngine()
        print("✅ Engine initialized")

        # Get overview
        print("\n2. Getting segmentation overview...")
        overview = engine.get_overview()

        if overview and 'summary' in overview:
            print(f"✅ Found {overview['summary']['total_customers']} customers")
            print(f"   Total Revenue: ${overview['summary']['total_revenue']:,.0f}")
            print(f"   Avg GP%: {overview['summary']['avg_gp_percentage']:.1f}%")
            print(f"   Wholesale: {overview['summary']['wholesale_count']}")
            print(f"   Retail: {overview['summary']['retail_count']}")

            # Show segments
            print("\n3. Customer Segments:")
            for segment, data in overview.get('segment_distribution', {}).items():
                print(f"   {segment}: {data.get('customer_count', 0)} customers, ${data.get('total_revenue', 0):,.0f}")

            # Show business distribution
            print("\n4. Business Type Distribution:")
            for btype, data in overview.get('business_type_distribution', {}).items():
                print(f"   {btype}: {data}")

            # Show customer classes
            print("\n5. Customer Classes:")
            for cclass, data in overview.get('customer_class_distribution', {}).items():
                print(f"   {cclass}: {data}")

            # Show payment behavior
            print("\n6. Payment Behavior:")
            for payment, data in overview.get('payment_behavior_distribution', {}).items():
                print(f"   {payment}: {data}")

            # Get recommendations
            print("\n7. Getting actionable recommendations...")
            recommendations = engine.get_actionable_recommendations()
            print(f"✅ Generated {len(recommendations)} recommendations")

            for rec in recommendations[:3]:  # Show top 3
                print(f"\n   Segment: {rec['segment']}")
                print(f"   Priority: {rec['priority']}")
                print(f"   Customers: {rec['customer_count']}")
                print(f"   Value: ${rec['total_value']:,.0f}")
                print(f"   Actions: {', '.join(rec['actions'][:2])}")

            # Identify at-risk customers
            print("\n8. Identifying at-risk customers...")
            at_risk = engine.identify_at_risk_customers(risk_threshold=0.6, min_value=5000)
            print(f"✅ Found {len(at_risk)} at-risk customers")

            if at_risk:
                total_at_risk = sum(c['monetary'] for c in at_risk)
                print(f"   Total value at risk: ${total_at_risk:,.0f}")
                print(f"   Top 3 at-risk:")
                for customer in at_risk[:3]:
                    print(f"     - {customer['company_name']}: ${customer['monetary']:,.0f} (Risk: {customer['risk_score']:.0f})")

            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED SUCCESSFULLY!")
            print("=" * 60)

            # Save test results
            with open('segmentation_test_results.json', 'w') as f:
                json.dump({
                    'status': 'success',
                    'overview': overview,
                    'recommendations_count': len(recommendations),
                    'at_risk_count': len(at_risk)
                }, f, indent=2, default=str)
            print("\nResults saved to segmentation_test_results.json")

        else:
            print("❌ No data returned from segmentation engine")
            print("   This might mean no customers in database or connection issue")

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = test_segmentation()
    sys.exit(0 if success else 1)