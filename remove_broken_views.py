#!/usr/bin/env python3
"""Remove broken excise views from view_reports list"""

with open('/Users/akbarchranya/georgiadashboard/app/main.py', 'r') as f:
    content = f.read()

# Remove the broken excise views section
old_section = """
            # Excise Tax Views (Professional Tax Compliance)
            {'id': 'pu_excise_collect', 'name': 'PU Excise Tax Collected', 'type': 'Excise View', 'category': 'Tax Reports', 'view': 'PUVIEWEXCISECOLLECT', 'description': 'Excise tax collection report (247 fields)'},
            {'id': 'pu_excise_paid', 'name': 'PU Excise Tax Paid', 'type': 'Excise View', 'category': 'Tax Reports', 'view': 'PUVIEWEXCISEPAID', 'description': 'Excise tax payment report (247 fields)'},
            {'id': 'pu_excise_transaction', 'name': 'PU Excise Transactions', 'type': 'Excise View', 'category': 'Tax Reports', 'view': 'PUVIEWEXCISETRANSACTION', 'description': 'Complete excise transactions (5,148 fields!)'},
            {'id': 'excise_tax_collect', 'name': 'Excise Tax Collection', 'type': 'Tax View', 'category': 'Tax Reports', 'view': 'VIEWEXCISETAXCOLLECT', 'description': 'Tax collection tracking (361 fields)'},
            {'id': 'excise_tax_paid', 'name': 'Excise Tax Paid', 'type': 'Tax View', 'category': 'Tax Reports', 'view': 'VIEWEXCISETAXPAID', 'description': 'Tax payment tracking (361 fields)'},
            {'id': 'hold_excise_tax', 'name': 'Held Excise Tax', 'type': 'Tax View', 'category': 'Tax Reports', 'view': 'VIEWHOLDEXCISETAX', 'description': 'Held excise tax report (1,599 fields)'},
            {'id': 'po_excise_tax', 'name': 'Purchase Order Excise Tax', 'type': 'Tax View', 'category': 'Tax Reports', 'view': 'VIEWPOEXCISETAX', 'description': 'PO excise tax tracking (2,397 fields)'},

            # Inventory Movement Reports
            {'id': 'item_movement', 'name': 'Item Movement Report', 'type': 'Movement View', 'category': 'Inventory Reports', 'view': 'VIEWITEMMOVEMENT', 'description': 'Real-time inventory movement (448 fields)'},
            {'id': 'item_movement_history', 'name': 'Item Movement History', 'type': 'Movement View', 'category': 'Inventory Reports', 'view': 'VIEWITEMMOVEMENTHISTORY', 'description': 'Historical inventory movement (608 fields)'},

            # Payment/Tender Reports
            {'id': 'tenders_analysis', 'name': 'Tender Analysis Report', 'type': 'Tender View', 'category': 'Financial Reports', 'view': 'VIEWTENDERS', 'description': 'Payment tender analysis (507 fields)'},"""

new_section = """
            # NOTE: Broken excise/movement/tender views REMOVED (caused severe timeouts)
            # - PUVIEWEXCISECOLLECT, PUVIEWEXCISEPAID, PUVIEWEXCISETRANSACTION
            # - VIEWEXCISETAXCOLLECT, VIEWEXCISETAXPAID, VIEWHOLDEXCISETAX, VIEWPOEXCISETAX
            # - VIEWITEMMOVEMENT, VIEWITEMMOVEMENTHISTORY, VIEWTENDERS
            # All excise functionality now uses fast PUExciseEntry table queries (see excise_reports below)"""

content = content.replace(old_section, new_section)

# Also remove the excise views query
old_query = """        # Get available excise tax views
        excise_views_query = \"\"\"
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.VIEWS
        WHERE TABLE_NAME LIKE '%EXCISE%' OR TABLE_NAME LIKE '%PU%'
        ORDER BY TABLE_NAME
        \"\"\"
        excise_views = db.execute_query(excise_views_query)"""

new_query = """        # Excise views removed - using optimized PUExciseEntry table queries instead"""

content = content.replace(old_query, new_query)

# Write back
with open('/Users/akbarchranya/georgiadashboard/app/main.py', 'w') as f:
    f.write(content)

print("✅ Removed broken excise/movement/tender views from view_reports")
print("✅ Removed excise views query")
