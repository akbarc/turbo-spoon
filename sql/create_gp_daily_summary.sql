-- =============================================
-- Table: GP_Daily_Summary
-- Description: Pre-calculated daily gross profit by category
-- Updates: Nightly or on-demand
-- Purpose: Makes category GP queries INSTANT
-- =============================================

-- Drop existing table if it exists
IF EXISTS (SELECT * FROM sys.objects WHERE name = 'GP_Daily_Summary' AND type = 'U')
    DROP TABLE GP_Daily_Summary
GO

-- Create summary table
CREATE TABLE GP_Daily_Summary (
    ID INT IDENTITY(1,1) PRIMARY KEY,

    -- Date dimension
    BusinessDate DATE NOT NULL,

    -- Category dimension
    CategoryID INT NULL,
    CategoryName NVARCHAR(255) NULL,

    -- Financial metrics
    Revenue DECIMAL(18,2) NOT NULL DEFAULT 0,
    COGS DECIMAL(18,2) NOT NULL DEFAULT 0,
    ExciseTax DECIMAL(18,2) NOT NULL DEFAULT 0,
    GrossProfit DECIMAL(18,2) NOT NULL DEFAULT 0,

    -- Volume metrics
    TransactionCount INT NOT NULL DEFAULT 0,
    ItemCount INT NOT NULL DEFAULT 0,

    -- Metadata
    LastUpdated DATETIME NOT NULL DEFAULT GETDATE(),

    -- Unique constraint on date + category
    CONSTRAINT UQ_GP_Daily_Summary UNIQUE (BusinessDate, CategoryID)
)
GO

-- Create indexes for fast queries
CREATE INDEX IX_GP_Daily_Summary_Date ON GP_Daily_Summary(BusinessDate)
GO

CREATE INDEX IX_GP_Daily_Summary_Category ON GP_Daily_Summary(CategoryID)
GO

-- =============================================
-- Stored Procedure: Update Daily GP Summary
-- Call this nightly or on-demand to refresh data
-- =============================================

IF EXISTS (SELECT * FROM sys.objects WHERE name = 'sp_UpdateGPDailySummary' AND type = 'P')
    DROP PROCEDURE sp_UpdateGPDailySummary
GO

CREATE PROCEDURE sp_UpdateGPDailySummary
    @StartDate DATE = NULL,
    @EndDate DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Default to yesterday if no dates provided
    IF @StartDate IS NULL
        SET @StartDate = CAST(DATEADD(day, -1, GETDATE()) AS DATE)

    IF @EndDate IS NULL
        SET @EndDate = @StartDate

    PRINT 'Updating GP Daily Summary from ' + CAST(@StartDate AS VARCHAR) + ' to ' + CAST(@EndDate AS VARCHAR)

    -- Delete existing data for these dates
    DELETE FROM GP_Daily_Summary
    WHERE BusinessDate BETWEEN @StartDate AND @EndDate

    PRINT 'Deleted existing data'

    -- Insert new summary data
    INSERT INTO GP_Daily_Summary (
        BusinessDate,
        CategoryID,
        CategoryName,
        Revenue,
        COGS,
        ExciseTax,
        GrossProfit,
        TransactionCount,
        ItemCount,
        LastUpdated
    )
    SELECT
        CAST(te.TransactionTime AS DATE) as BusinessDate,
        cat.ID as CategoryID,
        cat.Name as CategoryName,
        SUM(te.Price * te.Quantity) as Revenue,
        SUM(te.Cost * te.Quantity) as COGS,
        SUM(COALESCE(pe.PriceC, 0)) as ExciseTax,
        SUM((te.Price * te.Quantity) - (te.Cost * te.Quantity) - COALESCE(pe.PriceC, 0)) as GrossProfit,
        COUNT(DISTINCT te.TransactionNumber) as TransactionCount,
        COUNT(*) as ItemCount,
        GETDATE() as LastUpdated
    FROM [dbo].[TransactionEntry] te
    INNER JOIN [dbo].[Item] i ON te.ItemID = i.ID
    INNER JOIN [dbo].[Category] cat ON i.CategoryID = cat.ID
    LEFT JOIN [dbo].[PUExciseEntry] pe ON te.ID = pe.TransactionEntryID
    WHERE CAST(te.TransactionTime AS DATE) BETWEEN @StartDate AND @EndDate
    AND te.Quantity != 0
    GROUP BY
        CAST(te.TransactionTime AS DATE),
        cat.ID,
        cat.Name

    PRINT 'Inserted ' + CAST(@@ROWCOUNT AS VARCHAR) + ' summary records'

END
GO

-- Grant permissions
GRANT SELECT ON GP_Daily_Summary TO PUBLIC
GO

GRANT EXECUTE ON sp_UpdateGPDailySummary TO PUBLIC
GO

-- =============================================
-- Initial population for last 30 days
-- =============================================
PRINT 'Populating last 30 days of data...'
DECLARE @Start DATE = CAST(DATEADD(day, -30, GETDATE()) AS DATE)
DECLARE @End DATE = CAST(GETDATE() AS DATE)

EXEC sp_UpdateGPDailySummary @Start, @End
GO

PRINT 'GP_Daily_Summary table created and populated!'
PRINT 'Use: SELECT * FROM GP_Daily_Summary ORDER BY BusinessDate DESC'
GO
