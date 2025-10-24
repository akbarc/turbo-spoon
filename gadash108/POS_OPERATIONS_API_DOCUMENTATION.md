# POS Operations Dashboard API Documentation

## Overview

The POS Operations Dashboard API provides real-time operational insights by aggregating data from the existing 18 working POS reports. This API is designed for high performance with built-in caching mechanisms and focuses on providing actionable metrics for day-to-day business operations.

**Base URL:** `/api/pos`

**Key Features:**
- Built-in response caching with configurable TTL
- Aggregates data from existing proven reports
- Real-time operational alerts
- Performance optimizations for frequently accessed metrics
- Comprehensive error handling

---

## Endpoints

### 1. Operations Summary
**GET** `/api/pos/operations-summary`

High-level operations overview with key metrics for a specific date.

**Query Parameters:**
- `date` (optional): Target date in YYYY-MM-DD format. Default: today
- `compare` (optional): Include comparison to previous period. Values: `true`/`false`. Default: `true`

**Response:**
```json
{
  "date": "2025-10-06",
  "metrics": {
    "transaction_count": 157,
    "total_sales": 23450.75,
    "total_tax": 1876.06,
    "avg_transaction": 149.37,
    "unique_customers": 89,
    "active_cashiers": 4,
    "total_units": 2341
  },
  "comparison": {
    "previous_date": "2025-10-05",
    "sales_change": {
      "amount": 1234.50,
      "percent": 5.56
    },
    "transaction_change": {
      "count": 12,
      "percent": 8.27
    },
    "avg_transaction_change": {
      "amount": -2.15,
      "percent": -1.42
    }
  },
  "payment_methods": [
    {
      "method": "Cash",
      "count": 89,
      "total_amount": 12340.00
    },
    {
      "method": "Credit Card",
      "count": 68,
      "total_amount": 11110.75
    }
  ],
  "top_category": {
    "name": "CIGARETTES",
    "revenue": 15678.90
  },
  "_cache": {
    "hit": false,
    "age_seconds": 0,
    "ttl_seconds": 300
  }
}
```

**Cache TTL:** 5 minutes (300 seconds)

**Use Cases:**
- Dashboard overview widget
- Daily operations monitoring
- Quick status check

---

### 2. Daily Metrics
**GET** `/api/pos/daily-metrics`

Daily performance metrics with trends over a specified period.

**Query Parameters:**
- `days` (optional): Number of days to include. Range: 1-90. Default: 7
- `end_date` (optional): End date in YYYY-MM-DD format. Default: today

**Response:**
```json
{
  "period": {
    "start_date": "2025-09-30",
    "end_date": "2025-10-06",
    "days": 7
  },
  "daily_data": [
    {
      "date": "2025-10-06",
      "transaction_count": 157,
      "total_sales": 23450.75,
      "total_tax": 1876.06,
      "avg_transaction": 149.37,
      "unique_customers": 89,
      "total_units": 2341,
      "active_cashiers": 4
    }
    // ... more days
  ],
  "aggregates": {
    "total_sales": 164155.25,
    "total_transactions": 1098,
    "avg_daily_sales": 23450.75,
    "avg_daily_transactions": 157,
    "max_daily_sales": 26789.50,
    "min_daily_sales": 19234.00
  },
  "_cache": {
    "hit": false,
    "age_seconds": 0,
    "ttl_seconds": 180
  }
}
```

**Cache TTL:** 3 minutes (180 seconds)

**Use Cases:**
- Weekly performance trends
- Period-over-period analysis
- Sales forecasting data

---

### 3. Top Performers
**GET** `/api/pos/top-performers`

Top performing items, categories, and cashiers for a date range.

**Query Parameters:**
- `start_date` (optional): Start date in YYYY-MM-DD format. Default: 30 days ago
- `end_date` (optional): End date in YYYY-MM-DD format. Default: today
- `limit` (optional): Number of top performers per category. Range: 1-50. Default: 10

**Response:**
```json
{
  "period": {
    "start_date": "2025-09-06",
    "end_date": "2025-10-06"
  },
  "top_items": [
    {
      "item_name": "Marlboro Red Box",
      "item_code": "MAR001",
      "category": "CIGARETTES",
      "total_quantity": 2340.0,
      "total_revenue": 18720.00,
      "total_cost": 14976.00,
      "gross_profit": 3744.00,
      "transaction_count": 567
    }
    // ... more items
  ],
  "top_categories": [
    {
      "category": "CIGARETTES",
      "transaction_count": 1234,
      "total_quantity": 15678.0,
      "total_revenue": 125424.00,
      "total_cost": 100339.20,
      "gross_profit": 25084.80,
      "unique_items": 45
    }
    // ... more categories
  ],
  "top_cashiers": [
    {
      "cashier_name": "John Smith",
      "cashier_id": 5,
      "transaction_count": 456,
      "total_sales": 68934.50,
      "avg_transaction": 151.15,
      "first_transaction": "2025-10-06T08:15:00",
      "last_transaction": "2025-10-06T17:45:00"
    }
    // ... more cashiers
  ],
  "_cache": {
    "hit": false,
    "age_seconds": 0,
    "ttl_seconds": 600
  }
}
```

**Cache TTL:** 10 minutes (600 seconds)

**Use Cases:**
- Performance leaderboards
- Inventory planning insights
- Employee performance tracking
- Category mix analysis

---

### 4. Operational Alerts
**GET** `/api/pos/alerts`

Operational alerts and anomalies detected in the system.

**Query Parameters:**
- `date` (optional): Target date in YYYY-MM-DD format. Default: today
- `threshold_multiplier` (optional): Anomaly detection threshold multiplier. Default: 1.5

**Response:**
```json
{
  "date": "2025-10-06",
  "alert_count": 5,
  "alerts": [
    {
      "type": "low_inventory",
      "severity": "warning",
      "message": "Low inventory: Marlboro Red Box (15 units, reorder at 50)",
      "details": {
        "item_name": "Marlboro Red Box",
        "item_code": "MAR001",
        "current_quantity": 15.0,
        "reorder_point": 50.0,
        "category": "CIGARETTES"
      }
    },
    {
      "type": "high_transaction",
      "severity": "info",
      "message": "Unusually high transaction: $1234.56 (avg: $149.37)",
      "details": {
        "transaction_number": 98765,
        "time": "2025-10-06T14:30:00",
        "total": 1234.56,
        "customer_name": "ABC Wholesale",
        "threshold": 224.06,
        "average": 149.37
      }
    },
    {
      "type": "high_voids",
      "severity": "warning",
      "message": "High number of voids/returns: 8 transactions ($456.78)",
      "details": {
        "void_count": 8,
        "void_amount": 456.78
      }
    }
  ],
  "summary": {
    "critical": 0,
    "warning": 3,
    "info": 2
  },
  "_cache": {
    "hit": false,
    "age_seconds": 0,
    "ttl_seconds": 120
  }
}
```

**Alert Types:**
- `low_inventory`: Items below reorder point
- `high_transaction`: Unusually large transactions (potential data entry errors)
- `no_sales`: No sales recorded (if past noon)
- `high_voids`: Excessive voids/returns

**Severity Levels:**
- `critical`: Immediate attention required
- `warning`: Should be addressed soon
- `info`: Informational, no action required

**Cache TTL:** 2 minutes (120 seconds)

**Use Cases:**
- Real-time operational monitoring
- Exception reporting
- Inventory management alerts
- Fraud detection indicators

---

### 5. Hourly Breakdown
**GET** `/api/pos/hourly-breakdown`

Hourly sales breakdown for a specific date.

**Query Parameters:**
- `date` (optional): Target date in YYYY-MM-DD format. Default: today

**Response:**
```json
{
  "date": "2025-10-06",
  "hourly_data": [
    {
      "hour": 8,
      "hour_label": "08:00",
      "transaction_count": 12,
      "total_sales": 1234.56,
      "avg_transaction": 102.88,
      "unique_customers": 10
    },
    {
      "hour": 9,
      "hour_label": "09:00",
      "transaction_count": 23,
      "total_sales": 2456.78,
      "avg_transaction": 106.82,
      "unique_customers": 18
    }
    // ... hours 10-21
  ],
  "peak_hour": {
    "hour": 12,
    "hour_label": "12:00",
    "sales": 4567.89
  },
  "total_sales": 23450.75,
  "total_transactions": 157,
  "_cache": {
    "hit": false,
    "age_seconds": 0,
    "ttl_seconds": 300
  }
}
```

**Cache TTL:** 5 minutes (300 seconds)

**Use Cases:**
- Staffing optimization
- Peak hour identification
- Customer traffic patterns
- Performance by time of day

---

### 6. Transaction Velocity
**GET** `/api/pos/transaction-velocity`

Real-time transaction velocity metrics for the most recent time window.

**Query Parameters:**
- `minutes` (optional): Time window in minutes. Range: 1-480. Default: 60

**Response:**
```json
{
  "time_window": {
    "start": "2025-10-06T16:15:00",
    "end": "2025-10-06T17:15:00",
    "minutes": 60
  },
  "current_metrics": {
    "transaction_count": 24,
    "total_sales": 3456.78,
    "unique_customers": 19
  },
  "velocity": {
    "transactions_per_minute": 0.4,
    "sales_per_minute": 57.61,
    "avg_transaction": 144.03
  },
  "comparison": {
    "yesterday_transactions": 18,
    "yesterday_sales": 2678.90,
    "transaction_change_percent": 33.33,
    "sales_change_percent": 29.04
  },
  "_cache": {
    "hit": false,
    "age_seconds": 0,
    "ttl_seconds": 60
  }
}
```

**Cache TTL:** 1 minute (60 seconds)

**Use Cases:**
- Real-time monitoring dashboards
- Live performance tracking
- Immediate comparison vs yesterday
- Transaction flow analysis

---

## Cache Management

### Cache Statistics
**GET** `/api/pos/cache/stats`

Get detailed cache statistics.

**Response:**
```json
{
  "total_entries": 12,
  "cache_entries": [
    {
      "key": "operations_summary:date=2025-10-06",
      "age_seconds": 145,
      "ttl_seconds": 300,
      "expired": false,
      "size_bytes": 2048
    }
    // ... more entries
  ],
  "total_size_bytes": 24576
}
```

**Use Cases:**
- Cache performance monitoring
- Debugging cache behavior
- Memory usage tracking

---

### Clear Cache
**GET** `/api/pos/cache/clear`

Clear all cached responses (admin operation).

**Response:**
```json
{
  "success": true,
  "message": "Cache cleared: 12 entries removed"
}
```

**Use Cases:**
- Force refresh all cached data
- Clear stale cache after database updates
- Development/testing

---

## Performance Considerations

### Caching Strategy

Each endpoint has a different cache TTL based on data volatility:

| Endpoint | TTL | Rationale |
|----------|-----|-----------|
| operations-summary | 5 min | Balance between freshness and performance |
| daily-metrics | 3 min | Frequently accessed, moderate volatility |
| top-performers | 10 min | Less frequent changes, expensive query |
| alerts | 2 min | Need fresh data for timely alerts |
| hourly-breakdown | 5 min | Hourly data changes slowly within the hour |
| transaction-velocity | 1 min | Real-time monitoring requires fresh data |

### Query Optimization

All queries are optimized using:
- Proper indexing on Transaction.Time, TransactionNumber
- Aggregations pushed to database level
- LIMIT clauses to prevent unbounded result sets
- Date range filters on all time-based queries

### Best Practices

1. **Use caching wisely**: Don't clear cache unnecessarily
2. **Appropriate date ranges**: Limit queries to necessary time periods
3. **Monitor cache hit rates**: Use `/cache/stats` to track performance
4. **Handle cache metadata**: The `_cache` object in responses indicates cache status

---

## Error Handling

All endpoints return consistent error responses:

**400 Bad Request:**
```json
{
  "error": "Invalid date format. Use YYYY-MM-DD"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Database not initialized"
}
```

**Common Errors:**
- Invalid date format
- Database connection failure
- Query execution errors
- Parameter validation failures

---

## Integration Examples

### JavaScript/Fetch

```javascript
// Get operations summary for today
fetch('/api/pos/operations-summary')
  .then(response => response.json())
  .then(data => {
    console.log('Total Sales:', data.metrics.total_sales);
    console.log('Cache Age:', data._cache.age_seconds);
  });

// Get top performers for last 30 days
fetch('/api/pos/top-performers?start_date=2025-09-06&end_date=2025-10-06&limit=20')
  .then(response => response.json())
  .then(data => {
    data.top_items.forEach(item => {
      console.log(`${item.item_name}: $${item.total_revenue}`);
    });
  });

// Get hourly breakdown with cache stats
fetch('/api/pos/hourly-breakdown?date=2025-10-06')
  .then(response => response.json())
  .then(data => {
    console.log('Peak Hour:', data.peak_hour.hour_label);
    console.log('Peak Sales:', data.peak_hour.sales);
  });
```

### Python/Requests

```python
import requests
from datetime import datetime, timedelta

BASE_URL = 'http://localhost:5000/api/pos'

# Get daily metrics for last 7 days
response = requests.get(f'{BASE_URL}/daily-metrics', params={
    'days': 7,
    'end_date': datetime.now().strftime('%Y-%m-%d')
})
data = response.json()

for day in data['daily_data']:
    print(f"{day['date']}: ${day['total_sales']:.2f}")

# Check for alerts
response = requests.get(f'{BASE_URL}/alerts')
alerts_data = response.json()

for alert in alerts_data['alerts']:
    if alert['severity'] == 'critical':
        print(f"⚠️ CRITICAL: {alert['message']}")
```

### cURL

```bash
# Operations summary with comparison
curl "http://localhost:5000/api/pos/operations-summary?date=2025-10-06&compare=true"

# Top 20 performers for September
curl "http://localhost:5000/api/pos/top-performers?start_date=2025-09-01&end_date=2025-09-30&limit=20"

# Real-time velocity (last 30 minutes)
curl "http://localhost:5000/api/pos/transaction-velocity?minutes=30"

# Clear cache (admin)
curl "http://localhost:5000/api/pos/cache/clear"
```

---

## Data Sources

This API aggregates data from the following existing POS reports:

| Report Type | Primary Use | Tables Accessed |
|-------------|-------------|-----------------|
| daily_sales | Transaction counts and totals | Transaction, TransactionEntry |
| category_sales | Category performance | Transaction, TransactionEntry, Item, Category |
| item_sales | Item-level revenue | Transaction, TransactionEntry, Item |
| cashier_performance | Cashier metrics | Transaction, Cashier |
| payment_methods | Payment breakdown | Transaction, TenderEntry |
| inventory_valuation | Stock levels | Item, Category |
| sales_by_category | Category with profit | Transaction, TransactionEntry, Item, Category |
| sales_by_item | Item with profit | Transaction, TransactionEntry, Item |

---

## Future Enhancements

Potential improvements for future releases:

1. **WebSocket Support**: Real-time push notifications for alerts
2. **Advanced Analytics**: Predictive analytics and trend forecasting
3. **Custom Alert Rules**: User-configurable alert thresholds
4. **Export Functionality**: CSV/Excel export of all reports
5. **Multi-Store Support**: Aggregate data across multiple locations
6. **Redis Caching**: Replace in-memory cache with Redis for scalability
7. **Rate Limiting**: Prevent API abuse
8. **API Keys**: Authentication and authorization

---

## Troubleshooting

### Cache Not Working

1. Check cache stats: `GET /api/pos/cache/stats`
2. Verify cache TTL values in source code
3. Clear cache: `GET /api/pos/cache/clear`

### Slow Response Times

1. Check if cache is being used (`_cache.hit` in response)
2. Reduce date ranges in queries
3. Lower limit parameters
4. Monitor database query performance

### Missing Data

1. Verify date format (YYYY-MM-DD)
2. Check that transactions exist for the date range
3. Ensure database connection is active
4. Review application logs for errors

---

## Version History

**v1.0.0** (2025-10-06)
- Initial release
- 6 core operational endpoints
- Built-in caching with configurable TTL
- Comprehensive error handling
- Cache management endpoints

---

## Support

For issues, feature requests, or questions:
- Check application logs for detailed error messages
- Review database connectivity
- Verify query parameters match documented formats
- Use cache statistics endpoint for cache-related issues

---

## License & Credits

Built for Georgia Dashboard POS System
Aggregates data from existing proven POS reports
Designed for high performance and real-time operational insights
