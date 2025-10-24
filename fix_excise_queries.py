#!/usr/bin/env python3
"""
Fix excise tax queries in app/main.py
Replace PUExciseEntry references with proper Georgia excise tax logic
"""

import re

def fix_excise_queries():
    file_path = 'app/main.py'

    with open(file_path, 'r') as f:
        content = f.read()

    # Define the new excise queries using Georgia tax rates

    # 1. Fix pu_excise_summary
    old_pu_excise = r"""elif report_type == 'pu_excise_summary':
            query = f\"\"\"
            SELECT
                CAST\(pue\.TransactionTime AS DATE\) as ExciseDate,
                COUNT\(DISTINCT pue\.TransactionNumber\) as TransactionCount,
                SUM\(pue\.PriceC \* pue\.Quantity\) as TotalExciseTax,
                SUM\(pue\.Quantity\) as TotalQuantity,
                AVG\(pue\.PriceC\) as AvgExciseRate
            FROM dbo\.PUExciseEntry pue
            WHERE 1=1 \{date_filter\.replace\('t\.Time', 'pue\.TransactionTime'\)\}
            GROUP BY CAST\(pue\.TransactionTime AS DATE\)
            ORDER BY ExciseDate DESC
            \"\"\"
"""

    new_pu_excise = """elif report_type == 'pu_excise_summary':
            # Georgia excise tax summary using actual tax rates by category
            query = f\"\"\"
            SELECT
                CAST(t.Time AS DATE) as ExciseDate,
                COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
                SUM(
                    CASE
                        WHEN cat.Name LIKE '%CIGARETTE%' THEN te.Quantity * 0.37
                        WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN te.Quantity * 0.23
                        WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN te.Quantity * 0.15
                        WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * te.Quantity * 0.08
                        ELSE 0
                    END
                ) as TotalExciseTax,
                SUM(te.Quantity) as TotalQuantity,
                AVG(
                    CASE
                        WHEN cat.Name LIKE '%CIGARETTE%' THEN 0.37
                        WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN 0.23
                        WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN 0.15
                        WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * 0.08
                        ELSE 0
                    END
                ) as AvgExciseRate
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            JOIN dbo.Item i ON te.ItemID = i.ID
            LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
            WHERE 1=1 {date_filter}
            AND te.Quantity > 0
            GROUP BY CAST(t.Time AS DATE)
            ORDER BY ExciseDate DESC
            \"\"\"
"""

    content = re.sub(old_pu_excise, new_pu_excise, content, flags=re.DOTALL)

    # 2. Fix excise_by_category
    old_excise_cat = r"""elif report_type == 'excise_by_category':
            query = f\"\"\"
            SELECT
                cat\.Name as Category,
                COUNT\(DISTINCT pue\.TransactionNumber\) as TransactionCount,
                SUM\(pue\.PriceC \* pue\.Quantity\) as TotalExciseTax,
                SUM\(pue\.Quantity\) as TotalQuantity,
                AVG\(pue\.PriceC\) as AvgExciseRate,
                COUNT\(DISTINCT pue\.ItemID\) as UniqueItems
            FROM dbo\.PUExciseEntry pue
            JOIN dbo\.Item i ON pue\.ItemID = i\.ID
            LEFT JOIN dbo\.Category cat ON i\.CategoryID = cat\.ID
            WHERE 1=1 \{date_filter\.replace\('t\.Time', 'pue\.TransactionTime'\)\}
            GROUP BY cat\.Name
            ORDER BY TotalExciseTax DESC
            \"\"\"
"""

    new_excise_cat = """elif report_type == 'excise_by_category':
            # Georgia excise tax by category using actual tax rates
            query = f\"\"\"
            SELECT
                cat.Name as Category,
                COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
                SUM(
                    CASE
                        WHEN cat.Name LIKE '%CIGARETTE%' THEN te.Quantity * 0.37
                        WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN te.Quantity * 0.23
                        WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN te.Quantity * 0.15
                        WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * te.Quantity * 0.08
                        ELSE 0
                    END
                ) as TotalExciseTax,
                SUM(te.Quantity) as TotalQuantity,
                AVG(
                    CASE
                        WHEN cat.Name LIKE '%CIGARETTE%' THEN 0.37
                        WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN 0.23
                        WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN 0.15
                        WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * 0.08
                        ELSE 0
                    END
                ) as AvgExciseRate,
                COUNT(DISTINCT te.ItemID) as UniqueItems
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            JOIN dbo.Item i ON te.ItemID = i.ID
            LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
            WHERE 1=1 {date_filter}
            AND te.Quantity > 0
            GROUP BY cat.Name
            HAVING SUM(
                    CASE
                        WHEN cat.Name LIKE '%CIGARETTE%' THEN te.Quantity * 0.37
                        WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN te.Quantity * 0.23
                        WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN te.Quantity * 0.15
                        WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * te.Quantity * 0.08
                        ELSE 0
                    END
                ) > 0
            ORDER BY TotalExciseTax DESC
            \"\"\"
"""

    content = re.sub(old_excise_cat, new_excise_cat, content, flags=re.DOTALL)

    # 3. Fix excise_transactions
    old_excise_trans = r"""elif report_type == 'excise_transactions':
            query = f\"\"\"
            SELECT TOP 100
                pue\.TransactionNumber,
                pue\.TransactionTime,
                i\.Description as ItemName,
                cat\.Name as Category,
                pue\.Quantity,
                pue\.PriceC as ExciseRate,
                \(pue\.PriceC \* pue\.Quantity\) as ExciseTax,
                pue\.FullPrice,
                pue\.Price as SalePrice
            FROM dbo\.PUExciseEntry pue
            JOIN dbo\.Item i ON pue\.ItemID = i\.ID
            LEFT JOIN dbo\.Category cat ON i\.CategoryID = cat\.ID
            WHERE 1=1 \{date_filter\.replace\('t\.Time', 'pue\.TransactionTime'\)\}
            ORDER BY pue\.TransactionTime DESC
            \"\"\"
"""

    new_excise_trans = """elif report_type == 'excise_transactions':
            # Georgia excise tax transactions using actual tax rates
            query = f\"\"\"
            SELECT TOP 100
                t.TransactionNumber,
                t.Time as TransactionTime,
                i.Description as ItemName,
                cat.Name as Category,
                te.Quantity,
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
                END as ExciseTax,
                te.Price * te.Quantity as FullPrice,
                te.Price as SalePrice
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            JOIN dbo.Item i ON te.ItemID = i.ID
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
            \"\"\"
"""

    content = re.sub(old_excise_trans, new_excise_trans, content, flags=re.DOTALL)

    # 4. Fix daily_excise
    old_daily_excise = r"""elif report_type == 'daily_excise':
            query = f\"\"\"
            SELECT
                CAST\(pue\.TransactionTime AS DATE\) as ExciseDate,
                SUM\(pue\.PriceC \* pue\.Quantity\) as TotalExciseTax,
                COUNT\(DISTINCT pue\.TransactionNumber\) as TransactionCount,
                COUNT\(DISTINCT pue\.ItemID\) as UniqueItems,
                SUM\(pue\.Quantity\) as TotalQuantity
            FROM dbo\.PUExciseEntry pue
            WHERE 1=1 \{date_filter\.replace\('t\.Time', 'pue\.TransactionTime'\)\}
            GROUP BY CAST\(pue\.TransactionTime AS DATE\)
            ORDER BY ExciseDate DESC
            \"\"\"
"""

    new_daily_excise = """elif report_type == 'daily_excise':
            # Daily Georgia excise tax using actual tax rates
            query = f\"\"\"
            SELECT
                CAST(t.Time AS DATE) as ExciseDate,
                SUM(
                    CASE
                        WHEN cat.Name LIKE '%CIGARETTE%' THEN te.Quantity * 0.37
                        WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN te.Quantity * 0.23
                        WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN te.Quantity * 0.15
                        WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * te.Quantity * 0.08
                        ELSE 0
                    END
                ) as TotalExciseTax,
                COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
                COUNT(DISTINCT te.ItemID) as UniqueItems,
                SUM(te.Quantity) as TotalQuantity
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            JOIN dbo.Item i ON te.ItemID = i.ID
            LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
            WHERE 1=1 {date_filter}
            AND te.Quantity > 0
            AND (
                cat.Name LIKE '%CIGARETTE%' OR
                cat.Name LIKE '%CIGAR%' OR
                cat.Name LIKE '%LT-TAX%' OR
                cat.Name LIKE '%SMOKELESS%'
            )
            GROUP BY CAST(t.Time AS DATE)
            ORDER BY ExciseDate DESC
            \"\"\"
"""

    content = re.sub(old_daily_excise, new_daily_excise, content, flags=re.DOTALL)

    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(content)

    print("✅ Fixed all excise tax queries in app/main.py")
    print("   - pu_excise_summary: Now uses Georgia tax rates by category")
    print("   - excise_by_category: Now uses Georgia tax rates by category")
    print("   - excise_transactions: Now uses Georgia tax rates by category")
    print("   - daily_excise: Now uses Georgia tax rates by category")
    print("\n📋 Georgia Tax Rates Applied:")
    print("   - Cigarettes: $0.37/pack")
    print("   - Cigars: $0.23/unit")
    print("   - Little Cigars/LT-TAX: $0.15/unit")
    print("   - Smokeless Tobacco: 8% of cost")

if __name__ == '__main__':
    fix_excise_queries()
