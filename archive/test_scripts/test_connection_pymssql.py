#!/usr/bin/env python3
"""
Test script to verify SQL Server connection using pymssql (for legacy SQL Server 2008)
"""

import pymssql
import sys

def test_connection_with_ip():
    print("Testing SQL Server connection with pymssql using IP address...")
    try:
        from database_pymssql import DB_CONFIG
        conn = pymssql.connect(
            server=DB_CONFIG['server'],
            user=DB_CONFIG['username'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            timeout=DB_CONFIG['timeout'],
            login_timeout=DB_CONFIG['login_timeout']
        )
        cursor = conn.cursor()
        cursor.execute('SELECT @@VERSION')
        row = cursor.fetchone()
        print(f"✅ Connected with IP! SQL Server Version: {row[0]}")
        
        cursor.execute("SELECT name FROM sys.databases WHERE database_id > 4")
        print("Available databases:")
        for db_row in cursor.fetchall():
            print(f"  - {db_row[0]}")
        
        conn.close()
        print("\n🎉 Connection successful with IP address!")
        return True
    except Exception as e:
        print(f"❌ Connection with IP failed: {e}")
        return False

def test_connection_with_hostname():
    print("Testing SQL Server connection with pymssql using hostname...")
    try:
        from database_pymssql import DB_CONFIG
        conn = pymssql.connect(
            server='SOSERVER',  # Use hostname instead of IP
            user=DB_CONFIG['username'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            timeout=DB_CONFIG['timeout'],
            login_timeout=DB_CONFIG['login_timeout']
        )
        cursor = conn.cursor()
        cursor.execute('SELECT @@VERSION')
        row = cursor.fetchone()
        print(f"✅ Connected with hostname! SQL Server Version: {row[0]}")
        
        cursor.execute("SELECT name FROM sys.databases WHERE database_id > 4")
        print("Available databases:")
        for db_row in cursor.fetchall():
            print(f"  - {db_row[0]}")
        
        conn.close()
        print("\n🎉 Connection successful with hostname!")
        return True
    except Exception as e:
        print(f"❌ Connection with hostname failed: {e}")
        return False

def test_connection_to_master():
    print("Testing SQL Server connection to master database...")
    try:
        from database_pymssql import DB_CONFIG
        conn = pymssql.connect(
            server=DB_CONFIG['server'],
            user=DB_CONFIG['username'],
            password=DB_CONFIG['password'],
            database='master',  # Test with master database
            port=DB_CONFIG['port'],
            timeout=DB_CONFIG['timeout'],
            login_timeout=DB_CONFIG['login_timeout']
        )
        cursor = conn.cursor()
        cursor.execute('SELECT @@VERSION')
        row = cursor.fetchone()
        print(f"✅ Connected to master! SQL Server Version: {row[0]}")
        
        # Try to access GAWDB
        cursor.execute("SELECT name FROM sys.databases WHERE name = 'GAWDB'")
        db_exists = cursor.fetchone()
        if db_exists:
            print(f"✅ GAWDB database exists!")
        else:
            print("❌ GAWDB database not found")
        
        conn.close()
        print("\n🎉 Connection to master successful!")
        return True
    except Exception as e:
        print(f"❌ Connection to master failed: {e}")
        return False

if __name__ == "__main__":
    print("Trying multiple connection approaches...\n")
    
    success = False
    
    # Try IP address first
    if test_connection_with_ip():
        success = True
    
    print("\n" + "="*50 + "\n")
    
    # Try hostname
    if not success and test_connection_with_hostname():
        success = True
    
    print("\n" + "="*50 + "\n")
    
    # Try connecting to master database
    if not success and test_connection_to_master():
        success = True
    
    if not success:
        print("\n❌ All connection attempts failed!")
        sys.exit(1) 