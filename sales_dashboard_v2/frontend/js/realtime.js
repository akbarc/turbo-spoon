/**
 * Sales Dashboard Pro - Real-time Updates Module
 * Live data feeds, alerts, and advanced analytics
 */

// Real-time update interval
let realtimeInterval = null;
let alertCheckInterval = null;

// Initialize real-time features
function startRealTimeUpdates() {
    // Load initial real-time data
    loadRealTimeFeed();
    loadInventoryIntelligence();
    loadProfitOptimization();
    loadCLVAnalysis();
    loadSalesTeamPerformance();
    checkAlerts();

    // Set up intervals
    realtimeInterval = setInterval(() => {
        loadRealTimeFeed();
        updateLiveMetrics();
    }, 10000); // Update every 10 seconds

    alertCheckInterval = setInterval(() => {
        checkAlerts();
    }, 60000); // Check alerts every minute
}

// Load real-time transaction feed
async function loadRealTimeFeed() {
    try {
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/sales/real-time-feed',
            method: 'GET'
        });

        updateActivityFeed(response.transactions);

    } catch (error) {
        console.error('Error loading real-time feed:', error);
    }
}

// Update activity feed
function updateActivityFeed(transactions) {
    const $feed = $('#activityFeed');
    $feed.empty();

    if (!transactions || transactions.length === 0) {
        $feed.append('<p class="text-muted text-center">No recent activity</p>');
        return;
    }

    transactions.forEach((trans, index) => {
        const feedItem = `
            <div class="activity-item fade-in" style="animation-delay: ${index * 0.05}s">
                <div class="activity-icon">
                    <i class="fas fa-shopping-cart text-success"></i>
                </div>
                <div class="activity-content">
                    <div class="d-flex justify-content-between">
                        <strong>${trans.customer}</strong>
                        <span class="text-success fw-bold">$${formatNumber(trans.amount)}</span>
                    </div>
                    <small class="text-muted">${trans.time} - ${trans.items} items</small>
                    <div class="activity-preview">${trans.preview}</div>
                </div>
            </div>
        `;
        $feed.append(feedItem);
    });
}

// Load inventory intelligence
async function loadInventoryIntelligence() {
    try {
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/analytics/inventory-intelligence',
            method: 'GET'
        });

        updateInventoryDashboard(response);

    } catch (error) {
        console.error('Error loading inventory intelligence:', error);
    }
}

// Update inventory dashboard
function updateInventoryDashboard(data) {
    if (!data) return;

    // Create inventory alerts section
    const $container = $('#inventoryAlerts');
    if ($container.length === 0) {
        // Add inventory section if it doesn't exist
        const inventorySection = `
            <div class="row g-3 mb-4">
                <div class="col-12">
                    <div class="card border-0 shadow-sm">
                        <div class="card-header bg-transparent border-0">
                            <h5 class="mb-0 fw-semibold">
                                <i class="fas fa-boxes text-warning me-2"></i>Inventory Intelligence
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-3">
                                    <div class="stat-card">
                                        <h6>Total SKUs</h6>
                                        <h4>${data.summary.total_skus}</h4>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="stat-card">
                                        <h6>Stock Value</h6>
                                        <h4>$${formatNumber(data.summary.total_value)}</h4>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="stat-card">
                                        <h6>Critical Items</h6>
                                        <h4 class="text-danger">${data.summary.critical_items}</h4>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="stat-card">
                                        <h6>Dead Stock</h6>
                                        <h4 class="text-warning">$${formatNumber(data.summary.dead_stock_value)}</h4>
                                    </div>
                                </div>
                            </div>
                            <div id="inventoryAlerts" class="mt-3"></div>
                            <div id="abcAnalysis" class="mt-3"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        $('.main-content .container-fluid').last().append(inventorySection);
    }

    // Update reorder suggestions
    if (data.reorder_suggestions && data.reorder_suggestions.length > 0) {
        const alertsHtml = `
            <h6 class="mb-2">Reorder Alerts</h6>
            <div class="list-group">
                ${data.reorder_suggestions.map(item => `
                    <div class="list-group-item ${item.urgency === 'HIGH' ? 'list-group-item-danger' : 'list-group-item-warning'}">
                        <div class="d-flex justify-content-between">
                            <div>
                                <strong>${item.product}</strong>
                                <span class="ms-2">Stock: ${item.current_stock} units</span>
                            </div>
                            <div>
                                <span class="badge bg-danger">${item.days_remaining.toFixed(1)} days left</span>
                                <button class="btn btn-sm btn-primary ms-2" onclick="createReorder('${item.product}', ${item.suggested_order})">
                                    Order ${item.suggested_order} units
                                </button>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        $('#inventoryAlerts').html(alertsHtml);
    }

    // Update ABC analysis
    if (data.abc_analysis) {
        const abcHtml = `
            <h6 class="mb-2">ABC Analysis</h6>
            <div class="row">
                ${Object.keys(data.abc_analysis).map(category => `
                    <div class="col-md-4">
                        <div class="abc-card">
                            <h5>Category ${category}</h5>
                            <p>${data.abc_analysis[category].count} items</p>
                            <p>Value: $${formatNumber(data.abc_analysis[category].value)}</p>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        $('#abcAnalysis').html(abcHtml);
    }
}

// Load profit optimization
async function loadProfitOptimization() {
    try {
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/analytics/profit-optimization',
            method: 'GET'
        });

        updateProfitDashboard(response);

    } catch (error) {
        console.error('Error loading profit optimization:', error);
    }
}

// Update profit dashboard
function updateProfitDashboard(data) {
    if (!data) return;

    // Add profit optimization section
    const profitSection = `
        <div class="row g-3 mb-4">
            <div class="col-12">
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-transparent border-0">
                        <h5 class="mb-0 fw-semibold">
                            <i class="fas fa-chart-line text-success me-2"></i>Profit Optimization
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-md-4">
                                <h6>Overall Margin</h6>
                                <h3 class="${data.summary.overall_margin > 25 ? 'text-success' : 'text-warning'}">
                                    ${data.summary.overall_margin.toFixed(1)}%
                                </h3>
                            </div>
                            <div class="col-md-4">
                                <h6>Potential Impact</h6>
                                <h3 class="text-primary">$${formatNumber(data.summary.potential_monthly_impact)}/mo</h3>
                            </div>
                            <div class="col-md-4">
                                <h6>Opportunities</h6>
                                <h3>${data.summary.total_opportunities}</h3>
                            </div>
                        </div>
                        <div id="pricingRecommendations"></div>
                    </div>
                </div>
            </div>
        </div>
    `;

    if ($('#profitOptimization').length === 0) {
        $('.main-content .container-fluid').last().append(`<div id="profitOptimization">${profitSection}</div>`);
    }

    // Update pricing recommendations
    if (data.pricing_recommendations && data.pricing_recommendations.length > 0) {
        const recsHtml = `
            <h6 class="mb-2">Pricing Recommendations</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Current</th>
                            <th>Suggested</th>
                            <th>Action</th>
                            <th>Impact/Month</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.pricing_recommendations.map(rec => `
                            <tr>
                                <td>${rec.product}</td>
                                <td>$${rec.current_price.toFixed(2)}</td>
                                <td>$${rec.suggested_price.toFixed(2)}</td>
                                <td>
                                    <span class="badge ${rec.action === 'INCREASE' ? 'bg-success' : rec.action === 'DECREASE' ? 'bg-warning' : 'bg-info'}">
                                        ${rec.action}
                                    </span>
                                </td>
                                <td class="text-success">+$${formatNumber(rec.potential_monthly_impact)}</td>
                                <td>
                                    <button class="btn btn-sm btn-primary" onclick="applyPricing('${rec.product}', ${rec.suggested_price})">
                                        Apply
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        $('#pricingRecommendations').html(recsHtml);
    }
}

// Load CLV analysis
async function loadCLVAnalysis() {
    try {
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/analytics/customer-lifetime-value',
            method: 'GET'
        });

        updateCLVDashboard(response);

    } catch (error) {
        console.error('Error loading CLV analysis:', error);
    }
}

// Update CLV dashboard
function updateCLVDashboard(data) {
    if (!data) return;

    // Add CLV section
    const clvSection = `
        <div class="row g-3 mb-4">
            <div class="col-12">
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-transparent border-0">
                        <h5 class="mb-0 fw-semibold">
                            <i class="fas fa-users text-info me-2"></i>Customer Lifetime Value Analysis
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-md-3">
                                <h6>Avg CLV</h6>
                                <h3>$${formatNumber(data.summary.avg_clv)}</h3>
                            </div>
                            <div class="col-md-3">
                                <h6>At Risk</h6>
                                <h3 class="text-warning">${data.summary.at_risk_customers}</h3>
                                <small>Value: $${formatNumber(data.summary.at_risk_value)}</small>
                            </div>
                            <div class="col-md-3">
                                <h6>Avg Frequency</h6>
                                <h3>${data.summary.avg_purchase_frequency.toFixed(1)}/mo</h3>
                            </div>
                            <div class="col-md-3">
                                <h6>Avg Order</h6>
                                <h3>$${formatNumber(data.summary.avg_order_value)}</h3>
                            </div>
                        </div>
                        <div id="atRiskCustomers"></div>
                    </div>
                </div>
            </div>
        </div>
    `;

    if ($('#clvAnalysis').length === 0) {
        $('.main-content .container-fluid').last().append(`<div id="clvAnalysis">${clvSection}</div>`);
    }

    // Update at-risk customers
    if (data.at_risk_high_value && data.at_risk_high_value.length > 0) {
        const atRiskHtml = `
            <h6 class="mb-2">High-Value At-Risk Customers</h6>
            <div class="list-group">
                ${data.at_risk_high_value.map(customer => `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between">
                            <div>
                                <strong>${customer.CustomerName}</strong>
                                <span class="ms-2">Revenue: $${formatNumber(customer.TotalRevenue)}</span>
                            </div>
                            <div>
                                <span class="badge bg-warning">${customer.DaysSinceLastOrder} days inactive</span>
                                <button class="btn btn-sm btn-success ms-2" onclick="contactCustomer('${customer.CustomerName}')">
                                    Contact
                                </button>
                            </div>
                        </div>
                        <div class="progress mt-2" style="height: 5px;">
                            <div class="progress-bar bg-danger" style="width: ${customer.ChurnProbability * 100}%"></div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        $('#atRiskCustomers').html(atRiskHtml);
    }
}

// Load sales team performance
async function loadSalesTeamPerformance() {
    try {
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/analytics/sales-team-performance',
            method: 'GET'
        });

        updateTeamDashboard(response);

    } catch (error) {
        console.error('Error loading team performance:', error);
    }
}

// Update team dashboard
function updateTeamDashboard(data) {
    if (!data) return;

    // Add team performance section
    const teamSection = `
        <div class="row g-3 mb-4">
            <div class="col-12">
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-transparent border-0">
                        <h5 class="mb-0 fw-semibold">
                            <i class="fas fa-user-tie text-primary me-2"></i>Sales Team Performance
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-md-3">
                                <h6>Top Performer</h6>
                                <h4>${data.summary.top_performer}</h4>
                            </div>
                            <div class="col-md-3">
                                <h6>Team Sales</h6>
                                <h4>$${formatNumber(data.summary.total_sales)}</h4>
                            </div>
                            <div class="col-md-3">
                                <h6>Total Commission</h6>
                                <h4>$${formatNumber(data.summary.total_commission)}</h4>
                            </div>
                            <div class="col-md-3">
                                <h6>Avg Score</h6>
                                <h4>${data.summary.avg_performance_score.toFixed(1)}</h4>
                            </div>
                        </div>
                        <div id="teamLeaderboard"></div>
                    </div>
                </div>
            </div>
        </div>
    `;

    if ($('#teamPerformance').length === 0) {
        $('.main-content .container-fluid').last().append(`<div id="teamPerformance">${teamSection}</div>`);
    }

    // Update leaderboard
    if (data.team_performance && data.team_performance.length > 0) {
        const leaderboardHtml = `
            <h6 class="mb-2">Team Leaderboard</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Name</th>
                            <th>Sales</th>
                            <th>Profit</th>
                            <th>Score</th>
                            <th>Commission</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.team_performance.slice(0, 10).map((member, index) => `
                            <tr class="${index < 3 ? 'table-success' : ''}">
                                <td>
                                    ${index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : index + 1}
                                </td>
                                <td><strong>${member.name}</strong></td>
                                <td>$${formatNumber(member.total_sales)}</td>
                                <td>$${formatNumber(member.gross_profit)}</td>
                                <td>${member.performance_score}</td>
                                <td class="text-success">$${formatNumber(member.commission)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        $('#teamLeaderboard').html(leaderboardHtml);
    }
}

// Check for alerts
async function checkAlerts() {
    try {
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/analytics/automated-alerts',
            method: 'GET'
        });

        displayAlerts(response.alerts);

    } catch (error) {
        console.error('Error checking alerts:', error);
    }
}

// Display alerts
function displayAlerts(alerts) {
    if (!alerts || alerts.length === 0) return;

    const criticalAlerts = alerts.filter(a => a.type === 'CRITICAL');
    const warningAlerts = alerts.filter(a => a.type === 'WARNING');

    // Show notifications for critical alerts
    criticalAlerts.forEach(alert => {
        showNotification(alert.message, 'danger', alert.action);
    });

    // Update alert badge in header
    const totalAlerts = criticalAlerts.length + warningAlerts.length;
    if (totalAlerts > 0) {
        $('#alertBadge').text(totalAlerts).show();
    }
}

// Show notification
function showNotification(message, type = 'info', action = '') {
    const notification = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            <strong>${type === 'danger' ? '⚠️ Critical:' : 'ℹ️ Alert:'}</strong> ${message}
            ${action ? `<br><small>Action: ${action}</small>` : ''}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    $('#alertContainer').append(notification);

    // Auto-dismiss after 10 seconds
    setTimeout(() => {
        $('.alert').first().fadeOut(() => $(this).remove());
    }, 10000);
}

// Update live metrics
function updateLiveMetrics() {
    // This function updates specific metrics without full reload
    $.ajax({
        url: '/dashboard-v2/api/v2/sales/dashboard-summary',
        method: 'GET',
        data: { period: 'today' },
        success: function(response) {
            if (response.kpis) {
                // Update only the numbers, not full reload
                $('#totalRevenue').text(formatCurrency(response.kpis.total_revenue));
                $('#totalTransactions').text(formatNumber(response.kpis.total_transactions));
            }
        }
    });
}

// Action functions
function createReorder(product, quantity) {
    alert(`Creating reorder for ${product}: ${quantity} units`);
    // Here you would integrate with your ordering system
}

function applyPricing(product, newPrice) {
    alert(`Updating price for ${product} to $${newPrice}`);
    // Here you would integrate with your pricing system
}

function contactCustomer(customerName) {
    alert(`Initiating contact with ${customerName}`);
    // Here you would integrate with your CRM/communication system
}

// Cross-sell recommendations
async function loadCrossSellRecommendations() {
    try {
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/analytics/cross-sell-recommendations',
            method: 'GET'
        });

        console.log('Cross-sell recommendations loaded:', response);
        // Store for use when displaying product details
        window.crossSellData = response.cross_sell_recommendations;

    } catch (error) {
        console.error('Error loading cross-sell recommendations:', error);
    }
}

// Load demand forecast
async function loadDemandForecast() {
    try {
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/analytics/demand-forecast',
            method: 'GET'
        });

        updateForecastChart(response);
        displayForecastSummary(response);

    } catch (error) {
        console.error('Error loading demand forecast:', error);
    }
}

// Display forecast summary
function displayForecastSummary(forecastData) {
    if (!forecastData || !forecastData.product_forecasts) return;

    const forecastHtml = `
        <div class="forecast-summary">
            <h6>Top Product Forecasts (Next 7 Days)</h6>
            <div class="list-group">
                ${forecastData.product_forecasts.slice(0, 5).map(product => `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between">
                            <strong>${product.product}</strong>
                            <span>${product.avg_daily_demand.toFixed(1)} units/day</span>
                        </div>
                        <small class="text-muted">Trend: ${product.trend}</small>
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    $('#forecastSummary').html(forecastHtml);
}

// Stop real-time updates
function stopRealTimeUpdates() {
    if (realtimeInterval) {
        clearInterval(realtimeInterval);
        realtimeInterval = null;
    }
    if (alertCheckInterval) {
        clearInterval(alertCheckInterval);
        alertCheckInterval = null;
    }
}