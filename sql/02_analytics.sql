-- Run in MultiAssetResearch after the Python loader commits.
SELECT 'daily_prices' AS TableName, COUNT_BIG(*) AS TotalRows FROM research.daily_prices
UNION ALL SELECT 'monthly_returns', COUNT_BIG(*) FROM research.monthly_returns
UNION ALL SELECT 'portfolio_returns', COUNT_BIG(*) FROM research.portfolio_returns
UNION ALL SELECT 'weights', COUNT_BIG(*) FROM research.weights;

-- Must return no rows: fully invested, long-only allocations.
SELECT [date],portfolio,SUM(weight) AS total_weight,MIN(weight) AS minimum_weight
FROM research.weights GROUP BY [date],portfolio
HAVING ABS(SUM(weight)-1.0)>0.00001 OR MIN(weight)<-0.00001;

-- Must return no rows: training ends before holding month.
SELECT * FROM research.portfolio_returns WHERE training_end >= [date];

-- Rolling annual compounded net returns. Requires at least 12 observations.
WITH Rolling AS (
 SELECT [date],portfolio,
 SUM(LOG(1+net_return)) OVER(PARTITION BY portfolio ORDER BY [date] ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS log_return,
 COUNT(*) OVER(PARTITION BY portfolio ORDER BY [date] ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS n
 FROM research.portfolio_returns
)
SELECT [date],portfolio,EXP(log_return)-1 AS trailing_12m_return FROM Rolling WHERE n=12 ORDER BY portfolio,[date];

-- Return and volatility estimates in decimal units; no individual-manager attribution.
SELECT fund,benchmark_proxy,cagr,tracking_error,information_ratio,alpha_annual,alpha_pvalue_hac
FROM research.fund_metrics;
