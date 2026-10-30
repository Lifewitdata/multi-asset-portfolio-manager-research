"""Local Dash research application, backed by processed CSVs or SQL Server."""
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html
import dash_ag_grid as dag
from .config import ROOT, PROFILES, INVESTABLE
from .analytics import drawdown
from .portfolio import optimize

COLORS = {"Optimized":"#2dd4bf", "Policy":"#a5b4fc"}

def load_tables():
    names=["portfolio_returns","portfolio_metrics","weights","fund_metrics","rolling_fund_metrics",
           "factor_coefficients","rate_sensitivity","volatility_scores","monthly_returns"]
    if os.getenv("MULTI_ASSET_DASH_SOURCE", "csv").lower()=="sqlserver":
        from .database import read_dashboard
        return read_dashboard(names)
    missing=[name for name in names if not (ROOT/f"data/processed/{name}.csv").exists()]
    if missing:
        raise FileNotFoundError("Run python -m multi_asset.pipeline --download before starting Dash.")
    from .data import verify_processed
    verify_processed()
    return {n:pd.read_csv(ROOT/f"data/processed/{n}.csv") for n in names}

def table(frame, ident=None):
    data=frame.copy()
    for c in data.select_dtypes(include="number"):
        data[c]=data[c].round(5)
    args=dict(rowData=data.replace({np.nan:None}).to_dict("records"),
              columnDefs=[{"headerName":c.replace("_"," ").title(),"field":c} for c in data],
              defaultColDef={"sortable":True,"resizable":True,"filter":True,"minWidth":140},
              dashGridOptions={"pagination":True,"paginationPageSize":10,"paginationPageSizeSelector":[10,25,50],"domLayout":"autoHeight"},
              style={"width":"100%"})
    if ident:args["id"]=ident
    return dag.AgGrid(**args)

def style(fig, title):
    fig.update_layout(title=title,template="plotly_white",font={"family":"Arial","color":"#163047"},
                      margin=dict(l=45,r=20,t=65,b=45),legend=dict(orientation="h",y=-.2),paper_bgcolor="white")
    return fig

def portfolio_view(tables, profile):
    p=tables["portfolio_returns"].copy();p["date"]=pd.to_datetime(p.date)
    p=p[p.profile==profile].sort_values("date")
    growth, dd = go.Figure(), go.Figure()
    for approach,group in p.groupby("approach"):
        r=group.set_index("date").net_return
        initial=r.index[0]-pd.offsets.MonthEnd(1)
        wealth=pd.concat([pd.Series([100.],index=[initial]),100*(1+r).cumprod()])
        growth.add_scatter(x=wealth.index,y=wealth,name=approach,line=dict(color=COLORS[approach],width=3))
        dd.add_scatter(x=r.index,y=drawdown(r)*100,name=approach,line=dict(color=COLORS[approach]))
    stats=tables["portfolio_metrics"]
    selected=stats[stats.portfolio==f"{profile} Optimized"].iloc[0]
    cards=[html.Div([html.Span(label),html.Strong(f"{selected[key]:.2%}")],className="kpi") for label,key in
           [("Net CAGR","cagr"),("Annual volatility","annual_volatility"),("Maximum drawdown","maximum_drawdown"),("Tracking error vs policy","tracking_error")]]
    w=tables["weights"];w=w[w.portfolio==f"{profile} Optimized"]
    latest=w[w.date==w.date.max()].copy()
    allocation=style(px.bar(latest,x="ticker",y="weight",color="ticker",color_discrete_sequence=px.colors.qualitative.Safe),"Last historical rebalance weights")
    allocation.update_layout(showlegend=False);allocation.update_yaxes(tickformat=".0%")
    return cards,style(growth,"Growth of $100 · after modelled trading costs"),style(dd,"Drawdown · monthly observations (%)"),allocation

def fund_view(tables, fund):
    row=tables["fund_metrics"];row=row[row.fund==fund]
    rolling=tables["rolling_fund_metrics"];rolling=rolling[rolling.fund==fund]
    fig=style(px.line(rolling,x="date",y="information_ratio"),"Rolling 36-month information ratio")
    factors=tables["factor_coefficients"];factors=factors[(factors.fund==fund)&(factors.term!="const")].copy()
    factors["upper_error"]=factors.ci_high-factors.coefficient
    factors["lower_error"]=factors.coefficient-factors.ci_low
    chart=style(px.bar(factors,x="term",y="coefficient",error_y="upper_error",error_y_minus="lower_error"),"Factor exposure · HAC 95% confidence intervals")
    return table(row),fig,chart

def custom_view(tables, equity_percent, cap_percent):
    try:
        history=tables["monthly_returns"].set_index("date")[INVESTABLE].tail(36)
        w,cov=optimize(history,float(equity_percent)/100,float(cap_percent)/100)
        risk=float(np.sqrt(w.to_numpy() @ cov @ w.to_numpy()*12))
        frame=w.rename("weight").rename_axis("ticker").reset_index()
        fig=style(px.bar(frame,x="ticker",y="weight",color="ticker"),"Custom allocation · latest 36-month covariance")
        fig.update_yaxes(tickformat=".0%");fig.update_layout(showlegend=False)
        message=f"Estimated annual volatility: {risk:.2%}. This is an in-sample risk estimate, not a forecast or backtest. Equity {equity_percent}%; asset cap {cap_percent}%."
        return message,fig
    except (ValueError,TypeError) as exc:
        return str(exc),style(go.Figure(),"No feasible allocation")

def create_app(tables=None):
    tables=load_tables() if tables is None else tables
    app=Dash(__name__,assets_folder=str(ROOT/"assets"),title="Multi-Asset Research Lab")
    source=os.getenv("MULTI_ASSET_DASH_SOURCE","csv").upper()
    app.layout=html.Main([
        html.Header([html.Div("QUANTITATIVE RESEARCH / 02",className="eyebrow"),html.H1("Multi-Asset Research Lab"),
                     html.P("Client allocation, active fund evaluation and factor research using historical market data.")]),
        html.Div(f"REAL HISTORICAL DATA · USD · 2014–2025 · Retrospective research · Source mode: {source}",className="banner"),
        html.Section([html.H2("Client portfolio research"),html.P("36-month trailing covariance. Monthly rebalance. 10bp per dollar bought or sold. Each profile has an equity-matched policy comparator."),
                      html.Label("Client profile"),dcc.Dropdown(list(PROFILES),"Balanced",id="profile",clearable=False),
                      html.Div(id="kpis",className="kpis"),html.Div([dcc.Graph(id="growth"),dcc.Graph(id="drawdown")],className="grid"),
                      dcc.Graph(id="allocation")]),
        html.Section([html.H2("Active fund evaluation"),html.P("BOND vs AGG and MINT vs BIL are fund-level ETF proxy comparisons. MINT carries risks beyond Treasury bills; alpha is not proof of manager skill. Metrics below are decimals unless labelled otherwise."),
                      dcc.Dropdown(["BOND","MINT"],"BOND",id="fund",clearable=False),html.Div(id="fund-table"),
                      html.Div([dcc.Graph(id="fund-rolling"),dcc.Graph(id="factors")],className="grid"),
                      html.P("Blank MINT alpha/beta values are intentional: BIL is also the cash proxy, so benchmark excess return has no variation. Factors: SPY−BIL equity excess, IEF−BIL Treasury excess, LQD−IEF credit-relative return. Credit proxy is not duration-neutral. Regressions are retrospective attribution.")]),
        html.Section([html.H2("Bespoke allocation sandbox"),html.P("Solve using the latest study-window data. These controls do not alter the historical profile backtests above."),
                      html.Label("Equity allocation (%)"),dcc.Slider(10,85,5,value=55,id="equity",marks={10:"10%",25:"25%",55:"55%",85:"85%"}),
                      html.Label("Maximum allocation to one asset (%)"),dcc.Slider(30,70,5,value=50,id="cap",marks={30:"30%",50:"50%",70:"70%"}),
                      html.Button("Calculate allocation",id="solve",n_clicks=0),html.P(id="custom-message"),dcc.Graph(id="custom-weights")]),
        html.Section([html.H2("Volatility forecast validation"),html.P("Expanding-window next-month SPY realized volatility. Fixed model settings; no shuffled split. Annualized volatility decimal units. Forecasts do not drive portfolio weights."),
                      dcc.Graph(figure=style(px.bar(tables["volatility_scores"],x="model",y=["mae","rmse"],barmode="group"),"Forecast error · lower is better")),table(tables["volatility_scores"])]),
        html.Footer("Research prototype. Surviving instruments selected retrospectively; adjusted histories may be revised. No individual-manager attribution, tax modelling, FX hedge or investment recommendation.")
    ],className="page")
    @app.callback(Output("kpis","children"),Output("growth","figure"),Output("drawdown","figure"),Output("allocation","figure"),Input("profile","value"))
    def update_profile(profile):return portfolio_view(tables,profile)
    @app.callback(Output("fund-table","children"),Output("fund-rolling","figure"),Output("factors","figure"),Input("fund","value"))
    def update_fund(fund):return fund_view(tables,fund)
    @app.callback(Output("custom-message","children"),Output("custom-weights","figure"),Input("solve","n_clicks"),State("equity","value"),State("cap","value"))
    def update_custom(n,equity,cap):return custom_view(tables,equity,cap)
    return app

if __name__=="__main__":
    create_app().run(host="127.0.0.1",port=8051,debug=False)
