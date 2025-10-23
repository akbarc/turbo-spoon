"""
API tests for Georgia Dashboard REST API.

Run with: python -m pytest tests/test_api.py
"""
import sys
from pathlib import Path
import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.app import app

@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == 'Georgia Dashboard API'
    assert data['status'] == 'running'
    assert 'endpoints' in data

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert 'status' in data
    assert 'timestamp' in data
    assert 'database' in data
    assert 'sql_server' in data['database']

def test_ping(client):
    """Test ping endpoint."""
    response = client.get('/api/ping')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'timestamp' in data

def test_executive_summary_default_period(client):
    """Test executive summary with default period."""
    response = client.get('/api/business-overview/executive-summary')
    assert response.status_code == 200
    data = response.get_json()

    # Check structure
    assert 'current_period' in data
    assert 'comparison_period' in data
    assert 'changes' in data
    assert 'period_info' in data

    # Check current period has required fields
    current = data['current_period']
    assert 'revenue' in current
    assert 'transactions' in current
    assert 'unique_customers' in current
    assert 'avg_ticket' in current
    assert 'gross_profit' in current

    # Check changes are calculated
    changes = data['changes']
    assert 'revenue_change' in changes
    assert 'transactions_change' in changes

def test_executive_summary_custom_period(client):
    """Test executive summary with custom date range."""
    response = client.get(
        '/api/business-overview/executive-summary',
        query_string={'start_date': '2025-09-01', 'end_date': '2025-09-30'}
    )
    assert response.status_code == 200
    data = response.get_json()

    # Check period info matches request
    period_info = data['period_info']
    assert period_info['start_date'] == '2025-09-01'
    assert period_info['end_date'] == '2025-09-30'

def test_executive_summary_invalid_period(client):
    """Test executive summary with invalid period."""
    response = client.get(
        '/api/business-overview/executive-summary',
        query_string={'period': 'invalid_period'}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'message' in data

def test_sales_performance(client):
    """Test sales performance endpoint."""
    response = client.get(
        '/api/business-overview/sales-performance',
        query_string={'period': '30d', 'limit': 10}
    )
    assert response.status_code == 200
    data = response.get_json()

    # Check structure
    assert 'top_products' in data
    assert 'categories' in data
    assert 'period_info' in data

    # Check products have required fields
    if len(data['top_products']) > 0:
        product = data['top_products'][0]
        assert 'product' in product
        assert 'revenue' in product
        assert 'net_profit' in product
        assert 'net_margin' in product

def test_sales_trends(client):
    """Test sales trends endpoint."""
    response = client.get(
        '/api/business-overview/sales-trends',
        query_string={'period': '7d'}
    )
    assert response.status_code == 200
    data = response.get_json()

    # Check structure
    assert 'trends' in data
    assert 'summary' in data
    assert 'period_info' in data

    # Check summary has required fields
    summary = data['summary']
    assert 'total_days' in summary
    assert 'avg_daily_revenue' in summary

def test_excise_tax_report(client):
    """Test excise tax report endpoint."""
    response = client.get(
        '/api/excise-tax/report',
        query_string={'period': 'last_month'}
    )
    assert response.status_code == 200
    data = response.get_json()

    # Check structure
    assert 'summary' in data
    assert 'paid_breakdown' in data
    assert 'collected_breakdown' in data
    assert 'compliance_status' in data

    # Check summary fields
    summary = data['summary']
    assert 'excise_paid' in summary
    assert 'excise_collected' in summary
    assert 'difference' in summary
    assert 'recovery_rate' in summary

def test_excise_tax_products(client):
    """Test excise tax products endpoint."""
    response = client.get(
        '/api/excise-tax/products',
        query_string={'limit': 10}
    )
    assert response.status_code == 200
    data = response.get_json()

    # Check structure
    assert 'products' in data
    assert 'period_info' in data

def test_excise_tax_categories(client):
    """Test excise tax categories reference endpoint."""
    response = client.get('/api/excise-tax/categories')
    assert response.status_code == 200
    data = response.get_json()

    # Check structure
    assert 'categories' in data
    assert 'notes' in data

    # Check we have all expected categories
    assert len(data['categories']) == 7

def test_profitability_analysis(client):
    """Test profitability analysis endpoint."""
    response = client.get(
        '/api/profitability/analysis',
        query_string={'period': '30d'}
    )
    assert response.status_code == 200
    data = response.get_json()

    # Check structure
    assert 'overall' in data
    assert 'categories' in data
    assert 'period_info' in data

    # Check overall metrics
    overall = data['overall']
    assert 'total_revenue' in overall
    assert 'gross_profit' in overall
    assert 'net_profit' in overall
    assert 'gross_margin' in overall
    assert 'net_margin' in overall

def test_profitability_top_products(client):
    """Test profitability top products endpoint."""
    response = client.get(
        '/api/profitability/top-products',
        query_string={'limit': 10}
    )
    assert response.status_code == 200
    data = response.get_json()

    # Check structure
    assert 'products' in data
    assert 'period_info' in data

    # Check product fields
    if len(data['products']) > 0:
        product = data['products'][0]
        assert 'product' in product
        assert 'gross_profit' in product
        assert 'net_profit' in product
        assert 'net_margin' in product

def test_profitability_loss_leaders(client):
    """Test profitability loss leaders endpoint."""
    response = client.get(
        '/api/profitability/loss-leaders',
        query_string={'limit': 10, 'min_quantity': 5}
    )
    assert response.status_code == 200
    data = response.get_json()

    # Check structure
    assert 'products' in data
    assert 'note' in data
    assert 'period_info' in data

def test_404_error(client):
    """Test 404 error handling."""
    response = client.get('/api/nonexistent-endpoint')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == 'Not Found'

# Performance tests (optional)
def test_executive_summary_performance(client):
    """Test executive summary responds within acceptable time."""
    import time

    start = time.time()
    response = client.get('/api/business-overview/executive-summary?period=30d')
    end = time.time()

    assert response.status_code == 200
    assert (end - start) < 5.0, "Executive summary took too long"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
