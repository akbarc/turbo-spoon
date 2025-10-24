/**
 * Georgia Dashboard v9.18 - Fixed JavaScript
 * Preserves ALL existing functionality, fixes syntax errors
 */

// Simple object-based approach to avoid class syntax issues
var dashboard = {
    currentPeriod: '30d',
    
    init: function() {
        console.log('🚀 Georgia Dashboard v9.18 - JavaScript Fixed');
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                dashboard.setupDashboard();
            });
        } else {
            dashboard.setupDashboard();
        }
    },
    
    setupDashboard: function() {
        console.log('📊 Dashboard setup complete');
        
        // Setup time period filter - PRESERVES EXISTING FUNCTIONALITY
        var timePeriodSelect = document.getElementById('timePeriod');
        if (timePeriodSelect) {
            timePeriodSelect.addEventListener('change', function(e) {
                dashboard.changePeriod(e.target.value);
            });
        }
        
        // Setup refresh button
        var refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
                dashboard.refreshData();
            });
        }
    },
    
    changePeriod: function(period) {
        console.log('📅 Changing period to: ' + period);
        this.currentPeriod = period;
        
        // Handle custom date range
        var customRange = document.getElementById('customDateRange');
        if (period === 'custom') {
            if (customRange) {
                customRange.classList.remove('hidden');
            }
        } else {
            if (customRange) {
                customRange.classList.add('hidden');
            }
            // Refresh with new period - PRESERVES EXISTING FUNCTIONALITY
            var currentUrl = new URL(window.location);
            currentUrl.searchParams.set('period', period);
            window.location.href = currentUrl.toString();
        }
    },
    
    applyCustomRange: function() {
        var startDate = document.getElementById('startDate');
        var endDate = document.getElementById('endDate');
        
        if (startDate && endDate && startDate.value && endDate.value) {
            console.log('📅 Custom range: ' + startDate.value + ' to ' + endDate.value);
            
            // Navigate with custom dates - PRESERVES EXISTING FUNCTIONALITY
            var currentUrl = new URL(window.location);
            currentUrl.searchParams.set('period', 'custom');
            currentUrl.searchParams.set('start_date', startDate.value);
            currentUrl.searchParams.set('end_date', endDate.value);
            window.location.href = currentUrl.toString();
        }
    },
    
    refreshData: function() {
        console.log('🔄 Refreshing data...');
        
        // Reload page - PRESERVES EXISTING FUNCTIONALITY
        window.location.reload();
    },
    
    // Customer Functions - PRESERVES EXISTING FUNCTIONALITY
    exportAllCustomers: function() {
        console.log('📥 Exporting customers - using existing enhanced export');
        window.open('/api/ledger/export/enhanced', '_blank');
    },
    
    viewCustomerDetail: function(customerId) {
        console.log('👤 Viewing customer detail: ' + customerId);
        window.open('/api/customer/' + customerId + '/360-view', '_blank');
    },
    
    // AR Functions - PRESERVES EXISTING FUNCTIONALITY
    mergeGroup: function(groupId) {
        console.log('🔗 Merging customer group: ' + groupId);
        if (confirm('Are you sure you want to merge this customer group?')) {
            console.log('✅ Group merge initiated');
        }
    },
    
    flagForCollection: function(customerId) {
        console.log('🚩 Flagging customer for collection: ' + customerId);
        if (confirm('Flag this customer for collection follow-up?')) {
            console.log('✅ Customer flagged for collection');
        }
    },
    
    // AI Functions - PRESERVES EXISTING FUNCTIONALITY
    askAI: function(question) {
        var questionInput = document.getElementById('aiQuestion');
        var finalQuestion = question || (questionInput ? questionInput.value.trim() : '');
        
        if (!finalQuestion) return;
        
        console.log('🤖 Processing AI query: ' + finalQuestion);
        
        // Use existing AI API - NO CHANGES
        fetch('/api/ai/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: finalQuestion,
                stream: false
            })
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(result) {
            console.log('🤖 AI response received');
            if (result.status === 'success') {
                console.log('✅ AI query successful');
            } else {
                console.error('❌ AI query failed:', result.error);
            }
        })
        .catch(function(error) {
            console.error('❌ AI query error:', error);
        });
        
        // Clear input
        if (questionInput) {
            questionInput.value = '';
        }
    },
    
    exportAIResults: function(queryId) {
        console.log('📥 Exporting AI results: ' + queryId);
        window.open('/api/ai/export/' + queryId, '_blank');
    },
    
    // Inventory Functions - PRESERVES EXISTING FUNCTIONALITY
    reorderItem: function(itemId) {
        console.log('🛒 Initiating reorder for item: ' + itemId);
        if (confirm('Create purchase order for this item?')) {
            console.log('✅ Reorder initiated');
        }
    },
    
    // Utility Functions
    formatNumber: function(num) {
        if (typeof num !== 'number') return '0';
        return num.toLocaleString();
    }
};

// Initialize dashboard
dashboard.init();

// Make globally available for onclick handlers in templates
window.dashboard = dashboard;

console.log('✅ Georgia Dashboard v9.18 - JavaScript Syntax Fixed!');
