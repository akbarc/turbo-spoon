"""
Sales Dashboard V2 - Main Routes Integration
Combines all dashboard features and APIs
"""

from flask import Blueprint, render_template, send_from_directory
import os

# Import API blueprints
from sales_dashboard_v2.backend.sales_api import sales_api
from sales_dashboard_v2.backend.advanced_analytics import analytics_api

# Create main blueprint
dashboard_v2 = Blueprint(
    'dashboard_v2',
    __name__,
    template_folder='frontend',
    static_folder='frontend',
    url_prefix='/dashboard-v2'
)

# Register API blueprints
dashboard_v2.register_blueprint(sales_api)
dashboard_v2.register_blueprint(analytics_api)

@dashboard_v2.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@dashboard_v2.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files"""
    return send_from_directory(os.path.join(dashboard_v2.static_folder, 'js'), filename)

@dashboard_v2.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files"""
    return send_from_directory(os.path.join(dashboard_v2.static_folder, 'css'), filename)

@dashboard_v2.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve asset files"""
    return send_from_directory(os.path.join(dashboard_v2.static_folder, 'assets'), filename)