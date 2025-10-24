#!/usr/bin/env python3
"""Test PD check parser with recent formats"""

from modules.pd_check_parser import PDCheckParser

# Test data from your recent payments
test_comments = [
    "PD-8/16/25 SURAFAL",
    "RAHIM BHAI   PD-8/12/25",
    "DELIVERY PD-10/20/25",
    "DELIVERY PD-10/8/25",
    "DELIVERY  PD-9/20/25",
    "DELIVERY PD-9/10/25",
    "SHAHID BHAI PD-8/30/25",
    "PD;- 08/27/2025 IRFAN",
    "PD;- 08/21/2025 IRFAN",
    "pd:- 08/13/2025 from del",
    "AKBER BHAI  PD-8/8/25",
    "ASIF BHAI   PD-9/6/25",
    "FROM DEL PD:- 08/27/2025",
    "PD:- 08/20/2025 FROM DEL",
    "8/17/25",
    "8/12/25",
    "CURRENT",  # Should not be parsed as PD
    "RASOOL",    # Should not be parsed as PD
]

print("Testing PD Check Parser with Recent Formats")
print("=" * 60)

for comment in test_comments:
    info = PDCheckParser.extract_pd_info(comment)
    if info['is_pd_check'] or "/" in comment:
        print(f"\nComment: {comment}")
        print(f"  Is PD Check: {info['is_pd_check']}")
        if info['deposit_date']:
            print(f"  Deposit Date: {info['deposit_date']}")
            print(f"  Days Until: {info.get('days_until_deposit')}")
            if info.get('is_past_due'):
                print(f"  Status: PAST DUE")
            elif info.get('is_due_soon'):
                print(f"  Status: Due Soon")
        else:
            print(f"  Deposit Date: Could not parse")