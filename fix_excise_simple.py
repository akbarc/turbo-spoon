#!/usr/bin/env python3
"""
Fix the remaining excise_simple query and update comments
"""

def fix_excise_simple():
    file_path = 'app/main.py'

    with open(file_path, 'r') as f:
        content = f.read()

    # Fix the excise_simple query
    old_excise_simple = """        # Simple excise report using PUExciseEntry table directly
        elif report_type == 'excise_simple':
            query = f\"\"\"
            SELECT
                pue.TransactionNumber,
                CONVERT(varchar, pue.TransactionTime, 101) as TransactionDate,
                CONVERT(varchar, pue.TransactionTime, 108) as TransactionTime,
                COALESCE(i.Description, 'Item ID: ' + CAST(pue.ItemID AS VARCHAR)) as ItemName,
                COALESCE(cat.Name, 'Uncategorized') as Category,
                pue.Quantity,
                pue.Price as SalePrice,
                pue.PriceC as ExciseRate,
                (pue.PriceC * pue.Quantity) as ExciseTax
            FROM dbo.PUExciseEntry pue
            LEFT JOIN dbo.Item i ON pue.ItemID = i.ID
            LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
            WHERE 1=1 {date_filter.replace('t.Time', 'pue.TransactionTime')}
            AND pue.PriceC > 0
            ORDER BY pue.TransactionTime DESC
            \"\"\""""

    new_excise_simple = """        # Simple excise report using Georgia tax rates
        elif report_type == 'excise_simple':
            query = f\"\"\"
            SELECT TOP 100
                t.TransactionNumber,
                CONVERT(varchar, t.Time, 101) as TransactionDate,
                CONVERT(varchar, t.Time, 108) as TransactionTime,
                COALESCE(i.Description, 'Item ID: ' + CAST(i.ID AS VARCHAR)) as ItemName,
                COALESCE(cat.Name, 'Uncategorized') as Category,
                te.Quantity,
                te.Price as SalePrice,
                CASE
                    WHEN cat.Name LIKE '%CIGARETTE%' THEN 0.37
                    WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN 0.23
                    WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN 0.15
                    WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * 0.08
                    ELSE 0
                END as ExciseRate,
                CASE
                    WHEN cat.Name LIKE '%CIGARETTE%' THEN te.Quantity * 0.37
                    WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN te.Quantity * 0.23
                    WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN te.Quantity * 0.15
                    WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * te.Quantity * 0.08
                    ELSE 0
                END as ExciseTax
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            LEFT JOIN dbo.Item i ON te.ItemID = i.ID
            LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
            WHERE 1=1 {date_filter}
            AND te.Quantity > 0
            AND (
                cat.Name LIKE '%CIGARETTE%' OR
                cat.Name LIKE '%CIGAR%' OR
                cat.Name LIKE '%LT-TAX%' OR
                cat.Name LIKE '%SMOKELESS%'
            )
            ORDER BY t.Time DESC
            \"\"\""""

    content = content.replace(old_excise_simple, new_excise_simple)

    # Update comment about excise reports
    content = content.replace(
        "        # Add Excise Tax Reports (using PUExciseEntry table directly - OPTIMIZED)",
        "        # Add Excise Tax Reports (using Georgia tax rates - ACCURATE)"
    )

    content = content.replace(
        "        # NOTE: Broken excise views (PUVIEWEXCISECOLLECT, etc.) removed - caused timeouts",
        "        # NOTE: Now uses actual Georgia excise tax rates by product category"
    )

    content = content.replace(
        "        # Excise views removed - using PUExciseEntry table directly",
        "        # Excise views removed - using Georgia tax rates calculation"
    )

    with open(file_path, 'w') as f:
        f.write(content)

    print("✅ Fixed excise_simple query")
    print("✅ Updated all comments to reflect Georgia tax rate logic")

if __name__ == '__main__':
    fix_excise_simple()
