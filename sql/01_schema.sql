-- Use a dedicated MultiAssetResearch database. This script does not drop or truncate tables.
IF SCHEMA_ID(N'research') IS NULL EXEC(N'CREATE SCHEMA research');
GO
IF OBJECT_ID(N'research.assets', N'U') IS NULL
BEGIN
CREATE TABLE research.[assets] (
    [ticker] NVARCHAR(128) NOT NULL,
    [name] NVARCHAR(128) NOT NULL,
    [asset_class] NVARCHAR(128) NOT NULL,
    CONSTRAINT PK_assets PRIMARY KEY ([ticker])
);
END;
GO
IF OBJECT_ID(N'research.daily_prices', N'U') IS NULL
BEGIN
CREATE TABLE research.[daily_prices] (
    [date] DATE NOT NULL,
    [ticker] NVARCHAR(128) NOT NULL,
    [adjusted_close] FLOAT NOT NULL,
    CONSTRAINT PK_daily_prices PRIMARY KEY ([date], [ticker]),
    CONSTRAINT FK_daily_prices_asset FOREIGN KEY (ticker) REFERENCES research.assets(ticker),
    CONSTRAINT CK_prices_positive CHECK (adjusted_close > 0)
);
END;
GO
IF OBJECT_ID(N'research.daily_macro', N'U') IS NULL
BEGIN
CREATE TABLE research.[daily_macro] (
    [date] DATE NOT NULL,
    [value] FLOAT NOT NULL,
    [series] NVARCHAR(128) NOT NULL,
    CONSTRAINT PK_daily_macro PRIMARY KEY ([date], [series])
);
END;
GO
IF OBJECT_ID(N'research.monthly_returns', N'U') IS NULL
BEGIN
CREATE TABLE research.[monthly_returns] (
    [date] DATE NOT NULL,
    [AGG] FLOAT NOT NULL,
    [BIL] FLOAT NOT NULL,
    [BOND] FLOAT NOT NULL,
    [EEM] FLOAT NOT NULL,
    [EFA] FLOAT NOT NULL,
    [GLD] FLOAT NOT NULL,
    [IEF] FLOAT NOT NULL,
    [LQD] FLOAT NOT NULL,
    [MINT] FLOAT NOT NULL,
    [SPY] FLOAT NOT NULL,
    CONSTRAINT PK_monthly_returns PRIMARY KEY ([date])
);
END;
GO
IF OBJECT_ID(N'research.portfolio_returns', N'U') IS NULL
BEGIN
CREATE TABLE research.[portfolio_returns] (
    [date] DATE NOT NULL,
    [portfolio] NVARCHAR(128) NOT NULL,
    [profile] NVARCHAR(128) NOT NULL,
    [approach] NVARCHAR(128) NOT NULL,
    [gross_return] FLOAT NOT NULL,
    [net_return] FLOAT NOT NULL,
    [cost] FLOAT NOT NULL,
    [traded_fraction] FLOAT NOT NULL,
    [training_end] DATE NOT NULL,
    CONSTRAINT PK_portfolio_returns PRIMARY KEY ([date], [portfolio]),
    CONSTRAINT CK_returns_valid CHECK (net_return > -1 AND gross_return > -1),
    CONSTRAINT CK_training_past CHECK (training_end < [date]),
    CONSTRAINT CK_cost_nonnegative CHECK (cost >= 0 AND traded_fraction >= 0)
);
END;
GO
IF OBJECT_ID(N'research.weights', N'U') IS NULL
BEGIN
CREATE TABLE research.[weights] (
    [date] DATE NOT NULL,
    [portfolio] NVARCHAR(128) NOT NULL,
    [ticker] NVARCHAR(128) NOT NULL,
    [weight] FLOAT NOT NULL,
    CONSTRAINT PK_weights PRIMARY KEY ([date], [portfolio], [ticker]),
    CONSTRAINT FK_weights_asset FOREIGN KEY (ticker) REFERENCES research.assets(ticker),
    CONSTRAINT CK_weights_long CHECK (weight >= 0 AND weight <= 1)
);
END;
GO
IF OBJECT_ID(N'research.portfolio_metrics', N'U') IS NULL
BEGIN
CREATE TABLE research.[portfolio_metrics] (
    [portfolio] NVARCHAR(128) NOT NULL,
    [months] INT NOT NULL,
    [cagr] FLOAT NOT NULL,
    [annual_volatility] FLOAT NOT NULL,
    [maximum_drawdown] FLOAT NOT NULL,
    [sharpe_cash_proxy] FLOAT NULL,
    [tracking_error] FLOAT NOT NULL,
    [information_ratio] FLOAT NULL,
    [alpha_annual] FLOAT NULL,
    [alpha_pvalue_hac] FLOAT NULL,
    [beta] FLOAT NULL,
    [annual_mean_active_return] FLOAT NOT NULL,
    [active_month_hit_rate] FLOAT NOT NULL,
    [annual_traded_fraction] FLOAT NOT NULL,
    CONSTRAINT PK_portfolio_metrics PRIMARY KEY ([portfolio])
);
END;
GO
IF OBJECT_ID(N'research.fund_metrics', N'U') IS NULL
BEGIN
CREATE TABLE research.[fund_metrics] (
    [fund] NVARCHAR(128) NOT NULL,
    [benchmark_proxy] NVARCHAR(128) NOT NULL,
    [months] INT NOT NULL,
    [cagr] FLOAT NOT NULL,
    [annual_volatility] FLOAT NOT NULL,
    [maximum_drawdown] FLOAT NOT NULL,
    [sharpe_cash_proxy] FLOAT NULL,
    [tracking_error] FLOAT NOT NULL,
    [information_ratio] FLOAT NULL,
    [alpha_annual] FLOAT NULL,
    [alpha_pvalue_hac] FLOAT NULL,
    [beta] FLOAT NULL,
    [annual_mean_active_return] FLOAT NOT NULL,
    [active_month_hit_rate] FLOAT NOT NULL,
    CONSTRAINT PK_fund_metrics PRIMARY KEY ([fund])
);
END;
GO
IF OBJECT_ID(N'research.rolling_fund_metrics', N'U') IS NULL
BEGIN
CREATE TABLE research.[rolling_fund_metrics] (
    [date] DATE NOT NULL,
    [fund] NVARCHAR(128) NOT NULL,
    [months] INT NOT NULL,
    [cagr] FLOAT NOT NULL,
    [annual_volatility] FLOAT NOT NULL,
    [maximum_drawdown] FLOAT NOT NULL,
    [sharpe_cash_proxy] FLOAT NULL,
    [tracking_error] FLOAT NOT NULL,
    [information_ratio] FLOAT NULL,
    [alpha_annual] FLOAT NULL,
    [alpha_pvalue_hac] FLOAT NULL,
    [beta] FLOAT NULL,
    [annual_mean_active_return] FLOAT NOT NULL,
    [active_month_hit_rate] FLOAT NOT NULL,
    CONSTRAINT PK_rolling_fund_metrics PRIMARY KEY ([date], [fund])
);
END;
GO
IF OBJECT_ID(N'research.factor_coefficients', N'U') IS NULL
BEGIN
CREATE TABLE research.[factor_coefficients] (
    [fund] NVARCHAR(128) NOT NULL,
    [term] NVARCHAR(128) NOT NULL,
    [coefficient] FLOAT NOT NULL,
    [pvalue_hac] FLOAT NOT NULL,
    [ci_low] FLOAT NOT NULL,
    [ci_high] FLOAT NOT NULL,
    [r_squared] FLOAT NOT NULL,
    [nobs] INT NOT NULL,
    CONSTRAINT PK_factor_coefficients PRIMARY KEY ([fund], [term])
);
END;
GO
IF OBJECT_ID(N'research.rate_sensitivity', N'U') IS NULL
BEGIN
CREATE TABLE research.[rate_sensitivity] (
    [fund] NVARCHAR(128) NOT NULL,
    [return_per_1pp_yield_change] FLOAT NOT NULL,
    [pvalue_hac] FLOAT NOT NULL,
    [r_squared] FLOAT NOT NULL,
    CONSTRAINT PK_rate_sensitivity PRIMARY KEY ([fund])
);
END;
GO
IF OBJECT_ID(N'research.volatility_scores', N'U') IS NULL
BEGIN
CREATE TABLE research.[volatility_scores] (
    [model] NVARCHAR(128) NOT NULL,
    [mae] FLOAT NOT NULL,
    [rmse] FLOAT NOT NULL,
    [observations] INT NOT NULL,
    CONSTRAINT PK_volatility_scores PRIMARY KEY ([model])
);
END;
GO
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name='IX_daily_prices_ticker_date' AND object_id=OBJECT_ID('research.daily_prices'))
CREATE INDEX IX_daily_prices_ticker_date ON research.daily_prices(ticker,[date]) INCLUDE(adjusted_close);
GO
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name='IX_portfolio_returns_name_date' AND object_id=OBJECT_ID('research.portfolio_returns'))
CREATE INDEX IX_portfolio_returns_name_date ON research.portfolio_returns(portfolio,[date]) INCLUDE(net_return);
GO
