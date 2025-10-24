/**
 * Sales Dashboard Pro - Main JavaScript
 * Core functionality and initialization
 */

// Global Variables
let currentPeriod = 'today';
let autoRefreshInterval = null;
let dashboardData = {};
let charts = {};
let settings = {
    refreshInterval: 30000,
    dataLimit: 20,
    enableAnimations: true,
    enableNotifications: false
};

// Initialize Dashboard
$(document).ready(function() {
    console.log('Initializing Sales Dashboard Pro...');

    // Initialize components
    initializeClock();
    initializeDatePicker();
    initializeEventHandlers();
    initializeCharts();

    // Load initial data
    loadDashboardData();

    // Start real-time updates
    startRealTimeUpdates();

    // Load saved settings
    loadSettings();
});

// Initialize live clock
function initializeClock() {
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        $('#liveClock').text(timeString);
    }

    updateClock();
    setInterval(updateClock, 1000);
}

// Initialize date picker
function initializeDatePicker() {
    flatpickr("#dateRange", {
        mode: "range",
        dateFormat: "Y-m-d",
        defaultDate: [
            moment().subtract(7, 'days').format('YYYY-MM-DD'),
            moment().format('YYYY-MM-DD')
        ],
        onChange: function(selectedDates, dateStr, instance) {
            if (selectedDates.length === 2) {
                loadDashboardData();
            }
        }
    });
}

// Initialize event handlers
function initializeEventHandlers() {
    // Period selector
    $('input[name="period"]').on('change', function() {
        currentPeriod = $(this).val();

        // Show/hide custom date range
        if (currentPeriod === 'custom') {
            $('.custom-date-range').slideDown();
        } else {
            $('.custom-date-range').slideUp();
            loadDashboardData();
        }
    });

    // Category filter
    $('#categoryFilter').on('change', function() {
        loadDashboardData();
    });

    // Auto refresh toggle
    $('#autoRefresh').on('change', function() {
        if ($(this).is(':checked')) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });

    // View mode toggle
    $('[data-view]').on('click', function() {
        const view = $(this).data('view');
        $('[data-view]').removeClass('active');
        $(this).addClass('active');
        switchViewMode(view);
    });

    // Chart view toggles
    $('[data-chart]').on('click', function() {
        const chartType = $(this).data('chart');
        $('[data-chart]').removeClass('active');
        $(this).addClass('active');
        updateSalesTrendChart(chartType);
    });
}

// Load dashboard data
async function loadDashboardData() {
    try {
        showLoadingState();

        // Get date range
        const dateRange = getDateRange();

        // Fetch dashboard summary
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/sales/dashboard-summary',
            method: 'GET',
            data: {
                period: currentPeriod,
                ...dateRange
            }
        });

        dashboardData = response;

        // Update UI components
        updateKPIs(response.kpis);
        updateTrends(response.trends);
        updateComparisons(response.comparisons);

        // Load additional components in parallel
        await Promise.all([
            loadProductPerformance(),
            loadCustomerSegments(),
            loadSalesForecast(),
            loadHourlyAnalysis()
        ]);

        // Generate insights
        generateInsights();

        hideLoadingState();
        showSuccessMessage('Dashboard updated successfully');

    } catch (error) {
        console.error('Error loading dashboard:', error);
        hideLoadingState();
        showErrorMessage('Failed to load dashboard data');
    }
}

// Update KPI cards
function updateKPIs(kpis) {
    if (!kpis) return;

    // Animate number changes
    animateNumber('#totalRevenue', kpis.total_revenue || 0, true);
    animateNumber('#totalTransactions', kpis.total_transactions || 0, false);
    animateNumber('#uniqueCustomers', kpis.unique_customers || 0, false);
    animateNumber('#avgOrderValue', kpis.avg_order_value || 0, true);
    animateNumber('#grossProfit', kpis.gross_profit || 0, true);
    animateNumber('#profitMargin', kpis.profit_margin || 0, false, '%');

    // Update profit progress bar
    const profitProgress = Math.min(kpis.profit_margin || 0, 100);
    $('#profitProgress').css('width', profitProgress + '%');
}

// Update trend indicators
function updateTrends(trends) {
    if (!trends) return;

    // Update sparklines
    updateSparklines(trends);
}

// Update comparisons
function updateComparisons(comparisons) {
    if (!comparisons) return;

    // Revenue trend
    updateTrendBadge('#revenueTrend', comparisons.revenue_change);

    // Customer trend
    updateTrendBadge('#customerTrend', comparisons.customer_change);
}

// Update trend badge
function updateTrendBadge(selector, change) {
    const $badge = $(selector);
    const isPositive = change >= 0;

    $badge.removeClass('bg-success bg-danger')
          .addClass(isPositive ? 'bg-success' : 'bg-danger');

    $badge.find('i').removeClass('fa-arrow-up fa-arrow-down')
          .addClass(isPositive ? 'fa-arrow-up' : 'fa-arrow-down');

    $badge.find('span').text(Math.abs(change).toFixed(1) + '%');
}

// Load product performance
async function loadProductPerformance() {
    try {
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/sales/product-performance',
            method: 'GET',
            data: {
                period: currentPeriod,
                limit: settings.dataLimit
            }
        });

        updateProductsTable(response.products);

    } catch (error) {
        console.error('Error loading product performance:', error);
    }
}

// Update products table
function updateProductsTable(products) {
    const $tbody = $('#topProductsTable tbody');
    $tbody.empty();

    if (!products || products.length === 0) {
        $tbody.append('<tr><td colspan="6" class="text-center text-muted">No data available</td></tr>');
        return;
    }

    products.forEach((product, index) => {
        const trendIcon = product.velocity > 1 ? 'fa-arrow-up text-success' : 'fa-arrow-down text-danger';
        const marginClass = product.margin > 30 ? 'text-success' : product.margin < 15 ? 'text-danger' : 'text-warning';

        const row = `
            <tr class="fade-in" style="animation-delay: ${index * 0.05}s">
                <td><span class="badge bg-primary">${index + 1}</span></td>
                <td>
                    <div class="fw-semibold">${product.name}</div>
                    <small class="text-muted">${product.category}</small>
                </td>
                <td class="text-end fw-bold">$${formatNumber(product.revenue)}</td>
                <td class="text-end">${formatNumber(product.units_sold)}</td>
                <td class="text-end ${marginClass}">${product.margin.toFixed(1)}%</td>
                <td class="text-center">
                    <i class="fas ${trendIcon}"></i>
                </td>
            </tr>
        `;
        $tbody.append(row);
    });
}

// Load customer segments
async function loadCustomerSegments() {
    try {
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/sales/customer-segments',
            method: 'GET',
            data: {
                period: currentPeriod
            }
        });

        updateCustomerSegmentsChart(response.segments);

    } catch (error) {
        console.error('Error loading customer segments:', error);
    }
}

// Load sales forecast
async function loadSalesForecast() {
    try {
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/sales/sales-forecast',
            method: 'GET'
        });

        updateForecastChart(response);

    } catch (error) {
        console.error('Error loading forecast:', error);
    }
}

// Load hourly analysis
async function loadHourlyAnalysis() {
    try {
        const response = await $.ajax({
            url: '/dashboard-v2/api/v2/sales/hourly-analysis',
            method: 'GET',
            data: {
                days: 7
            }
        });

        updateHeatmap(response.heatmap);

    } catch (error) {
        console.error('Error loading hourly analysis:', error);
    }
}

// Generate insights
function generateInsights() {
    const insights = [];
    const kpis = dashboardData.kpis;
    const comparisons = dashboardData.comparisons;

    if (kpis) {
        // Revenue insight
        if (comparisons && comparisons.revenue_change > 10) {
            insights.push({
                type: 'success',
                icon: 'fa-chart-line',
                text: `Revenue is up ${comparisons.revenue_change.toFixed(1)}% compared to previous period`
            });
        } else if (comparisons && comparisons.revenue_change < -10) {
            insights.push({
                type: 'warning',
                icon: 'fa-exclamation-triangle',
                text: `Revenue is down ${Math.abs(comparisons.revenue_change).toFixed(1)}% - investigate causes`
            });
        }

        // Profit margin insight
        if (kpis.profit_margin < 20) {
            insights.push({
                type: 'warning',
                icon: 'fa-percentage',
                text: `Profit margin is below 20% - consider pricing optimization`
            });
        }

        // Customer insight
        if (comparisons && comparisons.customer_change < 0) {
            insights.push({
                type: 'info',
                icon: 'fa-users',
                text: `Customer count decreased - focus on retention strategies`
            });
        }

        // AOV insight
        if (kpis.avg_order_value > 100) {
            insights.push({
                type: 'success',
                icon: 'fa-dollar-sign',
                text: `Average order value is strong at $${kpis.avg_order_value.toFixed(2)}`
            });
        }
    }

    displayInsights(insights);
}

// Display insights
function displayInsights(insights) {
    const $container = $('#insightsList');
    $container.empty();

    if (insights.length === 0) {
        $container.append('<p class="text-muted">No insights available</p>');
        return;
    }

    insights.forEach((insight, index) => {
        const alertClass = insight.type === 'success' ? 'alert-success' :
                          insight.type === 'warning' ? 'alert-warning' : 'alert-info';

        const html = `
            <div class="alert ${alertClass} alert-sm fade-in" style="animation-delay: ${index * 0.1}s">
                <i class="fas ${insight.icon} me-2"></i>
                ${insight.text}
            </div>
        `;
        $container.append(html);
    });
}

// Helper Functions

// Get date range based on current selection
function getDateRange() {
    if (currentPeriod === 'custom') {
        const dates = $('#dateRange').val().split(' to ');
        return {
            start_date: dates[0],
            end_date: dates[1] || dates[0]
        };
    }
    return {};
}

// Animate number changes
function animateNumber(selector, value, isCurrency = false, suffix = '') {
    const $element = $(selector);
    const currentValue = parseFloat($element.text().replace(/[^0-9.-]/g, '')) || 0;

    if (!settings.enableAnimations) {
        $element.text(isCurrency ? formatCurrency(value) : formatNumber(value) + suffix);
        return;
    }

    $({ value: currentValue }).animate({ value: value }, {
        duration: 1000,
        easing: 'swing',
        step: function(now) {
            if (isCurrency) {
                $element.text(formatCurrency(now));
            } else {
                $element.text(formatNumber(now) + suffix);
            }
        }
    });
}

// Format number
function formatNumber(value) {
    return new Intl.NumberFormat('en-US').format(Math.round(value));
}

// Format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(Math.round(value));
}

// Show loading state
function showLoadingState() {
    $('.kpi-card').addClass('loading');
    $('.card-body').css('opacity', '0.6');
}

// Hide loading state
function hideLoadingState() {
    $('.kpi-card').removeClass('loading');
    $('.card-body').css('opacity', '1');
}

// Show success message
function showSuccessMessage(message) {
    if (!settings.enableNotifications) return;

    const alert = `
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <i class="fas fa-check-circle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    $('#alertContainer').append(alert);

    setTimeout(() => {
        $('.alert').fadeOut(() => $(this).remove());
    }, 3000);
}

// Show error message
function showErrorMessage(message) {
    const alert = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    $('#alertContainer').append(alert);
}

// Auto refresh functions
function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshInterval = setInterval(loadDashboardData, settings.refreshInterval);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Settings functions
function loadSettings() {
    const saved = localStorage.getItem('dashboardSettings');
    if (saved) {
        settings = JSON.parse(saved);
        applySettings();
    }
}

function saveSettings() {
    settings.refreshInterval = parseInt($('#refreshInterval').val()) * 1000;
    settings.dataLimit = parseInt($('#dataLimit').val());
    settings.enableAnimations = $('#enableAnimations').is(':checked');
    settings.enableNotifications = $('#enableNotifications').is(':checked');

    localStorage.setItem('dashboardSettings', JSON.stringify(settings));
    applySettings();

    $('#settingsModal').modal('hide');
    showSuccessMessage('Settings saved successfully');
}

function applySettings() {
    $('#refreshInterval').val(settings.refreshInterval / 1000);
    $('#dataLimit').val(settings.dataLimit);
    $('#enableAnimations').prop('checked', settings.enableAnimations);
    $('#enableNotifications').prop('checked', settings.enableNotifications);

    if ($('#autoRefresh').is(':checked')) {
        startAutoRefresh();
    }
}

// Export functions
function exportDashboard() {
    window.location.href = `/api/v2/sales/export?period=${currentPeriod}&format=pdf`;
}

function exportProducts() {
    window.location.href = `/api/v2/sales/export-products?period=${currentPeriod}&format=excel`;
}

function refreshDashboard() {
    loadDashboardData();
}

// View mode switch
function switchViewMode(mode) {
    if (mode === 'list') {
        $('.kpi-card').parent().removeClass('col-xl-3').addClass('col-12');
    } else {
        $('.kpi-card').parent().removeClass('col-12').addClass('col-xl-3');
    }
}