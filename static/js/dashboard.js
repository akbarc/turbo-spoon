/**
 * Georgia Dashboard v9.18 - Modern JavaScript Framework
 * Enhanced frontend with better performance and user experience
 */

class GeorgiaDashboard {
    constructor() {
        this.apiBase = '';
        this.cache = new Map();
        this.cacheTTL = 5 * 60 * 1000; // 5 minutes
        this.requestQueue = [];
        this.maxConcurrentRequests = 3;
        this.activeRequests = 0;
        
        this.init();
    }
    
    init() {
        console.log('🚀 Georgia Dashboard v9.18 - Initializing...');
        
        // Initialize components when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeComponents());
        } else {
            this.initializeComponents();
        }
    }
    
    initializeComponents() {
        console.log('📊 Initializing dashboard components...');
        
        // Load system status first
        this.loadSystemStatus();
        
        // Load dashboard data
        this.loadDashboardData();
        
        // Setup auto-refresh
        this.setupAutoRefresh();
        
        // Setup event listeners
        this.setupEventListeners();
        
        console.log('✅ Dashboard components initialized');
    }
    
    async loadSystemStatus() {
        try {
            const response = await this.makeRequest('/health');
            const data = await response.json();
            
            this.updateSystemStatus(data);
        } catch (error) {
            console.error('❌ Failed to load system status:', error);
            this.updateSystemStatus({ status: 'error', error: error.message });
        }
    }
    
    updateSystemStatus(data) {
        const statusEl = document.getElementById('system-status');
        if (!statusEl) return;
        
        if (data.status === 'healthy') {
            statusEl.innerHTML = `
                <div class="status-indicator status-healthy fade-in">
                    <i class="fas fa-check-circle"></i>
                    <span>System Healthy</span>
                </div>
                <div class="mt-2" style="font-size: 0.875rem; color: var(--gray-500);">
                    <div><strong>Database:</strong> ${data.database?.connected ? 'Connected' : 'Disconnected'}</div>
                    <div><strong>Version:</strong> ${data.application?.version || 'v9.18.0'}</div>
                    <div><strong>Environment:</strong> ${data.application?.environment || 'development'}</div>
                </div>
            `;
        } else {
            statusEl.innerHTML = `
                <div class="status-indicator status-danger fade-in">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>System Issues</span>
                </div>
                <div class="mt-2" style="font-size: 0.875rem; color: var(--gray-500);">
                    ${data.error || 'Unknown error occurred'}
                </div>
            `;
        }
    }
    
    async loadDashboardData() {
        const loadingTasks = [
            this.loadExecutiveSummary(),
            this.loadSalesPerformance(),
            this.loadInventoryHealth(),
            this.loadCustomerIntelligence()
        ];
        
        // Load all data in parallel but with request limiting
        for (const task of loadingTasks) {
            this.queueRequest(task);
        }
    }
    
    async loadExecutiveSummary() {
        try {
            const response = await this.makeRequest('/api/business-overview/executive-summary?filter=today');
            const data = await response.json();
            
            this.updateExecutiveSummary(data);
        } catch (error) {
            console.error('❌ Failed to load executive summary:', error);
            this.showError('executive-summary', 'Failed to load executive summary');
        }
    }
    
    updateExecutiveSummary(data) {
        // Update sales data
        const salesEl = document.getElementById('sales-data');
        if (salesEl && data.sales) {
            salesEl.innerHTML = `
                <div class="metric fade-in">
                    <div class="metric-value">$${this.formatNumber(data.sales.total_revenue || 0)}</div>
                    <div class="metric-label">Total Revenue</div>
                    <div class="metric-change positive mt-1">
                        <i class="fas fa-arrow-up"></i>
                        <span>Today's Performance</span>
                    </div>
                </div>
                <div class="mt-3" style="font-size: 0.875rem; color: var(--gray-500);">
                    <div>${this.formatNumber(data.sales.total_transactions || 0)} transactions</div>
                    <div>${this.formatNumber(data.sales.unique_customers || 0)} customers</div>
                    <div>Avg: $${this.formatNumber(data.sales.avg_transaction_value || 0)}</div>
                </div>
            `;
        }
        
        // Update inventory data
        const inventoryEl = document.getElementById('inventory-data');
        if (inventoryEl && data.inventory) {
            inventoryEl.innerHTML = `
                <div class="metric fade-in">
                    <div class="metric-value">${this.formatNumber(data.inventory.total_items || 0)}</div>
                    <div class="metric-label">Total Items</div>
                    <div class="metric-change neutral mt-1">
                        <i class="fas fa-boxes"></i>
                        <span>Inventory Status</span>
                    </div>
                </div>
                <div class="mt-3" style="font-size: 0.875rem; color: var(--gray-500);">
                    <div>${this.formatNumber(data.inventory.in_stock_items || 0)} in stock</div>
                    <div>${this.formatNumber(data.inventory.out_of_stock_items || 0)} out of stock</div>
                    <div>Value: $${this.formatNumber(data.inventory.total_value || 0)}</div>
                </div>
            `;
        }
        
        // Update AR data
        const arEl = document.getElementById('ar-data');
        if (arEl && data.accounts_receivable) {
            arEl.innerHTML = `
                <div class="metric fade-in">
                    <div class="metric-value">$${this.formatNumber(data.accounts_receivable.total_ar || 0)}</div>
                    <div class="metric-label">Total AR</div>
                    <div class="metric-change ${data.accounts_receivable.total_ar > 0 ? 'warning' : 'positive'} mt-1">
                        <i class="fas fa-file-invoice-dollar"></i>
                        <span>Outstanding</span>
                    </div>
                </div>
                <div class="mt-3" style="font-size: 0.875rem; color: var(--gray-500);">
                    <div>${this.formatNumber(data.accounts_receivable.customers_with_balance || 0)} customers</div>
                    <div>Avg: $${this.formatNumber(data.accounts_receivable.avg_balance || 0)}</div>
                    <div>Max: $${this.formatNumber(data.accounts_receivable.max_balance || 0)}</div>
                </div>
            `;
        }
    }
    
    async loadSalesPerformance() {
        try {
            const response = await this.makeRequest('/api/business-overview/sales-performance?filter=today');
            const data = await response.json();
            
            // Update sales performance section if it exists
            console.log('📊 Sales performance loaded:', data);
        } catch (error) {
            console.error('❌ Failed to load sales performance:', error);
        }
    }
    
    async loadInventoryHealth() {
        try {
            const response = await this.makeRequest('/api/business-overview/inventory-health');
            const data = await response.json();
            
            // Update inventory health section if it exists
            console.log('📦 Inventory health loaded:', data);
        } catch (error) {
            console.error('❌ Failed to load inventory health:', error);
        }
    }
    
    async loadCustomerIntelligence() {
        try {
            const response = await this.makeRequest('/api/business-overview/customer-intelligence?filter=today');
            const data = await response.json();
            
            // Update customer data
            const customerEl = document.getElementById('customer-data');
            if (customerEl && data.active_customers !== undefined) {
                customerEl.innerHTML = `
                    <div class="metric fade-in">
                        <div class="metric-value">${this.formatNumber(data.active_customers || 0)}</div>
                        <div class="metric-label">Active Customers</div>
                        <div class="metric-change positive mt-1">
                            <i class="fas fa-users"></i>
                            <span>Today</span>
                        </div>
                    </div>
                    <div class="mt-3" style="font-size: 0.875rem; color: var(--gray-500);">
                        <div>Last 7 days: ${this.formatNumber(data.customers_last_7_days || 0)}</div>
                        <div>Avg value: $${this.formatNumber(data.avg_customer_value || 0)}</div>
                        <div>High value: ${this.formatNumber(data.high_value_customers || 0)}</div>
                    </div>
                `;
            } else {
                customerEl.innerHTML = `
                    <div class="metric fade-in">
                        <div class="metric-value">Coming Soon</div>
                        <div class="metric-label">Customer Analytics</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('❌ Failed to load customer intelligence:', error);
            this.showError('customer-data', 'Customer data unavailable');
        }
    }
    
    showError(elementId, message) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="status-indicator status-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>${message}</span>
                </div>
            `;
        }
    }
    
    // Request queue management for better performance
    async queueRequest(requestFunction) {
        return new Promise((resolve, reject) => {
            this.requestQueue.push({ requestFunction, resolve, reject });
            this.processQueue();
        });
    }
    
    async processQueue() {
        if (this.activeRequests >= this.maxConcurrentRequests || this.requestQueue.length === 0) {
            return;
        }
        
        const { requestFunction, resolve, reject } = this.requestQueue.shift();
        this.activeRequests++;
        
        try {
            const result = await requestFunction();
            resolve(result);
        } catch (error) {
            reject(error);
        } finally {
            this.activeRequests--;
            // Process next request with a small delay
            setTimeout(() => this.processQueue(), 100);
        }
    }
    
    // Enhanced fetch with caching and error handling
    async makeRequest(url, options = {}) {
        const cacheKey = `${url}_${JSON.stringify(options)}`;
        
        // Check cache first
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTTL) {
                console.log(`📋 Cache hit for ${url}`);
                return cached.response;
            } else {
                this.cache.delete(cacheKey);
            }
        }
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout
        
        try {
            const response = await fetch(this.apiBase + url, {
                ...options,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Cache successful responses
            this.cache.set(cacheKey, {
                response: response.clone(),
                timestamp: Date.now()
            });
            
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    }
    
    setupAutoRefresh() {
        // Refresh every 5 minutes
        setInterval(() => {
            console.log('🔄 Auto-refreshing dashboard data...');
            this.cache.clear(); // Clear cache for fresh data
            this.loadSystemStatus();
            this.loadDashboardData();
        }, 5 * 60 * 1000);
    }
    
    setupEventListeners() {
        // Add smooth scrolling to navigation links
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
        
        // Add click tracking for navigation cards
        document.querySelectorAll('.nav-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const title = card.querySelector('.nav-title')?.textContent;
                console.log(`📊 Navigation: ${title} clicked`);
                
                // Add loading state
                card.style.opacity = '0.7';
                setTimeout(() => {
                    card.style.opacity = '1';
                }, 200);
            });
        });
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'r':
                        e.preventDefault();
                        this.refreshDashboard();
                        break;
                    case 'h':
                        e.preventDefault();
                        window.open('/health', '_blank');
                        break;
                }
            }
        });
    }
    
    refreshDashboard() {
        console.log('🔄 Manual refresh triggered');
        this.cache.clear();
        this.loadSystemStatus();
        this.loadDashboardData();
        
        // Show refresh indicator
        const indicator = document.createElement('div');
        indicator.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> Refreshing...';
        indicator.className = 'status-indicator status-healthy';
        indicator.style.position = 'fixed';
        indicator.style.top = '20px';
        indicator.style.right = '20px';
        indicator.style.zIndex = '1000';
        
        document.body.appendChild(indicator);
        
        setTimeout(() => {
            indicator.remove();
        }, 2000);
    }
    
    // Utility functions
    formatNumber(num) {
        if (typeof num !== 'number') return '0';
        
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        
        return num.toLocaleString();
    }
    
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount || 0);
    }
    
    formatDate(date) {
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    }
}

// Performance monitoring
class PerformanceMonitor {
    constructor() {
        this.metrics = {
            pageLoadTime: 0,
            apiResponseTimes: [],
            errorCount: 0
        };
        
        this.init();
    }
    
    init() {
        // Monitor page load time
        window.addEventListener('load', () => {
            this.metrics.pageLoadTime = performance.now();
            console.log(`⚡ Page loaded in ${this.metrics.pageLoadTime.toFixed(2)}ms`);
        });
        
        // Monitor API response times
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            const startTime = performance.now();
            try {
                const response = await originalFetch(...args);
                const endTime = performance.now();
                const duration = endTime - startTime;
                
                this.metrics.apiResponseTimes.push({
                    url: args[0],
                    duration,
                    timestamp: Date.now()
                });
                
                console.log(`🌐 API ${args[0]}: ${duration.toFixed(2)}ms`);
                return response;
            } catch (error) {
                this.metrics.errorCount++;
                throw error;
            }
        };
    }
    
    getMetrics() {
        return {
            ...this.metrics,
            avgApiResponseTime: this.metrics.apiResponseTimes.length > 0 
                ? this.metrics.apiResponseTimes.reduce((sum, m) => sum + m.duration, 0) / this.metrics.apiResponseTimes.length
                : 0
        };
    }
}

// Initialize dashboard when script loads
const dashboard = new GeorgiaDashboard();
const performanceMonitor = new PerformanceMonitor();

// Make dashboard available globally for debugging
window.GeorgiaDashboard = dashboard;
window.PerformanceMonitor = performanceMonitor;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { GeorgiaDashboard, PerformanceMonitor };
}
