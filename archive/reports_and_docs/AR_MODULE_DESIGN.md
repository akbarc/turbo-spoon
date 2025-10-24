# Accounts Receivable (AR) Module Design Document

## 🎯 Core Objectives
1. **Centralized AR Management**: Single dashboard for all AR-related activities
2. **Customer Intelligence**: Group related entities and understand payment patterns
3. **Cash Flow Prediction**: ML-based forecasting of incoming payments
4. **Collection Optimization**: Prioritize collection efforts based on risk and value
5. **Automated Workflows**: Streamline AR processes with smart automation

---

## 📊 Module Architecture

### 1. Data Layer Components

#### Customer Grouping Engine
```python
# Key Challenge: Multiple entities with similar names
# Example: "Malik Kherani" vs "MALIK KHERANI" vs "Malik Kherani Inc"

class CustomerGroupingEngine:
    """
    Groups related customers using:
    - Fuzzy name matching (Levenshtein distance)
    - Phone number matching
    - Address similarity
    - Email domain matching
    - Payment pattern correlation
    - Shared check signatures
    """
    
    def identify_customer_groups():
        """
        Returns: {
            'master_customer_id': 'MALIK_KHERANI_GROUP',
            'entities': [
                {'id': 123, 'name': 'Malik Kherani', 'company': 'MK Store 1'},
                {'id': 456, 'name': 'MALIK KHERANI', 'company': 'MK Petroleum'},
                {'id': 789, 'name': 'M Kherani', 'company': 'Kherani Enterprises'}
            ],
            'total_ar': 45000,
            'combined_credit_limit': 100000
        }
        """
```

#### Payment Prediction Engine
```python
class PaymentPredictionEngine:
    """
    Predicts cash flow using:
    - Historical payment patterns (day of week, time of month)
    - Seasonal trends
    - Customer-specific payment behavior
    - Outstanding invoice aging
    - Economic indicators
    """
    
    def predict_cash_flow(days_ahead=30):
        """
        Returns daily/weekly cash flow predictions
        with confidence intervals
        """
```

### 2. Frontend Components

#### Main AR Dashboard Layout
```
┌─────────────────────────────────────────────────────────────┐
│                    AR Command Center                         │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Total AR     │  │ Current Due  │  │ Overdue      │      │
│  │ $485,000     │  │ $125,000     │  │ $85,000      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │        7-Day Cash Flow Prediction                 │       │
│  │  [Interactive Chart with Confidence Bands]        │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
│  ┌─────────────────┐  ┌──────────────────────────────┐     │
│  │ Customer Groups │  │ Collection Priority List      │     │
│  │ [Smart Groups]  │  │ [Risk-Scored Customers]       │     │
│  └─────────────────┘  └──────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Feature Specifications

### 1. Customer Group Management

#### Smart Grouping Features
- **Auto-Detection**: Automatically identify related entities
- **Manual Override**: Allow manual grouping/ungrouping
- **Group Metrics**: Combined AR, credit limit, payment history
- **Unified View**: See all transactions across grouped entities

#### Matching Algorithms
```sql
-- Example: Find potential duplicates
WITH PotentialMatches AS (
    SELECT 
        c1.ID as Customer1,
        c2.ID as Customer2,
        c1.Company as Company1,
        c2.Company as Company2,
        -- Fuzzy matching score
        dbo.LevenshteinDistance(
            UPPER(REPLACE(c1.Company, ' ', '')), 
            UPPER(REPLACE(c2.Company, ' ', ''))
        ) as NameSimilarity,
        -- Phone match
        CASE WHEN c1.PhoneNumber = c2.PhoneNumber THEN 1 ELSE 0 END as SamePhone,
        -- Address similarity
        CASE WHEN c1.Address LIKE '%' + c2.Address + '%' THEN 1 ELSE 0 END as SimilarAddress
    FROM Customer c1
    CROSS JOIN Customer c2
    WHERE c1.ID < c2.ID  -- Avoid duplicates
)
SELECT * FROM PotentialMatches
WHERE NameSimilarity <= 3  -- Max 3 character difference
   OR SamePhone = 1
   OR SimilarAddress = 1
```

### 2. Cash Flow Prediction

#### Prediction Components

**A. Historical Analysis**
- Average days to payment by customer
- Payment day patterns (e.g., always pays on Fridays)
- Seasonal patterns (slower in summer, etc.)

**B. Current State Analysis**
- Current invoice aging
- Recent payment velocity changes
- Credit utilization trends

**C. Prediction Models**
```python
def predict_payment_probability(customer_id, invoice_date, amount):
    """
    Returns probability of payment on each future day
    
    Factors:
    - Customer's average days to pay
    - Day of week preference
    - Invoice amount vs typical amount
    - Current AR balance vs credit limit
    - Recent payment behavior changes
    """
    
    # Machine Learning Model Features:
    features = {
        'days_outstanding': days_since_invoice,
        'customer_avg_days_to_pay': 15.5,
        'day_of_week': 'Friday',
        'amount_vs_average': amount / customer_avg_invoice,
        'credit_utilization': current_ar / credit_limit,
        'last_payment_days_ago': 7,
        'payment_streak': 3,  # Consecutive on-time payments
        'nsf_history': 0.05,  # 5% NSF rate
        'seasonal_factor': get_seasonal_factor(current_month)
    }
    
    return ml_model.predict(features)
```

### 3. Collection Priority System

#### Risk Scoring Algorithm
```python
def calculate_collection_priority(customer):
    """
    Score 0-100, higher = needs immediate attention
    """
    
    score = 0
    
    # Age factors (40 points max)
    if days_overdue > 90: score += 40
    elif days_overdue > 60: score += 30
    elif days_overdue > 30: score += 20
    elif days_overdue > 0: score += 10
    
    # Amount factors (30 points max)
    if amount > 10000: score += 30
    elif amount > 5000: score += 20
    elif amount > 1000: score += 10
    
    # Risk factors (30 points max)
    if nsf_rate > 0.2: score += 15  # High NSF rate
    if payment_trend == 'declining': score += 10
    if credit_exceeded: score += 5
    
    return score
```

### 4. AR Analytics Dashboard

#### Key Metrics to Display

**Real-Time Metrics**
- Current AR Balance
- Today's Expected Collections
- New Charges Today
- Payments Received Today

**Aging Analysis**
- 0-30 days: $X (Y%)
- 31-60 days: $X (Y%)
- 61-90 days: $X (Y%)
- 90+ days: $X (Y%)

**Performance Indicators**
- DSO (Days Sales Outstanding)
- Collection Effectiveness Index
- Bad Debt Rate
- Average Days to Pay by Segment

**Predictive Insights**
- 7-Day Cash Flow Forecast
- 30-Day Cash Flow Forecast
- Risk Alerts (customers likely to default)
- Opportunity Alerts (customers ready for credit increase)

### 5. Automated Actions

#### Smart Workflows
1. **Auto-Statement Generation**: Email statements on optimal days
2. **Payment Reminders**: SMS/Email based on customer preference
3. **Credit Hold Triggers**: Auto-hold when limits exceeded
4. **Collection Escalation**: Progressive collection actions
5. **Payment Plan Generator**: AI-suggested payment plans

---

## 🎨 UI/UX Design

### Page Navigation Structure
```
/ar-dashboard (Main Dashboard)
├── /ar-dashboard/customers (Customer Groups & Management)
├── /ar-dashboard/collections (Collection Workbench)
├── /ar-dashboard/predictions (Cash Flow Predictions)
├── /ar-dashboard/statements (Statement Management)
├── /ar-dashboard/analytics (Deep Dive Analytics)
└── /ar-dashboard/settings (AR Settings & Rules)
```

### Visual Design Elements

**Color Coding System**
- 🟢 Green: Current (0-30 days)
- 🟡 Yellow: Warning (31-60 days)
- 🟠 Orange: Overdue (61-90 days)
- 🔴 Red: Seriously Overdue (90+ days)
- 🟣 Purple: Special Accounts (Payment Plans, Disputes)

**Interactive Features**
- Drag & Drop customer grouping
- Click to drill down on any metric
- Hover for quick customer details
- Right-click context menus for actions
- Keyboard shortcuts for power users

---

## 📈 Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Basic AR dashboard page
- [ ] Customer listing with AR balances
- [ ] Simple aging report
- [ ] Manual customer grouping

### Phase 2: Intelligence (Week 2)
- [ ] Auto-detect similar customers
- [ ] Basic payment prediction (historical average)
- [ ] Collection priority scoring
- [ ] Group-level AR view

### Phase 3: Prediction (Week 3)
- [ ] ML-based payment prediction
- [ ] 7-day cash flow forecast
- [ ] Payment pattern analysis
- [ ] Risk alerts

### Phase 4: Automation (Week 4)
- [ ] Auto-statements
- [ ] Smart reminders
- [ ] Collection workflows
- [ ] API integrations

---

## 🔑 Key Database Queries

### Get Customer Groups with AR
```sql
WITH CustomerGroups AS (
    SELECT 
        CASE 
            WHEN Company LIKE '%MALIK%KHERANI%' OR Company LIKE '%KHERANI%' THEN 'KHERANI_GROUP'
            WHEN Company LIKE '%PATEL%' THEN 'PATEL_GROUP'
            ELSE Company
        END as GroupName,
        ID,
        Company,
        AccountBalance,
        CreditLimit
    FROM Customer
    WHERE AccountBalance > 0
)
SELECT 
    GroupName,
    COUNT(*) as EntityCount,
    SUM(AccountBalance) as TotalAR,
    SUM(CreditLimit) as TotalCreditLimit,
    STRING_AGG(Company, ', ') as Entities
FROM CustomerGroups
GROUP BY GroupName
HAVING COUNT(*) > 1 OR SUM(AccountBalance) > 1000
ORDER BY SUM(AccountBalance) DESC
```

### Predict Next Week's Collections
```sql
WITH PaymentHistory AS (
    SELECT 
        CustomerID,
        DATEDIFF(day, t.Time, p.Time) as DaysToPay,
        DATEPART(dw, p.Time) as PaymentDayOfWeek,
        p.Amount
    FROM [Transaction] t
    INNER JOIN Payment p ON p.CustomerID = t.CustomerID
        AND p.Time > t.Time
        AND p.Time < DATEADD(day, 60, t.Time)
    WHERE t.Time > DATEADD(month, -6, GETDATE())
),
CustomerPatterns AS (
    SELECT 
        CustomerID,
        AVG(DaysToPay) as AvgDaysToPay,
        MODE() WITHIN GROUP (ORDER BY PaymentDayOfWeek) as PreferredPayDay,
        AVG(Amount) as AvgPaymentAmount
    FROM PaymentHistory
    GROUP BY CustomerID
)
-- Predict next 7 days collections
SELECT 
    DATEADD(day, number, GETDATE()) as PredictedDate,
    SUM(ar.Balance * 
        CASE 
            WHEN DATEDIFF(day, ar.Date, GETDATE()) + number >= cp.AvgDaysToPay 
            THEN 0.7  -- 70% probability if past average days
            ELSE 0.1  -- 10% probability otherwise
        END
    ) as PredictedCollection
FROM AccountReceivable ar
INNER JOIN CustomerPatterns cp ON ar.CustomerID = cp.CustomerID
CROSS JOIN (SELECT number FROM master..spt_values WHERE type = 'P' AND number < 7) n
WHERE ar.Balance > 0
GROUP BY DATEADD(day, number, GETDATE())
ORDER BY PredictedDate
```

---

## 🚀 Next Steps

1. **Create AR module file structure**
2. **Build basic AR dashboard page**
3. **Implement customer grouping logic**
4. **Develop payment prediction algorithm**
5. **Design collection priority system**
6. **Add interactive visualizations**
7. **Test with real data**
8. **Iterate based on user feedback**

---

## 💡 Innovation Opportunities

1. **AI Chat Assistant**: "Show me customers likely to pay this week"
2. **Mobile App**: Collection agents can update from the field
3. **Customer Portal**: Self-service payment plans
4. **Blockchain**: Immutable AR ledger for disputes
5. **IoT Integration**: Auto-charge when delivery confirmed
6. **Voice Commands**: "Alexa, what's our AR balance?"

---

## 📝 Notes on Customer Deduplication

The "Malik Kherani" example highlights a common issue. We should:

1. **Normalize names** before comparison (remove spaces, uppercase)
2. **Use phonetic matching** (Soundex, Metaphone) for similar sounding names
3. **Check business relationships** (same phone, address, email domain)
4. **Learn from user corrections** to improve matching algorithm
5. **Maintain audit trail** of all grouping/ungrouping actions

Example implementation:
```python
def normalize_name(name):
    """Remove spaces, special chars, uppercase"""
    return re.sub(r'[^A-Z0-9]', '', name.upper())

def are_related_entities(customer1, customer2):
    """Check if two customers are likely the same entity"""
    
    # Name similarity
    name_match = fuzz.ratio(
        normalize_name(customer1.company), 
        normalize_name(customer2.company)
    ) > 85
    
    # Phone match (last 10 digits)
    phone_match = (
        customer1.phone[-10:] == customer2.phone[-10:] 
        if customer1.phone and customer2.phone 
        else False
    )
    
    # Address similarity
    addr_match = fuzz.partial_ratio(
        customer1.address, 
        customer2.address
    ) > 80 if customer1.address and customer2.address else False
    
    return name_match or phone_match or addr_match
```