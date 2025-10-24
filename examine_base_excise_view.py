"""
Examine the base PUVIEWEXCISETRANSACTION view that PUVIEWEXCISECOLLECT depends on
"""

from database_pymssql import SQLServerConnection

def main():
    print("\n" + "="*80)
    print("EXAMINING BASE EXCISE TRANSACTION VIEW")
    print("="*80)

    with SQLServerConnection() as db:
        # Get PUVIEWEXCISETRANSACTION definition
        print("\n1. Getting PUVIEWEXCISETRANSACTION view definition...")
        query = """
        SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.PUVIEWEXCISETRANSACTION')) AS ViewDefinition
        """
        result = db.execute_query(query, description="Get PUVIEWEXCISETRANSACTION definition")

        if not result.empty and result.iloc[0]['ViewDefinition']:
            view_def = result.iloc[0]['ViewDefinition']
            print("\nVIEW DEFINITION:")
            print("="*80)
            print(view_def)
            print("="*80)

            # Save to file
            with open('PUVIEWEXCISETRANSACTION_definition.sql', 'w') as f:
                f.write(view_def)
            print("\n✅ View definition saved to: PUVIEWEXCISETRANSACTION_definition.sql")

        # Get structure of the view
        print("\n2. Getting PUVIEWEXCISETRANSACTION structure...")
        query2 = """
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'PUVIEWEXCISETRANSACTION'
        ORDER BY ORDINAL_POSITION
        """
        structure = db.execute_query(query2, description="PUVIEWEXCISETRANSACTION structure")
        print("\nVIEWEXCISETRANSACTION COLUMNS:")
        print(structure.to_string(index=False))

if __name__ == "__main__":
    main()
