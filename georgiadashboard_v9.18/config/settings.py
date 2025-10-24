"""
Georgia Dashboard v9.18 Configuration Settings
Enhanced configuration with better organization and validation
"""
import os
from pathlib import Path
from typing import Dict, Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional


class Config:
    """Base configuration with all common settings"""
    
    # Base paths
    BASE_DIR = Path(__file__).parent.parent.absolute()
    DATA_DIR = BASE_DIR / 'data'
    EXPORT_DIR = DATA_DIR / 'exports'
    UPLOAD_DIR = DATA_DIR / 'uploads'
    LOGS_DIR = BASE_DIR / 'logs'
    TEMPLATES_DIR = BASE_DIR / 'templates'
    STATIC_DIR = BASE_DIR / 'static'
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # Server Configuration
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 8081))
    
    # Database Configuration
    DB_CONFIG = {
        'server': os.getenv('DB_SERVER', '10.1.10.105'),
        'port': int(os.getenv('DB_PORT', 1433)),
        'username': os.getenv('DB_USERNAME', ''),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_DATABASE', 'GAWDB'),
        'tds_version': os.getenv('TDS_VERSION', '7.0'),
        'timeout': int(os.getenv('DB_TIMEOUT', 60)),
        'login_timeout': int(os.getenv('DB_LOGIN_TIMEOUT', 15)),
    }
    
    # Performance Configuration
    MAX_DB_CONNECTIONS = int(os.getenv('MAX_DB_CONNECTIONS', 3))
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
    CACHE_TTL = int(os.getenv('CACHE_TTL', 300))  # 5 minutes default
    
    # Application Settings
    ITEMS_PER_PAGE = 50
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'json'}
    
    # API Settings
    API_TIMEOUT = 30
    API_RATE_LIMIT = "100 per hour"
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = LOGS_DIR / 'app.log'
    
    # Business Logic Configuration
    TOBACCO_UPLIFTS = {
        'CIGARS': 1.23,  # 23% uplift
        'LT-TAX-COLLECTED': 1.10,  # 10% uplift
    }
    
    # AI Assistant Configuration (Optional)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    AI_ENABLED = bool(OPENAI_API_KEY)
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate configuration and return status"""
        issues = []
        
        # Check required database settings
        if not cls.DB_CONFIG['username']:
            issues.append("DB_USERNAME is required")
        if not cls.DB_CONFIG['password']:
            issues.append("DB_PASSWORD is required")
            
        # Check directory existence
        for dir_path in [cls.DATA_DIR, cls.LOGS_DIR]:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'ai_enabled': cls.AI_ENABLED,
            'database_configured': bool(cls.DB_CONFIG['username'] and cls.DB_CONFIG['password'])
        }


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = 'INFO'
    SECRET_KEY = os.getenv('SECRET_KEY')  # Must be set in production
    
    @classmethod
    def validate_config(cls):
        """Enhanced validation for production"""
        result = super().validate_config()
        
        # Additional production checks
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            result['issues'].append("SECRET_KEY must be changed in production")
            result['valid'] = False
            
        return result


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    
    # Use in-memory cache for testing
    CACHE_TYPE = 'simple'
    CACHE_TTL = 60


# Configuration dictionary
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str = None) -> Config:
    """Get configuration class based on environment"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    return config_map.get(config_name, config_map['default'])
