# tw-limitup-ticks-data

Daily-friendly pipeline that selects Taiwan common stocks which **approached or touched limit-up**, downloads full-day `intraday.trades` from **Fubon Neo**, and writes Parquet plus a manifest ready for GitHub (Git LFS).

每日流程：用富邦 Neo 挑出接近／觸及漲停的普通股，下載當日逐筆成交，寫成 Parquet 與 manifest，方便放進 GitHub。

---

## Layout

```
ticks/YYYY-MM-DD/{symbol}.parquet
ticks/YYYY-MM-DD/manifest.json
scripts/          # CLI entrypoints: select / fetch / write / archive
src/tw_limitup_ticks/
```

Parquet columns: `symbol`, `name`, `date`, `time_us`, `time_local`, `price`, `size`, `volume`, `bid`, `ask`, `serial`, `limit_up_price`, `is_limit_up_price`, plus selection metadata (`market`, `reference_price`, `high_price`, `change_percent`, `touched_limit_up`, …).

---

## Selection

1. `snapshot.movers` on **TSE + OTC**, `direction=up`, `change=percent`, `gte` configurable (**default 8**), `type=COMMONSTOCK`.
2. Confirm with `intraday.ticker`: compare `limitUpPrice` / `referencePrice` against movers `highPrice`.
   - **touched**: `highPrice >= limitUpPrice`
   - **approached**: high change vs reference is still `>= gte` (near the cap, not necessarily printed at it)
3. **Movers limitation:** `snapshot.movers` ranks by **last/close %**, not session-high / high-touch. A name that hit limit-up then pulled back below `--gte` **will not appear**. Optional workaround: **widen `--gte`** (for example `6` or `5`). Names that closed flat or down after a high-touch are still invisible to movers.

---

## Setup

Python 3.9–3.13.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### `fubon_neo` is not on PyPI

The official Fubon Neo SDK is distributed as a **platform wheel**, not a PyPI package. Dry-run / CI does **not** need it.

1. Download the wheel for your OS from the [SDK download page](https://www.fbs.com.tw/TradeAPI/docs/sdk/sdk-download).
2. Install it locally, for example:

```bash
pip install fubon_neo-2.3.0-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

### Credentials (never commit)

```bash
cp .env.example .env
```

| Variable | Meaning |
| --- | --- |
| `FUBON_ID` | National ID used to log in |
| `FUBON_PASSWORD` | Login password |
| `FUBON_CERT_PATH` | Path to the PKCS#12 cert (`.pfx`) |
| `FUBON_CERT_PASSWORD` | Certificate password |

`.gitignore` excludes `.env`, `*.pfx`, and `venv/`. Do not put secrets in the repo, in parquet, or in the manifest.

---

## How to run

Mock / CI (no live login):

```bash
python -m tw_limitup_ticks archive --dry-run --out /tmp/ticks-dry
# or
python scripts/archive.py --dry-run
# or
TW_LIMITUP_DRY_RUN=1 python -m tw_limitup_ticks archive --out /tmp/ticks-dry
```

Live daily archive (after market, with official SDK + cert):

```bash
python -m tw_limitup_ticks archive --gte 8 --out ticks
# widen movers screen if you want more high-then-pullback names:
python -m tw_limitup_ticks archive --gte 5 --out ticks
# only names whose high actually printed the official limit-up
python -m tw_limitup_ticks archive --touched-only --out ticks
```

Step by step:

```bash
python scripts/select.py --gte 8 -o /tmp/candidates.json
python scripts/fetch.py --candidates /tmp/candidates.json -o /tmp/trades
python scripts/write.py --candidates /tmp/candidates.json --trades-dir /tmp/trades --out ticks
```

Equivalent module CLI: `select`, `fetch`, `write`, `archive`.

Tests:

```bash
pytest
```

---

## GitHub storage (Git LFS)

`.gitattributes` tracks `ticks/**/*.parquet` with Git LFS. Once per clone:

```bash
git lfs install
git add ticks/YYYY-MM-DD/*.parquet ticks/YYYY-MM-DD/manifest.json
git commit -m "Add near-limit ticks for YYYY-MM-DD"
```

Keep this repository **private**. Tick dumps are bulky; LFS bandwidth/storage quotas apply.

---

## Terms of use / private note

Fubon Neo market data is provided under Fubon Securities’ API terms. Data is for **personal / internal research**, not redistribution. This repo is a private archive scaffold: do not publish credentials, certificates, or redistributed tick dumps in a public fork.

Official docs: [Market data HTTP API](https://www.fbs.com.tw/TradeAPI/docs/market-data/http-api/getting-started).

---

## 繁體中文摘要

- **選股：** 上市＋上櫃 `snapshot.movers` 上漲、漲跌幅、`gte` 預設 8、僅普通股；再用 `intraday.ticker` 的漲停價／參考價對照 movers 最高價，標記觸及或接近漲停。
- **限制：** movers 看的是**收盤／最新一筆漲跌幅**，不是盤中最高價。衝漲停後回落、收盤漲幅低於門檻的股票會漏掉；可把 `--gte` 放寬，仍無法涵蓋收跌的高點觸及。
- **輸出：** `ticks/YYYY-MM-DD/{代號}.parquet` 與 `manifest.json`。
- **SDK：** `fubon_neo` 為官方 `.whl`，**不在 PyPI**。CI 請用 `--dry-run`。
- **機密：** 只用環境變數／`.env`，憑證與密碼不得提交。
- **授權：** 行情僅供個人研究；建議私有 repo，勿公開散布逐筆成交。
