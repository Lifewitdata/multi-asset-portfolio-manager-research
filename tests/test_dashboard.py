import pandas as pd
import pytest
from multi_asset.dashboard import create_app,portfolio_view,fund_view,custom_view
from multi_asset.analytics import metrics,evaluate_funds,factor_research
from multi_asset.portfolio import backtest

@pytest.fixture(scope="module")
def tables():
    import numpy as np
    from multi_asset.config import ASSETS
    rng=np.random.default_rng(21)
    r=pd.DataFrame(rng.normal(.003,.025,(40,len(ASSETS))),index=pd.date_range("2014-01-31",periods=40,freq="ME"),columns=list(ASSETS))
    r.index.name="date"
    p,w=backtest(r)
    stats=[]
    for name,g in p.groupby("portfolio"):
        b=p[p.portfolio==name.split()[0]+" Policy"].set_index("date").net_return
        stats.append({"portfolio":name,**metrics(g.set_index("date").net_return,b,r.BIL)})
    funds,rolling=evaluate_funds(r,{"BOND":"AGG","MINT":"BIL"})
    macro=pd.concat([pd.DataFrame({"date":r.index,"series":s,"value":np.linspace(1,3,len(r))+rng.normal(0,.1,len(r))}) for s in ["DGS10","DGS2"]])
    factors,rates,_=factor_research(r,macro)
    return {"portfolio_returns":p,"weights":w,"portfolio_metrics":pd.DataFrame(stats),"fund_metrics":funds,
            "rolling_fund_metrics":rolling,"factor_coefficients":factors,"rate_sensitivity":rates,
            "monthly_returns":r.reset_index(),"volatility_scores":pd.DataFrame({"model":["Persistence"],"mae":[.1],"rmse":[.2],"observations":[3]})}

def test_layout_and_dependencies(tables):
    app=create_app(tables);client=app.server.test_client()
    for path in ["/","/_dash-layout","/_dash-dependencies","/assets/style.css"]:
        assert client.get(path).status_code==200
    assert len(app.callback_map)==3

@pytest.mark.parametrize("profile",["Conservative","Balanced","Growth"])
def test_profile_charts(tables,profile):
    cards,growth,dd,w=portfolio_view(tables,profile)
    assert len(cards)==4 and len(growth.data)==2 and len(dd.data)==2
    assert growth.data[0].y[0]==100
    assert len(w.data)==7

@pytest.mark.parametrize("fund",["BOND","MINT"])
def test_fund_charts(tables,fund):
    t,r,f=fund_view(tables,fund)
    assert t.rowData[0]["fund"]==fund and len(r.data)==1 and len(f.data)==1

def test_custom_allocation(tables):
    message,fig=custom_view(tables,55,50)
    assert "Estimated annual volatility" in message and len(fig.data)==7

def test_infeasible_custom_message(tables):
    message,fig=custom_view(tables,10,30)
    assert "infeasible" in message and not fig.data

def test_profile_callback_http(tables):
    app=create_app(tables)
    key=next(k for k in app.callback_map if "kpis" in k)
    response=app.server.test_client().post("/_dash-update-component",json={
        "output":key,"outputs":[{"id":"kpis","property":"children"},{"id":"growth","property":"figure"},{"id":"drawdown","property":"figure"},{"id":"allocation","property":"figure"}],
        "inputs":[{"id":"profile","property":"value","value":"Growth"}],"state":[],"changedPropIds":["profile.value"]})
    assert response.status_code==200
    assert "growth" in response.json["response"]
