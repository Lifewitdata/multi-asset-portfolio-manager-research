# Data sources and provenance

## Historical observations

| Source | Series | Purpose |
|---|---|---|
| Yahoo Finance chart endpoint | SPY, EFA, EEM, IEF, LQD, GLD, BIL, AGG, BOND, MINT adjusted close | Daily and monthly return proxies |
| Federal Reserve Board H.15 via FRED | DGS10, DGS2 | Treasury yield history and retrospective rate analysis |

Study dates are fixed in `config.py`: December 2013 supplies base prices; returns cover January 2014–December 2025. The checked-in `reports/source_manifest.json` records actual retrieval timestamps, request URLs, SHA-256 hashes and row counts from the completed historical run. It contains metadata, not raw prices.

Downloads are cached under `data/raw/` and ignored by git. Adjusted close is specifically requested; unadjusted close is not silently substituted. See [Yahoo's adjustment definition](https://in.help.yahoo.com/kb/adjusted-close-sln28256.html). The unofficial chart endpoint may change, rate-limit, or become unavailable; retries are bounded and failure is explicit.

FRED source pages: [DGS10](https://fred.stlouisfed.org/series/DGS10), [DGS2](https://fred.stlouisfed.org/series/DGS2). Values are percent, not decimal returns. Provider data may be revised; downloaded histories are not vintage datasets.

## Fund identities and comparator rationale

- [SPY issuer page](https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy): US large-cap equity proxy.
- [GLD issuer page](https://www.ssga.com/us/en/individual/etfs/spdr-gold-shares-gld): gold exposure.
- [BIL issuer page](https://www.ssga.com/us/en/individual/etfs/state-street-spdr-bloomberg-1-3-month-t-bill-etf-bil): short Treasury-bill proxy.
- [iShares fund list](https://www.ishares.com/us/products/etf-investments): EFA developed ex-US equities, EEM emerging-market equities, IEF Treasury bonds, LQD investment-grade corporate bonds and AGG aggregate US bonds.
- [PIMCO ETF strategies](https://www.pimco.com/us/en/investment-strategies/etfs): active fixed-income funds BOND and MINT.

AGG is an investable core-bond comparator for BOND; BIL is a conservative cash-like comparator for MINT. These are research choices, not assertions that the ETFs reproduce each fund's official benchmark. Do not attach today's manager names to the full historical sample without verified tenure records.

## Use and redistribution

Accessibility does not imply unrestricted redistribution. This repository supplies retrieval code and derived aggregate findings; it does not commit provider payloads, full price/return tables, or an API key. Data rights remain with their respective owners. Review provider terms before redistributing data, deploying a public feed, or commercial use. No third-party market-data license is granted by this repository.

Synthetic data appear only in deterministic unit tests, explicitly labelled as fixtures. Production ingestion has no synthetic fallback.
