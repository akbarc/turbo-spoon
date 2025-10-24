// Sales Dashboard JavaScript

// Global variables
let currentPeriod = 'today';
let autoRefreshInterval = null;
let salesTrendChart = null;
let categoryChart = null;

// Initialize on page load
$(document).ready(function() {
    initializeDashboard();
    setupEventHandlers();
    updateClock();
    loadDashboardData();
});

// Initialize dashboard components
function initializeDashboard() {
    // Initialize charts
    initializeSalesTrendChart();
    initializeCategoryChart();

    // Set up clock
    setInterval(updateClock, 1000);
}

// Setup event handlers
function setupEventHandlers() {
    // Period buttons
    $('.period-btn').on('click', function() {
        $('.period-btn').removeClass('active');
        $(this).addClass('active');
        currentPeriod = $(this).data('period');
        loadDashboardData();
    });

    // Auto refresh toggle
    $('#autoRefresh').on('change', function() {
        if ($(this).is(':checked')) {
            autoRefreshInterval = setInterval(loadDashboardData, 30000); // 30 seconds
        } else {
            if (autoRefreshInterval) {
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
            }
        }
    });
}

// Update clock
function updateClock() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    $('#currentTime').text(timeString);
}

// Load dashboard data
function loadDashboardData() {
    // Show loading state
    showLoadingState();

    // Calculate date range based on period
    const dateRange = getDateRange(currentPeriod);
    console.log('Loading data for period:', currentPeriod, 'Date range:', dateRange);

    // Load all data components
    Promise.all([
        loadSalesOverview(dateRange),
        loadSalesPerformance(dateRange),
        loadRecentTransactions(),
        loadSalesOpsOverview(),
        loadSalesTrends(dateRange)
    ]).then(() => {
        hideLoadingState();
        console.log('Dashboard data loaded successfully');
    }).catch(error => {
        console.error('Error loading dashboard:', error);
        hideLoadingState();
        showErrorMessage('Failed to load dashboard data');
    });
}

// Get date range based on period
function getDateRange(period) {
    const now = new Date();
    let startDate, endDate = now.toISOString().split('T')[0];

    switch (period) {
        case 'today':
            startDate = endDate;
            break;
        case 'yesterday':
            const yesterday = new Date(now);
            yesterday.setDate(yesterday.getDate() - 1);
            startDate = endDate = yesterday.toISOString().split('T')[0];
            break;
        case '7d':
            const week = new Date(now);
            week.setDate(week.getDate() - 7);
            startDate = week.toISOString().split('T')[0];
            break;
        case '30d':
            const month = new Date(now);
            month.setDate(month.getDate() - 30);
            startDate = month.toISOString().split('T')[0];
            break;
        case 'MTD':
            startDate = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
            break;
        case 'YTD':
            startDate = new Date(now.getFullYear(), 0, 1).toISOString().split('T')[0];
            break;
        default:
            startDate = endDate;
    }

    return { start: startDate, end: endDate, period: period };
}

// Load sales overview (KPI cards)
function loadSalesOverview(dateRange) {
    // For yesterday, use the specific date in sales-ops/overview
    if (currentPeriod === 'yesterday') {
        return $.ajax({
            url: '/api/sales-ops/overview',
            method: 'GET',
            data: { date: dateRange.start },
            success: function(response) {
                updateKPICards(response);
            },
            error: function(xhr) {
                console.error('Failed to load sales overview:', xhr.responseText);
            }
        });
    }

    // For other periods, use the sales-performance endpoint
    const url = currentPeriod === 'today' ?
        '/api/sales-ops/overview' :
        '/api/business-overview/sales-performance';

    const params = currentPeriod === 'today' ?
        { date: dateRange.start } :
        {
            period: currentPeriod,
            start_date: dateRange.start,
            end_date: dateRange.end
        };

    return $.ajax({
        url: url,
        method: 'GET',
        data: params,
        success: function(response) {
            updateKPICards(response);
        },
        error: function(xhr) {
            console.error('Failed to load sales overview:', xhr.responseText);
        }
    });
}

// Update KPI cards with data
function updateKPICards(response) {
    if (response.sales) {
        $('#totalSales').text(formatCurrency(response.sales.total_sales || 0));
        $('#totalTransactions').text(formatNumber(response.sales.total_transactions || 0));
        $('#unitsSold').text(formatNumber(response.sales.total_units || 0));
        $('#uniqueCustomers').text(formatNumber(response.sales.unique_customers || 0));
        $('#avgTransaction').text(formatCurrency(response.sales.avg_transaction || 0));

        // Calculate units per transaction
        const unitsPerTrans = response.sales.total_transactions > 0 ?
            (response.sales.total_units / response.sales.total_transactions).toFixed(1) : 0;
        $('#unitsPerTransaction').text(unitsPerTrans);
    }

    if (response.payments) {
        $('#totalPayments').text(formatCurrency(response.payments.total_amount || 0));
        $('#paymentCount').text(formatNumber(response.payments.total_payments || 0));
        $('#customersWhoPage').text(formatNumber(response.payments.customers_paid || 0));
    }
}

// Load sales performance (top products and categories)
function loadSalesPerformance(dateRange) {
    return $.ajax({
        url: '/api/business-overview/sales-performance',
        method: 'GET',
        data: {
            period: currentPeriod,
            start_date: dateRange.start,
            end_date: dateRange.end
        },
        success: function(response) {
            // Update top products table
            if (response.top_products) {
                updateTopProductsTable(response.top_products);
            }

            // Update category chart
            if (response.category_performance) {
                updateCategoryChart(response.category_performance);
            }
        }
    });
}

// Load recent transactions
function loadRecentTransactions() {
    // Always show today's recent transactions regardless of period selected
    return $.ajax({
        url: '/api/sales-ops/sales-detail',
        method: 'GET',
        data: {
            date: new Date().toISOString().split('T')[0],
            limit: 20
        },
        success: function(response) {
            updateRecentTransactionsTable(response.transactions || []);
        },
        error: function(xhr) {
            console.error('Failed to load recent transactions:', xhr.responseText);
            updateRecentTransactionsTable([]);
        }
    });
}

// Load sales ops overview (cashier performance)
function loadSalesOpsOverview() {
    return $.ajax({
        url: '/api/sales-ops/overview',
        method: 'GET',
        data: {
            date: new Date().toISOString().split('T')[0]
        },
        success: function(response) {
            if (response.operations && response.operations.cashier_activity) {
                updateCashierPerformance(response.operations.cashier_activity);
            }
        },
        error: function(xhr) {
            console.error('Failed to load cashier performance:', xhr.responseText);
            updateCashierPerformance([]);
        }
    });
}

// Load sales trends
function loadSalesTrends(dateRange) {
    return $.ajax({
        url: '/api/business-overview/sales-trends',
        method: 'GET',
        data: {
            period: currentPeriod
        },
        success: function(response) {
            if (response.daily_sales) {
                updateSalesTrendChart(response.daily_sales);
            }
        },
        error: function(xhr) {
            console.error('Failed to load sales trends:', xhr.responseText);
            updateSalesTrendChart([]);
        }
    });
}

// Update top products table
function updateTopProductsTable(products) {
    const tbody = $('#topProductsTable');
    tbody.empty();

    if (!products || products.length === 0) {
        tbody.append('<tr><td colspan="4" class="text-center text-muted">No sales data for this period</td></tr>');
        return;
    }

    products.forEach((product, index) => {
        const row = `
            <tr class="fade-in" style="animation-delay: ${index * 0.05}s">
                <td>
                    <div class="d-flex align-items-center">
                        <span class="badge bg-primary me-2">${index + 1}</span>
                        <span class="text-truncate" style="max-width: 200px;" title="${product.name}">
                            ${product.name}
                        </span>
                    </div>
                </td>
                <td class="text-end"><strong>$${formatCurrency(product.revenue)}</strong></td>
                <td class="text-end">${formatNumber(product.units_sold)}</td>
                <td class="text-end">
                    <span class="text-success">$${formatCurrency(product.gross_profit || 0)}</span>
                </td>
            </tr>
        `;
        tbody.append(row);
    });
}

// Update recent transactions table
function updateRecentTransactionsTable(transactions) {
    const tbody = $('#recentTransactionsTable');
    tbody.empty();

    if (!transactions || transactions.length === 0) {
        tbody.append('<tr><td colspan="4" class="text-center text-muted">No recent transactions</td></tr>');
        return;
    }

    transactions.forEach((trans, index) => {
        const row = `
            <tr class="fade-in" style="animation-delay: ${index * 0.05}s">
                <td>${trans.time}</td>
                <td class="text-truncate" style="max-width: 150px;" title="${trans.customer_name}">
                    ${trans.customer_name}
                </td>
                <td class="text-end"><strong>$${formatCurrency(trans.total)}</strong></td>
                <td class="text-center">
                    <span class="badge bg-info">${trans.line_items}</span>
                </td>
            </tr>
        `;
        tbody.append(row);
    });
}

// Update cashier performance
function updateCashierPerformance(cashiers) {
    const container = $('#cashierPerformance');
    container.empty();

    if (cashiers.length === 0) {
        container.html('<p class="text-muted">No cashier activity today</p>');
        return;
    }

    const maxSales = Math.max(...cashiers.map(c => c.sales_volume));

    cashiers.forEach(cashier => {
        const percentage = (cashier.sales_volume / maxSales) * 100;
        const item = `
            <div class="cashier-item">
                <div class="d-flex justify-content-between mb-2">
                    <span><strong>Cashier ${cashier.cashier_id}</strong></span>
                    <span>$${formatCurrency(cashier.sales_volume)}</span>
                </div>
                <div class="progress">
                    <div class="progress-bar bg-primary" style="width: ${percentage}%"></div>
                </div>
                <small class="text-muted">${cashier.transactions} transactions</small>
            </div>
        `;
        container.append(item);
    });
}

// Initialize Sales Trend Chart
function initializeSalesTrendChart() {
    const ctx = document.getElementById('salesTrendChart').getContext('2d');
    salesTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Sales',
                data: [],
                borderColor: 'rgb(13, 110, 253)',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Sales: $' + formatCurrency(context.raw);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + formatCurrency(value);
                        }
                    }
                }
            }
        }
    });
}

// Update Sales Trend Chart
function updateSalesTrendChart(data) {
    if (!salesTrendChart || !data || data.length === 0) return;

    const labels = data.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const values = data.map(d => d.sales);

    salesTrendChart.data.labels = labels;
    salesTrendChart.data.datasets[0].data = values;
    salesTrendChart.update();
}

// Initialize Category Chart
function initializeCategoryChart() {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    categoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    'rgba(13, 110, 253, 0.8)',
                    'rgba(25, 135, 84, 0.8)',
                    'rgba(255, 193, 7, 0.8)',
                    'rgba(220, 53, 69, 0.8)',
                    'rgba(13, 202, 240, 0.8)',
                    'rgba(111, 66, 193, 0.8)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 10,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.label + ': $' + formatCurrency(context.raw);
                        }
                    }
                }
            }
        }
    });
}

// Update Category Chart
function updateCategoryChart(categories) {
    if (!categoryChart || !categories || categories.length === 0) return;

    const topCategories = categories.slice(0, 6);
    const labels = topCategories.map(c => c.category_name);
    const values = topCategories.map(c => c.revenue);

    categoryChart.data.labels = labels;
    categoryChart.data.datasets[0].data = values;
    categoryChart.update();
}

// Utility Functions
function formatCurrency(value) {
    // Handle undefined, null, or non-numeric values
    const num = parseFloat(value) || 0;
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(num);
}

function formatNumber(value) {
    // Handle undefined, null, or non-numeric values
    const num = parseInt(value) || 0;
    return new Intl.NumberFormat('en-US').format(num);
}

function showLoadingState() {
    $('.kpi-card').addClass('loading-state');
}

function hideLoadingState() {
    $('.kpi-card').removeClass('loading-state');
}

function showErrorMessage(message) {
    console.error(message);
    // Could add a toast notification here
}

// Export functions
function exportTopProducts() {
    // Implementation for exporting top products
    window.location.href = `/api/export/top-products?period=${currentPeriod}`;
}