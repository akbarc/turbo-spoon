#!/usr/bin/env python3
"""
Simple Georgia Dashboard - Just Daily Sales
Focus: Get it working first!
"""
import os
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set TDS version BEFORE importing pymssql
os.environ['TDSVER'] = '7.0'

# Import pymssql BEFORE anything else
import pymssql

# Create Flask app
app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'amchranya',
    'password': '2000Akbar!',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 30,
    'login_timeout': 10
}

def get_db_connection():
    """Get a fresh database connection"""
    return pymssql.connect(
        server=DB_CONFIG['server'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        tds_version=DB_CONFIG['tds_version'],
        timeout=DB_CONFIG['timeout'],
        login_timeout=DB_CONFIG['login_timeout']
    )

def execute_query(query, params=None):
    """Execute query and return results as list of dicts"""
    conn = get_db_connection()
    cursor = conn.cursor(as_dict=True)

    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return results

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Georgia Dashboard - Daily Sales</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric {
            display: inline-block;
            margin: 10px 20px;
            text-align: center;
        }
        .metric-value {
            font-size: 36px;
            font-weight: bold;
            color: #4CAF50;
        }
        .metric-label {
            font-size: 14px;
            color: #666;
            text-transform: uppercase;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #4CAF50;
            color: white;
        }
        tr:hover {
            background: #f5f5f5;
        }
        .refresh {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        .refresh:hover {
            background: #45a049;
        }
        .loading {
            color: #666;
            font-style: italic;
        }
        .error {
            color: #d32f2f;
            background: #ffebee;
            padding: 10px;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <h1>📊 Georgia Dashboard - Today's Sales</h1>

    <div class="card">
        <h2>Summary</h2>
        <div id="summary">Loading...</div>
        <button class="refresh" onclick="loadData()">Refresh Data</button>
    </div>

    <div class="card">
        <h2>Recent Transactions</h2>
        <div id="transactions">Loading...</div>
    </div>

    <script>
        function formatCurrency(value) {
            return '$' + Number(value).toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
        }

        function formatDate(dateStr) {
            const date = new Date(dateStr);
            return date.toLocaleString();
        }

        async function loadData() {
            try {
                // Load summary
                document.getElementById('summary').innerHTML = '<p class="loading">Loading summary...</p>';
                const summaryRes = await fetch('/api/daily-summary');
                const summary = await summaryRes.json();

                if (summary.error) {
                    document.getElementById('summary').innerHTML = `<p class="error">Error: ${summary.error}</p>`;
                } else {
                    document.getElementById('summary').innerHTML = `
                        <div class="metric">
                            <div class="metric-value">${formatCurrency(summary.total_sales)}</div>
                            <div class="metric-label">Total Sales</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${summary.transaction_count}</div>
                            <div class="metric-label">Transactions</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${formatCurrency(summary.avg_ticket)}</div>
                            <div class="metric-label">Avg Ticket</div>
                        </div>
                    `;
                }

                // Load transactions
                document.getElementById('transactions').innerHTML = '<p class="loading">Loading transactions...</p>';
                const txRes = await fetch('/api/recent-transactions');
                const transactions = await txRes.json();

                if (transactions.error) {
                    document.getElementById('transactions').innerHTML = `<p class="error">Error: ${transactions.error}</p>`;
                } else if (transactions.length === 0) {
                    document.getElementById('transactions').innerHTML = '<p>No transactions today.</p>';
                } else {
                    let html = `
                        <table>
                            <thead>
                                <tr>
                                    <th>Time</th>
                                    <th>Transaction #</th>
                                    <th>Customer</th>
                                    <th>Amount</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;

                    transactions.forEach(tx => {
                        html += `
                            <tr>
                                <td>${formatDate(tx.Time)}</td>
                                <td>#${tx.TransactionNumber}</td>
                                <td>${tx.CustomerName || 'Walk-in'}</td>
                                <td>${formatCurrency(tx.Total)}</td>
                            </tr>
                        `;
                    });

                    html += '</tbody></table>';
                    document.getElementById('transactions').innerHTML = html;
                }
            } catch (err) {
                document.getElementById('summary').innerHTML = `<p class="error">Error loading data: ${err.message}</p>`;
                document.getElementById('transactions').innerHTML = '';
            }
        }

        // Load data on page load
        loadData();

        // Auto-refresh every 30 seconds
        setInterval(loadData, 30000);
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    """Home page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/daily-summary')
def daily_summary():
    """Get today's sales summary"""
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        query = """
        SELECT
            COALESCE(SUM(Total), 0) as total_sales,
            COUNT(*) as transaction_count,
            COALESCE(AVG(Total), 0) as avg_ticket
        FROM [dbo].[Transaction]
        WHERE Time >= %s
        """

        results = execute_query(query, (today,))

        if results:
            data = results[0]
            return jsonify({
                'total_sales': float(data['total_sales']),
                'transaction_count': int(data['transaction_count']),
                'avg_ticket': float(data['avg_ticket'])
            })
        else:
            return jsonify({'error': 'No data returned'})

    except Exception as e:
        print(f"Error in daily_summary: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent-transactions')
def recent_transactions():
    """Get recent transactions from today"""
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        query = """
        SELECT TOP 20
            t.TransactionNumber,
            t.Time,
            t.Total,
            c.Company as CustomerName
        FROM [dbo].[Transaction] t
        LEFT JOIN [dbo].[Customer] c ON t.CustomerID = c.ID
        WHERE t.Time >= %s
        ORDER BY t.Time DESC
        """

        results = execute_query(query, (today,))

        # Convert datetime objects to strings for JSON
        for row in results:
            if 'Time' in row and row['Time']:
                row['Time'] = row['Time'].isoformat()

        return jsonify(results)

    except Exception as e:
        print(f"Error in recent_transactions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-connection')
def test_connection():
    """Test database connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION, @@SERVERNAME, DB_NAME()")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return jsonify({
            'status': 'connected',
            'server': result[1],
            'database': result[2]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Simple Georgia Dashboard")
    print("📊 URL: http://localhost:8080")
    print("🔗 Via Tailscale: http://100.126.106.37:8080")

    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False  # No debug mode to avoid reloader
    )
