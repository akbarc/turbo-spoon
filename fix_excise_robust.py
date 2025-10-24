#!/usr/bin/env python3
"""
Robustly fix all excise queries by finding and replacing line by line
"""

def fix_excise_queries_robust():
    file_path = 'app/main.py'

    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Find the line numbers for each elif report_type block
    in_pu_excise_summary = False
    in_excise_by_category = False
    in_excise_transactions = False
    in_daily_excise = False

    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if we're entering a PUExciseEntry query block
        if "elif report_type == 'pu_excise_summary':" in line:
            # Replace entire pu_excise_summary block
            new_lines.append("        elif report_type == 'pu_excise_summary':\n")
            new_lines.append("            # Georgia excise tax summary using actual tax rates by category\n")
            new_lines.append("            query = f\"\"\"\n")
            new_lines.append("            SELECT\n")
            new_lines.append("                CAST(t.Time AS DATE) as ExciseDate,\n")
            new_lines.append("                COUNT(DISTINCT t.TransactionNumber) as TransactionCount,\n")
            new_lines.append("                SUM(\n")
            new_lines.append("                    CASE\n")
            new_lines.append("                        WHEN cat.Name LIKE '%CIGARETTE%' THEN te.Quantity * 0.37\n")
            new_lines.append("                        WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN te.Quantity * 0.23\n")
            new_lines.append("                        WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN te.Quantity * 0.15\n")
            new_lines.append("                        WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * te.Quantity * 0.08\n")
            new_lines.append("                        ELSE 0\n")
            new_lines.append("                    END\n")
            new_lines.append("                ) as TotalExciseTax,\n")
            new_lines.append("                SUM(te.Quantity) as TotalQuantity,\n")
            new_lines.append("                AVG(\n")
            new_lines.append("                    CASE\n")
            new_lines.append("                        WHEN cat.Name LIKE '%CIGARETTE%' THEN 0.37\n")
            new_lines.append("                        WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN 0.23\n")
            new_lines.append("                        WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN 0.15\n")
            new_lines.append("                        WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * 0.08\n")
            new_lines.append("                        ELSE 0\n")
            new_lines.append("                    END\n")
            new_lines.append("                ) as AvgExciseRate\n")
            new_lines.append("            FROM [dbo].[Transaction] t\n")
            new_lines.append("            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber\n")
            new_lines.append("            JOIN dbo.Item i ON te.ItemID = i.ID\n")
            new_lines.append("            LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID\n")
            new_lines.append("            WHERE 1=1 {date_filter}\n")
            new_lines.append("            AND te.Quantity > 0\n")
            new_lines.append("            GROUP BY CAST(t.Time AS DATE)\n")
            new_lines.append("            ORDER BY ExciseDate DESC\n")
            new_lines.append("            \"\"\"\n")

            # Skip the old query lines
            i += 1
            while i < len(lines) and 'elif report_type ==' not in lines[i]:
                i += 1
            continue

        elif "elif report_type == 'excise_by_category':" in line:
            # Replace entire excise_by_category block
            new_lines.append("\n")
            new_lines.append("        elif report_type == 'excise_by_category':\n")
            new_lines.append("            # Georgia excise tax by category using actual tax rates\n")
            new_lines.append("            query = f\"\"\"\n")
            new_lines.append("            SELECT\n")
            new_lines.append("                cat.Name as Category,\n")
            new_lines.append("                COUNT(DISTINCT t.TransactionNumber) as TransactionCount,\n")
            new_lines.append("                SUM(\n")
            new_lines.append("                    CASE\n")
            new_lines.append("                        WHEN cat.Name LIKE '%CIGARETTE%' THEN te.Quantity * 0.37\n")
            new_lines.append("                        WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN te.Quantity * 0.23\n")
            new_lines.append("                        WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN te.Quantity * 0.15\n")
            new_lines.append("                        WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * te.Quantity * 0.08\n")
            new_lines.append("                        ELSE 0\n")
            new_lines.append("                    END\n")
            new_lines.append("                ) as TotalExciseTax,\n")
            new_lines.append("                SUM(te.Quantity) as TotalQuantity,\n")
            new_lines.append("                AVG(\n")
            new_lines.append("                    CASE\n")
            new_lines.append("                        WHEN cat.Name LIKE '%CIGARETTE%' THEN 0.37\n")
            new_lines.append("                        WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN 0.23\n")
            new_lines.append("                        WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN 0.15\n")
            new_lines.append("                        WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * 0.08\n")
            new_lines.append("                        ELSE 0\n")
            new_lines.append("                    END\n")
            new_lines.append("                ) as AvgExciseRate,\n")
            new_lines.append("                COUNT(DISTINCT te.ItemID) as UniqueItems\n")
            new_lines.append("            FROM [dbo].[Transaction] t\n")
            new_lines.append("            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber\n")
            new_lines.append("            JOIN dbo.Item i ON te.ItemID = i.ID\n")
            new_lines.append("            LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID\n")
            new_lines.append("            WHERE 1=1 {date_filter}\n")
            new_lines.append("            AND te.Quantity > 0\n")
            new_lines.append("            GROUP BY cat.Name\n")
            new_lines.append("            HAVING SUM(\n")
            new_lines.append("                    CASE\n")
            new_lines.append("                        WHEN cat.Name LIKE '%CIGARETTE%' THEN te.Quantity * 0.37\n")
            new_lines.append("                        WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN te.Quantity * 0.23\n")
            new_lines.append("                        WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN te.Quantity * 0.15\n")
            new_lines.append("                        WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * te.Quantity * 0.08\n")
            new_lines.append("                        ELSE 0\n")
            new_lines.append("                    END\n")
            new_lines.append("                ) > 0\n")
            new_lines.append("            ORDER BY TotalExciseTax DESC\n")
            new_lines.append("            \"\"\"\n")

            # Skip the old query lines
            i += 1
            while i < len(lines) and 'elif report_type ==' not in lines[i]:
                i += 1
            continue

        elif "elif report_type == 'excise_transactions':" in line:
            # Replace entire excise_transactions block
            new_lines.append("\n")
            new_lines.append("        elif report_type == 'excise_transactions':\n")
            new_lines.append("            # Georgia excise tax transactions using actual tax rates\n")
            new_lines.append("            query = f\"\"\"\n")
            new_lines.append("            SELECT TOP 100\n")
            new_lines.append("                t.TransactionNumber,\n")
            new_lines.append("                t.Time as TransactionTime,\n")
            new_lines.append("                i.Description as ItemName,\n")
            new_lines.append("                cat.Name as Category,\n")
            new_lines.append("                te.Quantity,\n")
            new_lines.append("                CASE\n")
            new_lines.append("                    WHEN cat.Name LIKE '%CIGARETTE%' THEN 0.37\n")
            new_lines.append("                    WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN 0.23\n")
            new_lines.append("                    WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN 0.15\n")
            new_lines.append("                    WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * 0.08\n")
            new_lines.append("                    ELSE 0\n")
            new_lines.append("                END as ExciseRate,\n")
            new_lines.append("                CASE\n")
            new_lines.append("                    WHEN cat.Name LIKE '%CIGARETTE%' THEN te.Quantity * 0.37\n")
            new_lines.append("                    WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN te.Quantity * 0.23\n")
            new_lines.append("                    WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN te.Quantity * 0.15\n")
            new_lines.append("                    WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * te.Quantity * 0.08\n")
            new_lines.append("                    ELSE 0\n")
            new_lines.append("                END as ExciseTax,\n")
            new_lines.append("                te.Price * te.Quantity as FullPrice,\n")
            new_lines.append("                te.Price as SalePrice\n")
            new_lines.append("            FROM [dbo].[Transaction] t\n")
            new_lines.append("            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber\n")
            new_lines.append("            JOIN dbo.Item i ON te.ItemID = i.ID\n")
            new_lines.append("            LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID\n")
            new_lines.append("            WHERE 1=1 {date_filter}\n")
            new_lines.append("            AND te.Quantity > 0\n")
            new_lines.append("            AND (\n")
            new_lines.append("                cat.Name LIKE '%CIGARETTE%' OR\n")
            new_lines.append("                cat.Name LIKE '%CIGAR%' OR\n")
            new_lines.append("                cat.Name LIKE '%LT-TAX%' OR\n")
            new_lines.append("                cat.Name LIKE '%SMOKELESS%'\n")
            new_lines.append("            )\n")
            new_lines.append("            ORDER BY t.Time DESC\n")
            new_lines.append("            \"\"\"\n")

            # Skip the old query lines
            i += 1
            while i < len(lines) and 'elif report_type ==' not in lines[i]:
                i += 1
            continue

        elif "elif report_type == 'daily_excise':" in line:
            # Replace entire daily_excise block
            new_lines.append("\n")
            new_lines.append("        elif report_type == 'daily_excise':\n")
            new_lines.append("            # Daily Georgia excise tax using actual tax rates\n")
            new_lines.append("            query = f\"\"\"\n")
            new_lines.append("            SELECT\n")
            new_lines.append("                CAST(t.Time AS DATE) as ExciseDate,\n")
            new_lines.append("                SUM(\n")
            new_lines.append("                    CASE\n")
            new_lines.append("                        WHEN cat.Name LIKE '%CIGARETTE%' THEN te.Quantity * 0.37\n")
            new_lines.append("                        WHEN cat.Name LIKE '%CIGAR%' AND cat.Name NOT LIKE '%LIT%' AND cat.Name NOT LIKE '%LITTLE%' THEN te.Quantity * 0.23\n")
            new_lines.append("                        WHEN cat.Name LIKE '%LT-TAX%' OR cat.Name LIKE '%LIT%CIGAR%' OR cat.Name LIKE '%LITTLE%CIGAR%' THEN te.Quantity * 0.15\n")
            new_lines.append("                        WHEN cat.Name LIKE '%SMOKELESS%' THEN te.Cost * te.Quantity * 0.08\n")
            new_lines.append("                        ELSE 0\n")
            new_lines.append("                    END\n")
            new_lines.append("                ) as TotalExciseTax,\n")
            new_lines.append("                COUNT(DISTINCT t.TransactionNumber) as TransactionCount,\n")
            new_lines.append("                COUNT(DISTINCT te.ItemID) as UniqueItems,\n")
            new_lines.append("                SUM(te.Quantity) as TotalQuantity\n")
            new_lines.append("            FROM [dbo].[Transaction] t\n")
            new_lines.append("            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber\n")
            new_lines.append("            JOIN dbo.Item i ON te.ItemID = i.ID\n")
            new_lines.append("            LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID\n")
            new_lines.append("            WHERE 1=1 {date_filter}\n")
            new_lines.append("            AND te.Quantity > 0\n")
            new_lines.append("            AND (\n")
            new_lines.append("                cat.Name LIKE '%CIGARETTE%' OR\n")
            new_lines.append("                cat.Name LIKE '%CIGAR%' OR\n")
            new_lines.append("                cat.Name LIKE '%LT-TAX%' OR\n")
            new_lines.append("                cat.Name LIKE '%SMOKELESS%'\n")
            new_lines.append("            )\n")
            new_lines.append("            GROUP BY CAST(t.Time AS DATE)\n")
            new_lines.append("            ORDER BY ExciseDate DESC\n")
            new_lines.append("            \"\"\"\n")

            # Skip the old query lines
            i += 1
            while i < len(lines) and 'elif report_type ==' not in lines[i]:
                i += 1
            continue

        else:
            new_lines.append(line)
            i += 1

    # Write the fixed content
    with open(file_path, 'w') as f:
        f.writelines(new_lines)

    print("✅ Robustly fixed all excise tax queries")

if __name__ == '__main__':
    fix_excise_queries_robust()
