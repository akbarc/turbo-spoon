"""
Georgia Dashboard REST API

Flask-based REST API providing programmatic access to the GAWDB database.
Complements the Streamlit dashboard with API endpoints for integrations.
"""
import os
import sys
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS
from flask_caching import Cache

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.sql_server import db

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# CORS configuration (adjust for production)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # TODO: Restrict in production
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Caching configuration
cache_config = {
    'CACHE_TYPE': os.getenv('CACHE_TYPE', 'simple'),
    'CACHE_DEFAULT_TIMEOUT': int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))
}
app.config.from_mapping(cache_config)
cache = Cache(app)

# Register blueprints
from routes.health import health_bp
from routes.business_overview import business_bp
from routes.excise_tax import excise_bp
from routes.profitability import profitability_bp

app.register_blueprint(health_bp, url_prefix='/api')
app.register_blueprint(business_bp, url_prefix='/api/business-overview')
app.register_blueprint(excise_bp, url_prefix='/api/excise-tax')
app.register_blueprint(profitability_bp, url_prefix='/api/profitability')

# Root endpoint
@app.route('/')
def index():
    """API root endpoint."""
    return jsonify({
        "name": "Georgia Dashboard API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/api/docs",
        "endpoints": {
            "health": "/api/health",
            "business_overview": {
                "executive_summary": "/api/business-overview/executive-summary",
                "sales_performance": "/api/business-overview/sales-performance",
                "sales_trends": "/api/business-overview/sales-trends"
            },
            "excise_tax": {
                "report": "/api/excise-tax/report",
                "breakdown": "/api/excise-tax/breakdown"
            },
            "profitability": {
                "analysis": "/api/profitability/analysis",
                "category": "/api/profitability/category",
                "product": "/api/profitability/product"
            }
        }
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Not Found",
        "message": "The requested endpoint does not exist",
        "status_code": 404
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred",
        "status_code": 500
    }), 500

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all other exceptions."""
    return jsonify({
        "error": error.__class__.__name__,
        "message": str(error),
        "status_code": 500
    }), 500

if __name__ == '__main__':
    # Get configuration from environment
    port = int(os.getenv('API_PORT', 5000))
    host = os.getenv('API_HOST', '0.0.0.0')
    debug = os.getenv('API_DEBUG', 'False').lower() == 'true'

    print(f"Starting Georgia Dashboard API on {host}:{port}")
    print(f"Debug mode: {debug}")

    app.run(host=host, port=port, debug=debug, threaded=True)
