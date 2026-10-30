-- Stale-price diagnostics for research.daily_prices (read-only).
-- A frozen feed keeps delivering rows but repeats the previous close, so row-count and
-- month-end gap checks pass. These queries find repeat runs and the rows they reach.
-- Limits must match config.STALE_RUN_DAYS / STALE_RUN_OVERRIDES.
SET NOCOUNT ON;

-- 1. Runs of consecutive trading days whose close equals the previous close (gaps and islands).
WITH ordered AS (
    SELECT ticker, [date], adjusted_close,
           CASE WHEN adjusted_close = LAG(adjusted_close) OVER (PARTITION BY ticker ORDER BY [date]) THEN 1 ELSE 0 END AS is_repeat,
           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY [date]) AS rn
    FROM research.daily_prices
), repeats AS (
    SELECT ticker, [date], adjusted_close,
           rn - ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY [date]) AS island
    FROM ordered WHERE is_repeat = 1
), runs AS (
    SELECT ticker, MIN([date]) AS first_repeat, MAX([date]) AS last_repeat,
           COUNT(*) AS repeated_days, MIN(adjusted_close) AS repeated_close,
           CASE WHEN ticker = N'BIL' THEN 15 ELSE 5 END AS limit_days
    FROM repeats GROUP BY ticker, island
)
SELECT ticker, first_repeat, last_repeat, repeated_days, limit_days, repeated_close,
       CASE WHEN repeated_days > limit_days THEN 'STALE' ELSE 'within limit' END AS status
FROM runs
WHERE repeated_days >= 5
ORDER BY CASE WHEN repeated_days > limit_days THEN 0 ELSE 1 END, repeated_days DESC, ticker;

-- 2. Was the market open? Other tickers that moved on the repeated days of each STALE run.
WITH ordered AS (
    SELECT ticker, [date], adjusted_close,
           LAG(adjusted_close) OVER (PARTITION BY ticker ORDER BY [date]) AS previous_close,
           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY [date]) AS rn
    FROM research.daily_prices
), repeats AS (
    SELECT ticker, [date], rn - ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY [date]) AS island
    FROM ordered WHERE adjusted_close = previous_close
), stale AS (
    SELECT ticker, MIN([date]) AS first_repeat, MAX([date]) AS last_repeat, COUNT(*) AS repeated_days
    FROM repeats GROUP BY ticker, island
    HAVING COUNT(*) > CASE WHEN ticker = N'BIL' THEN 15 ELSE 5 END
)
SELECT s.ticker, s.first_repeat, s.last_repeat, s.repeated_days,
       COUNT(DISTINCT o.[date]) AS days_with_other_moves,
       COUNT(DISTINCT o.ticker) AS other_tickers_moving
FROM stale s
JOIN ordered o ON o.[date] BETWEEN s.first_repeat AND s.last_repeat
             AND o.ticker <> s.ticker AND o.adjusted_close <> o.previous_close
GROUP BY s.ticker, s.first_repeat, s.last_repeat, s.repeated_days;

-- 3. Affected scope for every STALE run: month-ends whose closes are wrong, the next month's
--    return (wrong base), every 36-month rolling window containing either month, and the
--    full-period fund statistics where the ticker is a fund or its comparator.
WITH ordered AS (
    SELECT ticker, [date], adjusted_close,
           LAG(adjusted_close) OVER (PARTITION BY ticker ORDER BY [date]) AS previous_close,
           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY [date]) AS rn
    FROM research.daily_prices
), repeats AS (
    SELECT ticker, [date], rn - ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY [date]) AS island
    FROM ordered WHERE adjusted_close = previous_close
), stale AS (
    SELECT ticker, MIN([date]) AS first_repeat, MAX([date]) AS last_repeat
    FROM repeats GROUP BY ticker, island
    HAVING COUNT(*) > CASE WHEN ticker = N'BIL' THEN 15 ELSE 5 END
), month_ends AS (
    -- A month-end close is wrong when that month's last trading day sits inside the run.
    SELECT s.ticker, EOMONTH(p.[date]) AS month_end
    FROM stale s
    JOIN (SELECT ticker, MAX([date]) AS [date] FROM research.daily_prices GROUP BY ticker, EOMONTH([date])) p
      ON p.ticker = s.ticker AND p.[date] BETWEEN s.first_repeat AND s.last_repeat
), return_months AS (
    SELECT ticker, month_end FROM month_ends
    UNION SELECT ticker, EOMONTH(DATEADD(MONTH, 1, month_end)) FROM month_ends
)
SELECT 'monthly_returns' AS affected_table, r.ticker AS series, COUNT(*) AS affected_rows,
       MIN(m.[date]) AS first_date, MAX(m.[date]) AS last_date
FROM return_months r JOIN research.monthly_returns m ON m.[date] = r.month_end
GROUP BY r.ticker
UNION ALL
SELECT 'rolling_fund_metrics', f.fund, COUNT(DISTINCT f.[date]), MIN(f.[date]), MAX(f.[date])
FROM return_months r
JOIN research.fund_metrics fm ON r.ticker IN (fm.fund, fm.benchmark_proxy)
JOIN research.rolling_fund_metrics f ON f.fund = fm.fund
     AND f.[date] BETWEEN r.month_end AND EOMONTH(DATEADD(MONTH, 35, r.month_end))
GROUP BY f.fund
UNION ALL
SELECT 'fund_metrics', fm.fund, 1, NULL, NULL
FROM research.fund_metrics fm
WHERE EXISTS (SELECT 1 FROM return_months r WHERE r.ticker IN (fm.fund, fm.benchmark_proxy))
ORDER BY affected_table, series;
