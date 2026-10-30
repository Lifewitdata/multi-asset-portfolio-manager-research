"""Walk-forward one-month-ahead realized volatility; labels mature before refitting."""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

def features(prices):
    daily = prices[prices.ticker=="SPY"].set_index("date").adjusted_close.sort_index()
    log_returns = np.log(daily).diff().dropna()
    realized = log_returns.resample("ME").std(ddof=1)*np.sqrt(252)
    counts = log_returns.resample("ME").count()
    realized = realized[counts>=15]
    monthly_return = daily.resample("ME").last().pct_change(fill_method=None)
    frame = pd.DataFrame({"target":realized,"lag1":realized.shift(1),
                          "lag3_mean":realized.shift(1).rolling(3).mean(),
                          "lag12_mean":realized.shift(1).rolling(12).mean(),
                          "lag_abs_return":monthly_return.shift(1).abs()}).dropna()
    return frame

def forecast(prices, minimum_train=36):
    frame = features(prices)
    if minimum_train < 12 or minimum_train >= len(frame):
        raise ValueError("Need at least 12 training rows and one complete holdout month")
    columns = [c for c in frame if c != "target"]
    rows = []
    for i in range(minimum_train, len(frame)):
        train, test = frame.iloc[:i], frame.iloc[[i]]
        predictions = {"Persistence":float(test.lag1.iloc[0]), "Trailing mean":float(test.lag3_mean.iloc[0])}
        for name, model in [("OLS",LinearRegression()), ("Random forest",RandomForestRegressor(n_estimators=100,max_depth=3,min_samples_leaf=6,random_state=42,n_jobs=1))]:
            model.fit(train[columns],train.target)
            predictions[name] = max(0., float(model.predict(test[columns])[0]))
        for name,value in predictions.items():
            rows.append({"date":test.index[0],"model":name,"actual":float(test.target.iloc[0]),
                         "prediction":value,"training_end":train.index[-1],"training_rows":len(train)})
    predictions = pd.DataFrame(rows)
    scores=[]
    for name,g in predictions.groupby("model"):
        e=g.prediction-g.actual
        scores.append({"model":name,"mae":float(e.abs().mean()),"rmse":float(np.sqrt((e**2).mean())),"observations":len(g)})
    return predictions, pd.DataFrame(scores).sort_values("mae")
