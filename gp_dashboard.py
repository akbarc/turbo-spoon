#!/usr/bin/env python3
"""
Simple Gross Profit Dashboard
Shows today's GP, category breakdown, and excise tax
"""
import os
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify

# Set TDS version BEFORE importing pymssql
os.environ['TDSVER'] = '7.0'

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_foundation.gross_profit import (
    get_gross_profit_summary,
    get_gp_by_category,
    get_gp_by_department,
    get_excise_tax_breakdown
)

app = Flask(__name__)

@app.route('/')
def dashboard():
    """Executive GP dashboard - optimized and fast"""
    return render_template('executive_gp.html')

@app.route('/detailed')
def detailed_dashboard():
    """Detailed GP dashboard"""
    return render_template('gp_dashboard.html')

def parse_date_range(request):
    """Parse start_date and end_date from request parameters"""
    from flask import request as flask_request

    start_date_str = flask_request.args.get('start_date')
    end_date_str = flask_request.args.get('end_date')

    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        # Default to today
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

    return start_date, end_date

@app.route('/api/gp/summary')
def gp_summary():
    """Get GP summary for date range"""
    try:
        start_date, end_date = parse_date_range(None)
        summary = get_gross_profit_summary(start_date, end_date)
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gp/categories')
def gp_categories():
    """Get category breakdown for date range"""
    try:
        start_date, end_date = parse_date_range(None)
        categories = get_gp_by_category(start_date, end_date)
        return jsonify(categories)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gp/departments')
def gp_departments():
    """Get department breakdown for date range"""
    try:
        start_date, end_date = parse_date_range(None)
        departments = get_gp_by_department(start_date, end_date)
        return jsonify(departments)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gp/excise')
def gp_excise():
    """Get excise tax breakdown for date range"""
    try:
        start_date, end_date = parse_date_range(None)
        excise = get_excise_tax_breakdown(start_date, end_date)
        return jsonify(excise)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Legacy endpoint for backward compatibility
@app.route('/api/gp/today')
def gp_today():
    """Get today's GP summary (legacy)"""
    return gp_summary()

@app.route('/api/gp/week')
def gp_week():
    """Get last 7 days GP summary"""
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        summary = get_gross_profit_summary(week_ago, today)
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("="*60)
    print("Gross Profit Dashboard")
    print("="*60)
    print("\nStarting server...")
    print(f"Dashboard: http://localhost:8081")
    print(f"Tailscale: http://100.126.106.37:8081")
    print("\nPress Ctrl+C to stop")
    print("="*60)

    app.run(host='0.0.0.0', port=8081, debug=False, threaded=True)
