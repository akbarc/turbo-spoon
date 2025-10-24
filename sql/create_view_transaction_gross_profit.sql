-- =============================================
-- View: vw_TransactionGrossProfit
-- Description: Accurate gross profit calculation with excise tax
-- Auto-updates: Yes - whenever POS updates Transaction/TransactionEntry/PUExciseEntry
-- Created: October 15, 2025
-- =============================================

IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_TransactionGrossProfit')
    DROP VIEW vw_TransactionGrossProfit
GO

CREATE VIEW vw_TransactionGrossProfit AS
SELECT
    -- Transaction Info
    te.TransactionNumber,
    te.ID as TransactionEntryID,
    te.TransactionTime,
    t.CustomerID,
    COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
    t.StoreID,

    -- Item Info
    te.ItemID,
    i.Description as ItemName,
    i.ItemLookupCode,
    cat.Name as CategoryName,
    cat.ID as CategoryID,
    dept.Name as DepartmentName,

    -- Quantities and Prices
    te.Quantity,
    te.Price as UnitPrice,
    te.Cost as UnitCost,

    -- Financial Calculations
    (te.Price * te.Quantity) as Revenue,
    (te.Cost * te.Quantity) as COGS,

    -- Excise Tax (from PUExciseEntry)
    COALESCE(pe.PriceC, 0) as ExciseTax,
    pe.SubDescription3 as ExciseTaxType,

    -- CORRECT Gross Profit Calculation
    -- GP = Revenue - COGS - Excise Tax
    (te.Price * te.Quantity) -
    (te.Cost * te.Quantity) -
    COALESCE(pe.PriceC, 0) as GrossProfit,

    -- GP Margin %
    CASE
        WHEN (te.Price * te.Quantity) > 0
        THEN (
            ((te.Price * te.Quantity) - (te.Cost * te.Quantity) - COALESCE(pe.PriceC, 0))
            / (te.Price * te.Quantity) * 100
        )
        ELSE 0
    END as GPMarginPercent,

    -- Flags
    CASE WHEN pe.PriceC IS NOT NULL THEN 1 ELSE 0 END as HasExciseTax,
    CASE WHEN te.Quantity < 0 THEN 1 ELSE 0 END as IsReturn

FROM [dbo].[TransactionEntry] te
INNER JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
LEFT JOIN [dbo].[PUExciseEntry] pe ON te.ID = pe.TransactionEntryID
LEFT JOIN [dbo].[Item] i ON te.ItemID = i.ID
LEFT JOIN [dbo].[Category] cat ON i.CategoryID = cat.ID
LEFT JOIN [dbo].[Department] dept ON i.DepartmentID = dept.ID
LEFT JOIN [dbo].[Customer] c ON t.CustomerID = c.ID

WHERE te.Quantity != 0  -- Exclude zero-quantity entries

GO

-- Create indexes for performance
CREATE INDEX IX_vw_TransactionGrossProfit_TransactionTime
ON TransactionEntry(TransactionTime)
GO

CREATE INDEX IX_vw_TransactionGrossProfit_CustomerID
ON [Transaction](CustomerID)
GO

-- Grant permissions
GRANT SELECT ON vw_TransactionGrossProfit TO PUBLIC
GO

PRINT 'View vw_TransactionGrossProfit created successfully'
PRINT 'This view auto-updates when POS adds transactions'
GO
