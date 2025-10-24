#!/usr/bin/env python3
"""
Test Tailscale database connection
"""

import pymssql
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set TDS version
os.environ['TDSVER'] = '7.0'

def test_direct_connection():
    """Test direct pymssql connection"""
    print("🔄 Testing direct pymssql connection...")
    
    try:
        conn = pymssql.connect(
            server='10.1.10.105',
            user='amchranya', 
            password='2000Akbar!',
            database='GAWDB',
            tds_version='7.0',
            timeout=30,
            login_timeout=10
        )
        
        print("✅ SUCCESS: Direct connection works!")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM [dbo].[Transaction] WHERE CAST(Time AS DATE) = CAST(GETDATE() AS DATE)")
        result = cursor.fetchone()
        print(f"✅ Query result: {result[0]} transactions today")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_class_connection():
    """Test our SQLServerConnection class"""
    print("\n🔄 Testing SQLServerConnection class...")
    
    try:
        from database_pymssql import SQLServerConnection
        
        db = SQLServerConnection()
        if db.connect():
            print("✅ SUCCESS: Class connection works!")
            
            # Test query
            result = db.execute_query("SELECT COUNT(*) as count FROM [dbo].[Transaction] WHERE CAST(Time AS DATE) = CAST(GETDATE() AS DATE)")
            count = result.iloc[0]['count'] if not result.empty else 0
            print(f"✅ Query result: {count} transactions today")
            
            db.close()
            return True
        else:
            print("❌ FAILED: Class connection failed")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

if __name__ == "__main__":
    print("🧪 TAILSCALE DATABASE CONNECTION TEST")
    print("=" * 50)
    
    # Test both methods
    direct_works = test_direct_connection()
    class_works = test_class_connection()
    
    print("\n📊 RESULTS:")
    print(f"Direct pymssql: {'✅ WORKING' if direct_works else '❌ FAILED'}")
    print(f"Class method:   {'✅ WORKING' if class_works else '❌ FAILED'}")
    
    if direct_works and not class_works:
        print("\n🔍 DIAGNOSIS: Direct connection works, class method fails")
        print("   → Issue is in SQLServerConnection class implementation")
    elif not direct_works and not class_works:
        print("\n🔍 DIAGNOSIS: Both methods fail")
        print("   → Issue is with Tailscale subnet routing or SQL Server")
    elif direct_works and class_works:
        print("\n🎉 SUCCESS: Both methods work - dashboard should work remotely!")
