/**
 * Sales Dashboard Pro - Charts Module
 * All chart visualizations and updates
 */

// Chart instances storage
let chartInstances = {
    salesTrend: null,
    heatmap: null,
    categoryDonut: null,
    forecast: null,
    customerSegments: null,
    sparklines: {}
};

// Initialize all charts
function initializeCharts() {
    initializeSalesTrendChart();
    initializeHeatmapChart();
    initializeCategoryChart();
    initializeForecastChart();
    initializeCustomerSegmentsChart();
    initializeSparklines();
}

// Sales Trend Chart with Forecast
function initializeSalesTrendChart() {
    const options = {
        series: [],
        chart: {
            type: 'area',
            height: 350,
            animations: {
                enabled: true,
                easing: 'easeinout',
                speed: 800
            },
            toolbar: {
                show: true,
                tools: {
                    download: true,
                    selection: true,
                    zoom: true,
                    zoomin: true,
                    zoomout: true,
                    pan: true,
                    reset: true
                }
            }
        },
        dataLabels: {
            enabled: false
        },
        stroke: {
            curve: 'smooth',
            width: [3, 2]
        },
        fill: {
            type: 'gradient',
            gradient: {
                shadeIntensity: 1,
                inverseColors: false,
                opacityFrom: 0.5,
                opacityTo: 0,
                stops: [0, 90, 100]
            }
        },
        xaxis: {
            type: 'datetime',
            categories: []
        },
        yaxis: {
            title: {
                text: 'Sales ($)'
            },
            labels: {
                formatter: function(value) {
                    return '$' + formatNumber(value);
                }
            }
        },
        tooltip: {
            shared: true,
            y: {
                formatter: function(value) {
                    return '$' + formatNumber(value);
                }
            }
        },
        colors: ['#008FFB', '#00E396']
    };

    chartInstances.salesTrend = new ApexCharts(document.querySelector("#salesTrendChart"), options);
    chartInstances.salesTrend.render();
}

// Update Sales Trend Chart
function updateSalesTrendChart(chartType) {
    if (!dashboardData.trends) return;

    let data, categories;

    if (chartType === 'hourly' && dashboardData.trends.hourly) {
        data = dashboardData.trends.hourly;
        categories = data.map(d => {
            const hour = d.hour;
            return `${hour}:00`;
        });

        chartInstances.salesTrend.updateOptions({
            xaxis: {
                type: 'category',
                categories: categories
            }
        });

        chartInstances.salesTrend.updateSeries([{
            name: 'Sales',
            data: data.map(d => d.sales)
        }]);
    } else if (dashboardData.trends.daily) {
        data = dashboardData.trends.daily;
        categories = data.map(d => d.date);

        chartInstances.salesTrend.updateOptions({
            xaxis: {
                type: 'datetime',
                categories: categories
            }
        });

        chartInstances.salesTrend.updateSeries([{
            name: 'Actual Sales',
            data: data.map(d => d.sales)
        }]);
    }
}

// Sales Heatmap
function initializeHeatmapChart() {
    const options = {
        series: [],
        chart: {
            height: 350,
            type: 'heatmap',
        },
        dataLabels: {
            enabled: false
        },
        colors: ["#008FFB"],
        xaxis: {
            type: 'category',
            categories: ['12am', '1am', '2am', '3am', '4am', '5am', '6am', '7am',
                        '8am', '9am', '10am', '11am', '12pm', '1pm', '2pm', '3pm',
                        '4pm', '5pm', '6pm', '7pm', '8pm', '9pm', '10pm', '11pm']
        },
        tooltip: {
            y: {
                formatter: function(value) {
                    return '$' + formatNumber(value);
                }
            }
        }
    };

    chartInstances.heatmap = new ApexCharts(document.querySelector("#salesHeatmap"), options);
    chartInstances.heatmap.render();
}

// Update Heatmap
function updateHeatmap(heatmapData) {
    if (!heatmapData || !chartInstances.heatmap) return;

    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const series = [];

    days.forEach((day, dayIndex) => {
        const dayData = heatmapData.filter(d => d.day === day);
        const hourlyData = [];

        for (let hour = 0; hour < 24; hour++) {
            const hourData = dayData.find(d => d.hour === hour);
            hourlyData.push(hourData ? hourData.sales : 0);
        }

        series.push({
            name: day,
            data: hourlyData
        });
    });

    chartInstances.heatmap.updateSeries(series);
}

// Category Donut Chart
function initializeCategoryChart() {
    const options = {
        series: [],
        chart: {
            type: 'donut',
            height: 300
        },
        labels: [],
        colors: ['#008FFB', '#00E396', '#FEB019', '#FF4560', '#775DD0', '#3F51B5'],
        legend: {
            show: false // We'll create custom legend
        },
        dataLabels: {
            enabled: true,
            formatter: function(val, opts) {
                return opts.w.config.labels[opts.seriesIndex] + ': ' + val.toFixed(1) + '%';
            }
        },
        tooltip: {
            y: {
                formatter: function(value) {
                    return '$' + formatNumber(value);
                }
            }
        }
    };

    chartInstances.categoryDonut = new ApexCharts(document.querySelector("#categoryDonut"), options);
    chartInstances.categoryDonut.render();
}

// Update Category Chart
function updateCategoryChart(categories) {
    if (!categories || categories.length === 0 || !chartInstances.categoryDonut) return;

    const labels = categories.map(c => c.category_name || 'Unknown');
    const values = categories.map(c => c.revenue || 0);

    chartInstances.categoryDonut.updateOptions({
        labels: labels
    });

    chartInstances.categoryDonut.updateSeries(values);

    // Update custom legend
    const legendContainer = $('#categoryLegend');
    legendContainer.empty();

    categories.forEach((cat, index) => {
        const color = ['#008FFB', '#00E396', '#FEB019', '#FF4560', '#775DD0', '#3F51B5'][index % 6];
        const percent = ((cat.revenue / categories.reduce((a, b) => a + b.revenue, 0)) * 100).toFixed(1);

        const legendItem = `
            <div class="legend-item mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <span class="legend-color" style="background-color: ${color}"></span>
                        <span class="fw-semibold">${cat.category_name}</span>
                    </div>
                    <div class="text-end">
                        <div class="fw-bold">$${formatNumber(cat.revenue)}</div>
                        <small class="text-muted">${percent}%</small>
                    </div>
                </div>
            </div>
        `;
        legendContainer.append(legendItem);
    });
}

// Forecast Chart
function initializeForecastChart() {
    const options = {
        series: [],
        chart: {
            type: 'line',
            height: 300,
            toolbar: {
                show: false
            }
        },
        stroke: {
            width: [3, 2, 2],
            curve: 'smooth',
            dashArray: [0, 5, 5]
        },
        xaxis: {
            type: 'datetime'
        },
        yaxis: {
            title: {
                text: 'Sales ($)'
            },
            labels: {
                formatter: function(value) {
                    return '$' + formatNumber(value);
                }
            }
        },
        tooltip: {
            shared: true
        },
        colors: ['#008FFB', '#00E396', '#FEB019'],
        fill: {
            type: 'solid',
            opacity: [1, 0.3, 0.3]
        }
    };

    chartInstances.forecast = new ApexCharts(document.querySelector("#forecastChart"), options);
    chartInstances.forecast.render();
}

// Update Forecast Chart
function updateForecastChart(forecastData) {
    if (!forecastData || !chartInstances.forecast) return;

    const series = [];

    // Historical data
    if (forecastData.historical && forecastData.historical.length > 0) {
        series.push({
            name: 'Actual',
            data: forecastData.historical.map(d => ({
                x: new Date(d.date).getTime(),
                y: d.actual_sales
            }))
        });
    }

    // Forecast data
    if (forecastData.forecast && forecastData.forecast.length > 0) {
        series.push({
            name: 'Predicted',
            data: forecastData.forecast.map(d => ({
                x: new Date(d.date).getTime(),
                y: d.predicted_sales
            }))
        });

        // Confidence intervals
        series.push({
            name: 'Upper Bound',
            data: forecastData.forecast.map(d => ({
                x: new Date(d.date).getTime(),
                y: d.confidence_upper
            }))
        });

        series.push({
            name: 'Lower Bound',
            data: forecastData.forecast.map(d => ({
                x: new Date(d.date).getTime(),
                y: d.confidence_lower
            }))
        });
    }

    chartInstances.forecast.updateSeries(series);
}

// Customer Segments Chart
function initializeCustomerSegmentsChart() {
    const options = {
        series: [],
        chart: {
            type: 'bar',
            height: 300,
            stacked: false
        },
        plotOptions: {
            bar: {
                horizontal: false,
                columnWidth: '55%',
                endingShape: 'rounded'
            }
        },
        dataLabels: {
            enabled: false
        },
        xaxis: {
            categories: []
        },
        yaxis: [{
            title: {
                text: 'Customer Count'
            }
        }, {
            opposite: true,
            title: {
                text: 'Revenue ($)'
            },
            labels: {
                formatter: function(value) {
                    return '$' + formatNumber(value);
                }
            }
        }],
        tooltip: {
            shared: true,
            intersect: false
        },
        colors: ['#008FFB', '#00E396']
    };

    chartInstances.customerSegments = new ApexCharts(document.querySelector("#customerSegmentsChart"), options);
    chartInstances.customerSegments.render();
}

// Update Customer Segments
function updateCustomerSegmentsChart(segments) {
    if (!segments || segments.length === 0 || !chartInstances.customerSegments) return;

    const categories = segments.map(s => s.segment);
    const customerCounts = segments.map(s => s.customer_count);
    const revenues = segments.map(s => s.total_revenue);

    chartInstances.customerSegments.updateOptions({
        xaxis: {
            categories: categories
        }
    });

    chartInstances.customerSegments.updateSeries([{
        name: 'Customers',
        type: 'column',
        data: customerCounts
    }, {
        name: 'Revenue',
        type: 'line',
        data: revenues
    }]);
}

// Initialize Sparklines
function initializeSparklines() {
    // Revenue sparkline
    const revenueSparklineOptions = {
        series: [{
            data: []
        }],
        chart: {
            type: 'line',
            height: 40,
            sparkline: {
                enabled: true
            }
        },
        stroke: {
            curve: 'smooth',
            width: 2
        },
        colors: ['#00E396']
    };

    chartInstances.sparklines.revenue = new ApexCharts(
        document.querySelector("#revenueSparkline"),
        revenueSparklineOptions
    );
    chartInstances.sparklines.revenue.render();

    // Transactions sparkline
    const transactionsSparklineOptions = {
        ...revenueSparklineOptions,
        colors: ['#008FFB']
    };

    chartInstances.sparklines.transactions = new ApexCharts(
        document.querySelector("#transactionsSparkline"),
        transactionsSparklineOptions
    );
    chartInstances.sparklines.transactions.render();

    // Customers sparkline
    const customersSparklineOptions = {
        ...revenueSparklineOptions,
        colors: ['#FEB019']
    };

    chartInstances.sparklines.customers = new ApexCharts(
        document.querySelector("#customersSparkline"),
        customersSparklineOptions
    );
    chartInstances.sparklines.customers.render();
}

// Update Sparklines
function updateSparklines(trends) {
    if (!trends || !trends.daily) return;

    const recentData = trends.daily.slice(-7);

    if (chartInstances.sparklines.revenue) {
        chartInstances.sparklines.revenue.updateSeries([{
            data: recentData.map(d => d.sales)
        }]);
    }

    if (chartInstances.sparklines.transactions) {
        chartInstances.sparklines.transactions.updateSeries([{
            data: recentData.map(d => d.transactions)
        }]);
    }

    // For customers, we'll use transactions as a proxy
    if (chartInstances.sparklines.customers) {
        chartInstances.sparklines.customers.updateSeries([{
            data: recentData.map(d => Math.round(d.transactions * 0.7))
        }]);
    }
}