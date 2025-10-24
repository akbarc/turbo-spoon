#!/usr/bin/env python3
"""
Test script to verify Vercel deployment compatibility
Tests mock data mode when pymssql is not available
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_mock_database():
    """Test database connection in mock mode"""
    print("🧪 Testing database connection in mock mode...")
    
    try:
        from database_pymssql import SQLServerConnection
        
        # Initialize connection
        db = SQLServerConnection()
        
        # Test connection
        if db.connect():
            print("✅ Database connection successful (mock mode)")
        else:
            print("❌ Database connection failed")
            return False
        
        # Test basic query
        result = db.execute_query("SELECT 1 as test")
        if not result.empty:
            print("✅ Basic query successful")
        else:
            print("❌ Basic query failed")
            return False
        
        # Test sales data query
        sales_query = """
        SELECT SUM(NetSales) as NetSales, COUNT(*) as Invoices 
        FROM TransactionEntry 
        WHERE Date >= '2025-01-01'
        """
        result = db.execute_query(sales_query)
        if not result.empty:
            print(f"✅ Sales query successful: {result.to_dict('records')[0]}")
        else:
            print("❌ Sales query failed")
            return False
        
        print("✅ All database tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_flask_app():
    """Test Flask app import and basic functionality"""
    print("\n🧪 Testing Flask app import...")
    
    try:
        # Import the main app
        from unified_dashboard import app, analytics
        
        print("✅ Flask app imported successfully")
        
        # Test that app is configured correctly
        if app.config.get('TESTING') is not False:
            print("✅ Flask app configuration OK")
        
        # Test analytics engine
        if analytics:
            print("✅ Analytics engine initialized")
        
        print("✅ All Flask tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Flask test failed: {e}")
        return False

def test_vercel_entry_point():
    """Test Vercel entry point"""
    print("\n🧪 Testing Vercel entry point...")
    
    try:
        # Test api/index.py import
        sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))
        from api.index import app as vercel_app
        
        print("✅ Vercel entry point imported successfully")
        
        if vercel_app:
            print("✅ Vercel app object exists")
        
        print("✅ All Vercel tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Vercel test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Vercel Deployment Compatibility")
    print("=" * 50)
    
    tests = [
        ("Database Mock Mode", test_mock_database),
        ("Flask App", test_flask_app),
        ("Vercel Entry Point", test_vercel_entry_point)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        if test_func():
            passed += 1
        print("-" * 30)
    
    print(f"\n🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Ready for Vercel deployment!")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 