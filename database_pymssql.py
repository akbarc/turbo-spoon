import os
import logging
from datetime import datetime, timedelta
import threading
import time

# Set up logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom database exception classes for better error handling
class DatabaseConnectionError(Exception):
    """Raised when database connection fails"""
    pass

class DatabaseQueryError(Exception):
    """Raised when database query execution fails"""
    pass

class ConnectionPoolError(Exception):
    """Raised when connection pool operations fail"""
    pass

class DatabaseTimeoutError(Exception):
    """Raised when database operations timeout"""
    pass

# Set TDS version FIRST before anything else
os.environ['TDSVER'] = '7.0'

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if it exists
    logger.info("✅ Environment variables loaded from .env file")
except ImportError:
    logger.info("ℹ️ python-dotenv not available, using system environment variables only")

# IMPORTANT: Import pymssql BEFORE pandas to avoid connection conflicts!
try:
    import pymssql
    PYMSSQL_AVAILABLE = True
    logger.info("pymssql module available - real database mode")
except ImportError:
    PYMSSQL_AVAILABLE = False
    logger.error("pymssql not available - cannot connect to database")
    raise ImportError("pymssql is required for database connectivity")

# LAZY IMPORT: pandas will be imported only when needed to avoid conflicts
pd = None  # Will be imported in functions that need it

# Database configuration - Environment variables with fallbacks
# Try Tailscale network first, then local network
TAILSCALE_OFFICE_IP = '100.84.221.9'  # Your office network Tailscale IP
LOCAL_OFFICE_IP = '10.1.10.105'       # Direct office IP

DB_CONFIG = {
    'server': os.getenv('DB_SERVER', LOCAL_OFFICE_IP),  # Will be dynamically set
    'port': int(os.getenv('DB_PORT', '1433')),
    'username': os.getenv('DB_USERNAME', 'sa'),  # Default SQL Server username
    'password': os.getenv('DB_PASSWORD', 'your-password'),  # MUST set in environment
    'database': os.getenv('DB_DATABASE', 'GAWDB'),  # Your actual database
    'tds_version': os.getenv('TDS_VERSION', '7.0'),  # Verified working with SQL Server 2008 R2
    'timeout': int(os.getenv('DB_TIMEOUT', '30')),  # Reduced timeout for faster failover
    'login_timeout': int(os.getenv('DB_LOGIN_TIMEOUT', '10'))  # Reduced login timeout
}

class ConnectionPool:
    """Simple connection pool for better performance"""
    
    def __init__(self, max_connections=5):
        self.max_connections = max_connections
        self.pool = []
        self.active_connections = []
        self.lock = threading.Lock()
        self.last_cleanup = time.time()
        
    def get_connection(self):
        """Get a connection from the pool or create a new one"""
        with self.lock:
            # Clean up old connections periodically
            if time.time() - self.last_cleanup > 300:  # 5 minutes
                self._cleanup_connections()
                self.last_cleanup = time.time()
            
            # Try to get from pool first
            if self.pool:
                conn = self.pool.pop()
                self.active_connections.append(conn)
                return conn
            
            # Create new connection if pool is empty
            try:
                conn = self._create_connection()
                if conn:
                    self.active_connections.append(conn)
                    return conn
                else:
                    raise ConnectionPoolError("Failed to create new database connection")
            except (DatabaseConnectionError, ConnectionPoolError):
                raise
            except Exception as e:
                logger.error(f"❌ Unexpected error creating connection: {e}")
                raise ConnectionPoolError(f"Unexpected connection creation error: {e}")
    
    def return_connection(self, conn):
        """Return connection to pool"""
        with self.lock:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
                
            # Test if connection is still valid
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                cursor.fetchone()
                cursor.close()
                # Connection is good, add to pool
                if len(self.pool) < self.max_connections:
                    self.pool.append(conn)
                    logger.debug("🔄 Connection returned to pool")
                else:
                    conn.close()
                    logger.debug("🗑️ Pool full, closing connection")
            except Exception as e:
                # Connection is bad, close it safely
                logger.warning(f"⚠️ Connection validation failed: {e}")
                try:
                    conn.close()
                    logger.debug("❌ Bad connection closed safely")
                except Exception as close_error:
                    logger.error(f"❌ Error closing bad connection: {close_error}")
    
    def _create_connection(self):
        """Create a new database connection using pymssql"""
        if not PYMSSQL_AVAILABLE:
            raise DatabaseConnectionError("pymssql driver not available")
            
        try:
            conn = pymssql.connect(
                server=DB_CONFIG['server'],
                user='amchranya',  # Use working credentials
                password='2000Akbar!',  # Use working credentials  
                database='GAWDB',  # Use correct database
                port=DB_CONFIG['port'],
                timeout=30,  # Shorter timeout
                login_timeout=10,  # Shorter login timeout
                tds_version='7.0'  # Force TDS 7.0
            )
            logger.info(f"✅ Successfully connected to SQL Server: {DB_CONFIG['server']}")
            return conn
        except pymssql.InterfaceError as e:
            logger.error(f"❌ Database interface error: {e}")
            raise DatabaseConnectionError(f"Interface error connecting to database: {e}")
        except pymssql.DatabaseError as e:
            logger.error(f"❌ Database error: {e}")
            raise DatabaseConnectionError(f"Database error: {e}")
        except pymssql.OperationalError as e:
            logger.error(f"❌ Operational error (connection/server issue): {e}")
            raise DatabaseConnectionError(f"Connection operational error: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected connection error: {e}")
            raise DatabaseConnectionError(f"Unexpected database connection error: {e}")
    
    def _cleanup_connections(self):
        """Clean up old or bad connections"""
        logger.debug("🧹 Cleaning up connection pool")
        connections_to_remove = []
        
        for conn in self.pool[:]:
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                cursor.fetchone()
                cursor.close()
            except Exception as e:
                logger.debug(f"🔍 Connection validation failed during cleanup: {e}")
                connections_to_remove.append(conn)
        
        # Remove bad connections
        for conn in connections_to_remove:
            try:
                self.pool.remove(conn)
                conn.close()
                logger.debug("🗑️ Removed bad connection from pool")
            except Exception as e:
                logger.warning(f"⚠️ Error removing bad connection: {e}")

# Global connection pool
connection_pool = ConnectionPool(max_connections=3)

class SQLServerConnection:
    def __init__(self):
        self.connection = None
        self.backup_connection = None
        self.is_using_backup = False
        # DISABLE CONNECTION POOLING TO PREVENT CRASHES
        self.use_pool = False  # Changed from True to False
        self.backup_db_path = 'georgia_dashboard.db'
        
        # Set TDS version immediately
        import os
        os.environ['TDSVER'] = '7.0'
        
    def connect(self):
        """Connect to SQL Server database via Tailscale subnet routing"""
        if not PYMSSQL_AVAILABLE:
            raise DatabaseConnectionError("pymssql driver not available - cannot connect to database")

        logger.info("🔄 Connecting to SQL Server via Tailscale subnet routing...")
        logger.info(f"🔍 Connection parameters: server='10.1.10.105', database='GAWDB', tds_version='7.0'")
        logger.info(f"🔍 TDS environment variable: {os.environ.get('TDSVER', 'NOT SET')}")

        # Use EXACT same approach as working test - single attempt, no retry
        import pymssql
        import socket

        # First test socket connectivity
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('10.1.10.105', 1433))
            sock.close()
            if result == 0:
                logger.info("✅ Socket test: Port 1433 is reachable")
            else:
                logger.error(f"❌ Socket test failed: {result}")
        except Exception as e:
            logger.error(f"❌ Socket test exception: {e}")

        # Now try actual connection
        logger.info("🔄 Attempting pymssql.connect()...")
        self.connection = pymssql.connect(
            server='10.1.10.105',
            user='amchranya',
            password='2000Akbar!',
            database='GAWDB',
            tds_version='7.0',
            timeout=30,
            login_timeout=10
        )

        logger.info("✅ Successfully connected to SQL Server via Tailscale subnet routing!")
        self.is_using_backup = False
        return True
    
    def close(self):
        """Close database connection with better TDS cleanup"""
        if self.connection:
            try:
                if self.use_pool:
                    connection_pool.return_connection(self.connection)
                else:
                    # Try to cancel any pending operations to avoid TDS assertion errors
                    try:
                        if hasattr(self.connection, 'cancel'):
                            self.connection.cancel()
                    except:
                        pass  # Ignore cancel errors
                    
                    # Close the connection
                    self.connection.close()
                    logger.debug("🔌 Database connection closed cleanly")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self.connection = None
    
    def test_connection(self):
        """Test database connectivity"""
        try:
            if not self.connection:
                self.connect()
            
            cursor = self.connection.cursor()
            cursor.execute("SELECT @@VERSION, @@SERVERNAME, DB_NAME()")
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                logger.info(f"✅ Database test successful: {result[1]} - {result[2]}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Database test failed: {e}")
            raise Exception(f"Database connectivity test failed: {e}")
    
    def execute_query(self, query, params=None, description="Query", use_cache=False, retry_count=3):
        """Execute SQL query and return pandas DataFrame with retry logic for TDS timeouts"""
        # Lazy import pandas to avoid conflicts with pymssql
        import pandas as pd

        if not self.connection:
            if not self.connect():
                raise Exception("No database connection available")

        last_error = None
        for attempt in range(retry_count):
            try:
                # Add small delay to prevent TDS overload
                time.sleep(0.1)

                if attempt > 0:
                    logger.info(f"🔄 Retry attempt {attempt + 1}/{retry_count} for: {description}")
                else:
                    logger.info(f"🔍 Executing: {description}")

                cursor = self.connection.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                cursor.close()

                df = pd.DataFrame(results, columns=columns)
                logger.info(f"✅ {description} successful: {len(df)} rows")
                return df
                
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                # Check for TDS timeout or connection errors
                if 'tds' in error_msg or 'timeout' in error_msg or 'dead' in error_msg:
                    logger.warning(f"⚠️ TDS/timeout error on attempt {attempt + 1}: {e}")
                    
                    # Reconnect for next attempt
                    try:
                        self.close()
                    except:
                        pass
                    
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        self.connect()
                        continue
                else:
                    # Non-retryable error
                    logger.error(f"❌ {description} failed: {e}")
                    break
        
        # All retries exhausted or non-retryable error
        logger.error(f"❌ {description} failed after {retry_count} attempts: {last_error}")
        # Return empty dataframe to prevent server crashes
        return pd.DataFrame()
    
    def get_tables(self, schema='dbo'):
        """Get list of tables in the database"""
        query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = ? AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
        """
        return self.execute_query(query, params=[schema], description="Get Tables List")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

def quick_query(query, params=None):
    """
    Quick query execution function
    Returns pandas DataFrame or raises exception if connection fails
    """
    try:
        with SQLServerConnection() as db:
            return db.execute_query(query, params)
    except Exception as e:
        logger.error(f"Quick query failed: {e}")
        raise Exception(f"Database query failed: {e}")

def test_database_connectivity():
    """Test database connectivity and return basic info"""
    query = """
    SELECT 
        @@SERVERNAME as server_name,
        @@VERSION as version,
        DB_NAME() as current_database,
        SYSTEM_USER as login_user
    """
    return quick_query(query)

def get_table_list():
    """Get list of all tables"""
    with SQLServerConnection() as db:
        return db.get_tables()

def sample_table_data(table_name, schema='dbo', limit=10):
    """Get sample data from a table"""
    # Validate and sanitize inputs to prevent SQL injection
    try:
        safe_limit = int(limit)
        if safe_limit < 1 or safe_limit > 1000:
            safe_limit = 10
    except (ValueError, TypeError):
        safe_limit = 10
    
    # Sanitize table and schema names (allow only alphanumeric, underscore, dash)
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', str(table_name)) or not re.match(r'^[a-zA-Z0-9_-]+$', str(schema)):
        raise ValueError("Invalid table or schema name")
    
    query = f"SELECT TOP {safe_limit} * FROM [{schema}].[{table_name}]"
    return quick_query(query) 