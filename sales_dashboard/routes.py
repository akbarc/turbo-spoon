"""
Sales Dashboard Route
This module contains the route for the new sales dashboard page.
"""

from flask import Blueprint, render_template

# Create blueprint for sales dashboard
sales_dashboard_bp = Blueprint(
    'sales_dashboard',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/sales-dashboard'
)

@sales_dashboard_bp.route('/')
def sales_dashboard():
    """Render the sales dashboard page"""
    return render_template('sales_dashboard.html')