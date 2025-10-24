"""
Examine the PUVIEWEXCISECOLLECT view definition to understand exact excise calculation logic
"""

from database_pymssql import SQLServerConnection

def main():
    print("\n" + "="*80)
    print("EXAMINING EXCISE VIEW DEFINITION")
    print("="*80)

    with SQLServerConnection() as db:
        # Get the view definition
        print("\n1. Getting PUVIEWEXCISECOLLECT view definition...")
        query = """
        SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.PUVIEWEXCISECOLLECT')) AS ViewDefinition
        """
        result = db.execute_query(query, description="Get view definition")

        if not result.empty and result.iloc[0]['ViewDefinition']:
            view_def = result.iloc[0]['ViewDefinition']
            print("\nVIEW DEFINITION:")
            print("="*80)
            print(view_def)
            print("="*80)

            # Save to file for easier analysis
            with open('PUVIEWEXCISECOLLECT_definition.sql', 'w') as f:
                f.write(view_def)
            print("\n✅ View definition saved to: PUVIEWEXCISECOLLECT_definition.sql")

        # Also get sample data to understand what it returns
        print("\n2. Getting sample data from PUVIEWEXCISECOLLECT...")
        query2 = """
        SELECT TOP 10 *
        FROM dbo.PUVIEWEXCISECOLLECT
        WHERE TOTALEXCISECOLLECT > 0
        ORDER BY DATE DESC
        """
        sample = db.execute_query(query2, description="PUVIEWEXCISECOLLECT sample")
        print("\nSAMPLE DATA:")
        print(sample.to_string(index=False))

        # Get excise totals for a specific date range
        print("\n3. Getting excise totals for recent period...")
        query3 = """
        SELECT
            COUNT(*) as transaction_count,
            SUM(LOOSETOBACCO) as total_loose_tobacco,
            SUM(SMOKELESS) as total_smokeless,
            SUM(LARGECIGARS) as total_large_cigars,
            SUM(LITTLECIGARS) as total_little_cigars,
            SUM(VAPORSOPEN) as total_vapors_open,
            SUM(VAPORSDEVICE) as total_vapors_device,
            SUM(VAPORSCLOSED) as total_vapors_closed,
            SUM(TOTALEXCISECOLLECT) as total_excise,
            SUM(TOTALSALES) as total_sales
        FROM dbo.PUVIEWEXCISECOLLECT
        WHERE DATE >= '2024-01-01'
        """
        totals = db.execute_query(query3, description="Excise totals")
        print("\nEXCISE TOTALS (2024+):")
        print(totals.to_string(index=False))

if __name__ == "__main__":
    main()
