-- GP_Customer_Daily_Summary Table
-- Stores daily gross profit by customer for FAST customer analytics
-- Populated by populate_gp_customer_summary.py

IF OBJECT_ID('GP_Customer_Daily_Summary', 'U') IS NOT NULL
    DROP TABLE GP_Customer_Daily_Summary;

CREATE TABLE GP_Customer_Daily_Summary (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    BusinessDate DATE NOT NULL,
    CustomerID NVARCHAR(50) NOT NULL,
    CustomerName NVARCHAR(200),  -- COALESCE(Company, FirstName + ' ' + LastName)
    Revenue DECIMAL(18,2) NOT NULL DEFAULT 0,
    COGS DECIMAL(18,2) NOT NULL DEFAULT 0,
    ExciseTax DECIMAL(18,2) NOT NULL DEFAULT 0,
    GrossProfit DECIMAL(18,2) NOT NULL DEFAULT 0,
    TransactionCount INT NOT NULL DEFAULT 0,
    ItemCount INT NOT NULL DEFAULT 0,
    CreatedAt DATETIME DEFAULT GETDATE()
);

-- Create indexes for fast date range queries
CREATE INDEX IX_BusinessDate ON GP_Customer_Daily_Summary(BusinessDate);
CREATE INDEX IX_CustomerID ON GP_Customer_Daily_Summary(CustomerID);
CREATE INDEX IX_BusinessDate_CustomerID ON GP_Customer_Daily_Summary(BusinessDate, CustomerID);
CREATE INDEX IX_GrossProfit ON GP_Customer_Daily_Summary(GrossProfit DESC);

PRINT '✅ GP_Customer_Daily_Summary table created successfully';
PRINT '📊 Ready to store daily GP by customer';
PRINT '🚀 Run: python3 populate_gp_customer_summary_range.py';
