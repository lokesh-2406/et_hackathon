# 🔬 Portfolio Surgeon — AI Money Mentor

<div align="center">

**ET AI Hackathon 2026 · Problem Statement PS9 · MF Portfolio X-Ray**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.28-00D4AA?style=for-the-badge)](https://github.com/langchain-ai/langgraph)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F54B27?style=for-the-badge)](https://console.groq.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)
[![Cost](https://img.shields.io/badge/API_Cost-₹0_Free-gold?style=for-the-badge)](https://console.groq.com)

<br/>

> **Most tools analyse portfolios. Portfolio Surgeon engineers decisions.**

*A 7-agent agentic AI system that transforms a raw CAMS/KFintech PDF into a conviction-scored, tax-aware, execution-ready investment action plan — in under 45 seconds.*

<br/>

---

</div>

## 📋 Table of Contents

- [The Problem We're Solving](#-the-problem-were-solving)
- [What Portfolio Surgeon Does](#-what-portfolio-surgeon-does)
- [The Debate Club — Our Differentiator](#️-the-debate-club--our-differentiator)
- [System Architecture](#️-system-architecture)
- [Agent Pipeline](#-agent-pipeline-deep-dive)
- [Quick Start](#-quick-start)
- [Demo Mode](#-demo-mode)
- [Project Structure](#-project-structure)
- [Tech Stack](#-tech-stack)
- [Impact Model](#-impact-model)
- [Sample Output](#-sample-output)
- [Team](#-team)

---

## 😵 The Problem We're Solving

**95% of Indian investors have no structured financial plan.**

A SEBI-registered advisor charges ₹25,000–₹50,000 per year. That makes professional portfolio analysis a luxury accessible only to HNIs — while 14 crore+ demat account holders are flying blind, making decisions based on nothing more than NAV numbers and WhatsApp forwards.

What they actually get from their fund house is a PDF like this:

```
Folio No: 101/A1
Scheme: HDFC Top 100 Fund - Regular Plan - Growth
ISIN: INF179K01BE2

Date        Description     Amount      Units       NAV         Balance
15-Jan-22   SIP Purchase    10,000.00   20.833      480.0000    20.833
15-Feb-22   SIP Purchase    10,000.00   20.619      484.9800    41.452
...
```

Hundreds of rows. No XIRR. No overlap analysis. No benchmark comparison. No rebalancing advice. Just data — with zero decision intelligence layered on top.

**The gap isn't data. It's the missing layer between data and decisions.**

---

## 🧠 What Portfolio Surgeon Does

Upload a CAMS or KFintech PDF. Enter your age and monthly SIP. Get a complete investment intelligence report in 45 seconds.

| What you upload | What you get back |
|---|---|
| Raw CAMS/KFintech PDF | True XIRR per fund, computed from every transaction |
| Fund names in a table | Overlap toxicity score — which funds secretly hold the same stocks |
| Transaction history | Portfolio health score (0–100) with six diagnostic flags |
| Nothing | Bull vs Bear vs Judge debate per fund with conviction score |
| Nothing | Tax-aware rebalancing plan (STCG vs LTCG timing flagged) |
| Nothing | Downloadable action memo ready to hand to your MFD |
| Nothing | Persistent watchlist alerts saved across sessions |

**This is not a dashboard. It is a decision engine.**

---

## ⚔️ The Debate Club — Our Differentiator

Every portfolio analysis tool gives you numbers. Portfolio Surgeon gives you a simulated investment committee.

For each of the top 5 funds by portfolio weight, three specialised AI agents debate the holding:

### 🐂 Bull Agent
Makes the strongest possible case **for holding or increasing allocation**. Grounded in this investor's actual XIRR, portfolio weight, and benchmark performance — not generic market commentary.

```
"Parag Parikh Flexi Cap Fund carries a 29.7% portfolio weight with a compelling
XIRR of 19.5% — significantly outpacing the Nifty 50's 12% one-year return.
Its global diversification into US tech reduces India-specific concentration risk.
The fund's consistent outperformance across 3 and 5 year periods justifies
maintaining and even increasing the current SIP."
```

### 🐻 Bear Agent
Makes the strongest possible case **against the fund — trimming or exiting**. References overlap with other holdings, expense drag, and underperformance with specific numbers.

```
"At 29.7% portfolio weight, Parag Parikh Flexi Cap is a single-fund concentration
risk in a portfolio with an overlap toxicity score of 80/100. Three other large-cap
funds in this portfolio hold identical positions in Reliance and HDFC Bank. The
investor is paying for diversification they are not receiving."
```

### ⚖️ Judge Agent
Synthesises both arguments into a **decisive, conviction-scored verdict in structured JSON**.

```json
{
  "verdict": "TRIM",
  "conviction": 8,
  "reasoning": "Strong XIRR performance argues for retention, but concentration
                risk at 29.7% weight is the dominant risk factor in a portfolio
                already showing 80/100 overlap toxicity.",
  "action": "Reduce allocation by 20-25% via partial redemption. Redirect to
             mid-cap index fund to improve diversification without reducing
             equity exposure."
}
```

The Judge runs at `temperature=0.1` — deterministic, not creative. Bull and Bear run at `temperature=0.3` — argumentative, not hallucinating.

**15 LLM calls. 5 funds. 3 agents each. One investment committee.**

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PORTFOLIO SURGEON                                │
│                    LangGraph Orchestrated Pipeline                        │
└─────────────────────────────────────────────────────────────────────────┘

User Input
  │  CAMS/KFintech PDF
  │  Age + Monthly SIP
  ▼
┌──────────┐    ┌──────────┐    ┌───────────────┐    ┌─────────────┐
│  Parser  │───▶│ Enricher │───▶│ Diagnostician │───▶│ Debate Club │
│ Agent 1  │    │ Agent 2  │    │   Agent 3     │    │  Agent 4    │
└──────────┘    └──────────┘    └───────────────┘    └─────────────┘
     │               │                 │                     │
  pdfplumber      mfapi.in         6 checks              Groq API
  regex + LLM     pyxirr           health score          Bull+Bear+Judge
  fallback        AMFI fallback    overlap/xirr/         per top-5 funds
                  benchmark        allocation
                                                               │
                                                               ▼
                                                    ┌──────────────────┐
                                                    │   Strategist     │
                                                    │   Agent 5        │
                                                    └──────────────────┘
                                                           │
                                                       Groq API
                                                       Tax-aware plan
                                                       STCG/LTCG timing
                                                           │
                              ┌────────────────────────────┘
                              ▼
              ┌──────────┐    ┌──────────┐
              │ Executor │───▶│ Monitor  │
              │ Agent 6  │    │ Agent 7  │
              └──────────┘    └──────────┘
                   │               │
            Action memo         SQLite
            Plain text         Watchlist
            Download-ready     Persistent alerts
                   │               │
                   └───────┬───────┘
                           ▼
               ┌────────────────────┐
               │   Streamlit UI     │
               │   5-Tab Interface  │
               │                    │
               │ • Diagnostics      │
               │ • Debate Club      │
               │ • Rebalancing Plan │
               │ • Action Memo      │
               │ • Watchlist        │
               └────────────────────┘

External Services:
  Groq API (LLaMA 3.3 70B)     — LLM inference, free tier
  mfapi.in                      — Live NAV history, free
  AMFI NAVAll.txt               — Fallback NAV source, free
  SQLite (local)                — Watchlist persistence, built-in
```

### Design Principles

**Single shared state.** Every agent reads from and writes to one `PortfolioState` TypedDict. The Debate Club can reference XIRR computed by the Enricher without any inter-agent API calls. The Strategist sees every verdict the Debate Club produced. Nothing is re-fetched.

**Fault-tolerant by design.** LangGraph checkpoints state after every node. If the Groq API times out mid-debate, the pipeline resumes from the last successful agent — not from scratch.

**Modular and extensible.** Each agent is an independent Python function. Swapping the LLM provider, adding a new diagnostic check, or inserting a new agent between existing ones requires zero changes to any other agent.

---

## 🤖 Agent Pipeline — Deep Dive

### Agent 1 — Parser
**Responsibility:** Extract structured folio and transaction data from raw PDF.

**Strategy:** Two-tier with automatic fallback.

- **Tier 1 (Regex):** Extracts Folio Number, Scheme Name, ISIN, and all transaction rows using compiled regex patterns. Handles both `DD-Mon-YYYY` and `DD/MM/YYYY` date formats. Splits PDF by folio sections. Fast and deterministic.
- **Tier 2 (LLM Fallback):** If regex returns zero folios (format mismatch across AMCs), automatically escalates to Groq with the first 4,000 characters of extracted text. Handles KFintech, non-standard CAMS formats, and merged PDFs.

**Why this matters:** CAMS PDF formats vary significantly across AMCs. SBI MF uses `DD/MM/YYYY`. Axis MF uses "Account No." instead of "Folio No." Franklin Templeton uses Indian number formatting. The two-tier strategy means the demo never returns a blank result.

---

### Agent 2 — Enricher
**Responsibility:** Augment raw folio data with live NAV, XIRR, expense drag, and benchmark returns.

**Four-pass fuzzy matching** maps PDF scheme names (which contain plan/variant suffixes) to mfapi scheme codes:
1. Exact match on normalised scheme name
2. Match on Scheme_NAV_Name column (catches funds like HDFC Top 100)
3. First-4-words prefix match
4. Jaccard word overlap ≥ 0.45

**Hard alias table** handles 30+ funds that were fully renamed through acquisitions: IDFC → Bandhan, L&T → HSBC, Reliance → Nippon, Principal → Sundaram, Franklin Prima → Franklin Flexi Cap.

**AMFI fallback:** If mfapi.in is unreachable during the demo, a cached AMFI `NAVAll.txt` provides current NAV for every fund on the exchange. Zero single points of failure.

**XIRR computation:** Uses `pyxirr` with all purchase transactions as outflows and current market value as the terminal inflow. Sanity-capped at ±99% to filter corrupt PDF data.

---

### Agent 3 — Diagnostician
**Responsibility:** Run 6 analytical checks and produce a portfolio health score.

| Check | What it measures | How |
|---|---|---|
| Overlap Toxicity | Holdings overlap between fund pairs | Category-based heuristic → 0–100 toxicity score |
| Benchmark Comparison | Fund XIRR vs Nifty 50 1-year return | Flags every underperformer with exact delta |
| Asset Allocation | Actual vs recommended equity/debt split | Rule: `(100 - age)%` in equity |
| Concentration Risk | Single fund > 30% of portfolio | Flags fund name + exact percentage |
| Expense Drag | Rupees lost to TER vs direct plans | Projected over 10, 20, and 30 years |
| Health Score | Composite 0–100 portfolio wellness | Weighted penalty model (see below) |

**Health score formula:**
```
Score = 100
Score -= min(overlap_toxicity × 0.3, 30)   # max 30 pts for overlap
Score -= min(underperformers × 8, 24)       # max 24 pts for underperformance
Score -= 15 if allocation is imbalanced     # flat penalty
Score -= min(concentration_funds × 10, 20) # max 20 pts for concentration
Score = max(Score, 0)
```

No LLM calls. Pure Python. Fast and reproducible.

---

### Agent 4 — Debate Club
**Responsibility:** Simulate an investment committee for the top 5 funds.

Three sequential Groq calls per fund:
1. **Bull prompt** — `temperature=0.3`, argumentative, references actual numbers
2. **Bear prompt** — `temperature=0.3`, contrarian, references overlap and underperformance
3. **Judge prompt** — `temperature=0.1`, deterministic JSON verdict

**Judge output schema:**
```python
{
    "verdict": "HOLD" | "TRIM" | "EXIT" | "ADD",
    "conviction": int,   # 1–10
    "reasoning": str,    # 2–3 sentences
    "action": str        # Specific instruction, e.g. "Reduce SIP by 50%"
}
```

JSON parse failure is handled with `re.search(r'\{.*\}', raw, re.DOTALL)` fallback — the demo never crashes on a malformed LLM response.

Rate limit protection: `time.sleep(0.5)` between fund debates keeps well within Groq free tier limits (30 req/min).

---

### Agent 5 — Strategist
**Responsibility:** Synthesise all prior analysis into a tax-aware rebalancing plan.

**Tax classification logic:**
- Holdings > 365 days: **LTCG** at 12.5% (above ₹1.25 lakh exemption)
- Holdings < 365 days: **STCG** at 20%
- Plan timing accounts for this: "Wait 3 months for LTCG treatment" vs "Immediate — LTCG already applicable"

The Strategist prompt passes: health score, total portfolio value, all debate verdicts with conviction scores, overlap toxicity, underperformer count, allocation balance status, 20-year expense drag, and per-fund tax classification — all in one structured prompt. The LLM has everything it needs to give specific, grounded advice.

**Output schema:**
```python
{
    "summary": str,
    "actions": [{"fund", "action_type", "current_sip", "new_sip", "reason", "timing"}],
    "new_funds_to_add": [str],
    "target_allocation": {"large_cap": %, "mid_cap": %, "small_cap": %, "debt": %},
    "priority_order": [str]
}
```

---

### Agent 6 — Executor
**Responsibility:** Convert the rebalancing plan into a formatted, downloadable action memo.

Generates a plain-text document structured for real-world use — an investor can hand this to their mutual fund distributor or use it directly on Coin, Groww, or MFCentral. Sections include: executive summary, diagnostic flags, numbered recommended actions with timing and SIP changes, target allocation with ASCII bar chart, benchmark context, and fund verdict summary.

Saved to `data/action_memo.txt`. Served via Streamlit's `st.download_button`.

---

### Agent 7 — Monitor
**Responsibility:** Persist actionable alerts to a cross-session SQLite watchlist.

**Five trigger categories:**

| Trigger | Condition |
|---|---|
| `UNDERPERFORMANCE` | Fund XIRR < Nifty 50 1-year return |
| `HIGH_CONVICTION_SELL` | Debate Club verdict EXIT/TRIM with conviction ≥ 7 |
| `HIGH_OVERLAP` | Portfolio overlap toxicity score > 60/100 |
| `ALLOCATION_IMBALANCE` | Equity/debt deviation > 10% from age-based recommendation |
| `CONCENTRATION_RISK` | Single fund > 30% of portfolio |

Deduplication logic: same `fund_name + trigger_type + date` combination is never inserted twice. Alerts survive across sessions. Supports `ACTIVE` / `RESOLVED` lifecycle.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Free [Groq API key](https://console.groq.com) (takes 2 minutes)
- A CAMS or KFintech PDF statement — or use the built-in synthetic generator

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/portfolio-surgeon.git
cd portfolio-surgeon

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API key
cp .env.example .env
# Edit .env and add your Groq API key:
# GROQ_API_KEY=gsk_your_key_here
# GROQ_MODEL=llama-3.3-70b-versatile
```

### Run the App

```bash
streamlit run ui/app.py
# Opens at http://localhost:8501
```

Upload a PDF from the sidebar, set your age and monthly SIP, and click **Analyse Portfolio**.

### Run via CLI (no UI)

```bash
python main.py --pdf data/samples/test.pdf --age 32 --sip 15000
```

---

## 🎬 Demo Mode

If you don't have a CAMS PDF handy, generate a fully realistic synthetic portfolio:

### Step 1 — Generate the golden demo portfolio

```bash
# Generate 8-fund portfolio designed to trigger every diagnostic
python create_test_pdf.py --output data/samples/golden.pdf --preset golden

# Or a minimal 2-fund portfolio for quick testing
python create_test_pdf.py --output data/samples/minimal.pdf --preset minimal

# Custom portfolio
python create_test_pdf.py \
  --output data/samples/custom.pdf \
  --name "Rahul Sharma" \
  --pan ABCDE1234F \
  --age 45 \
  --sip 25000
```

### Step 2 — Pre-compute and cache the result

Run this once before your live demo. If anything breaks during the presentation, load the cache instantly — zero pipeline re-run needed.

```bash
python demo_cache.py --pdf data/samples/golden.pdf
```

### Step 3 — Verify the cache

```bash
python demo_cache.py --verify
```

Expected output:
```
[demo_cache] Cache verification — data/golden_cache.json
  Folios     : 8
  Health     : 27/100
  Verdicts   : 5
  Actions    : 5
  Memo chars : 3241
  Watchlist  : 4 trigger(s)

  Cache is valid and ready for demo.
```

### Step 4 — Load demo in the UI

Click **"🎬 Load Demo (cached)"** in the Streamlit sidebar. All 5 tabs populate instantly.

---

### Golden Portfolio — What It Triggers

The synthetic golden portfolio is engineered to fire every diagnostic simultaneously. Here is exactly why each fund was chosen:

| Fund | Value | Diagnostic Triggered |
|---|---|---|
| HDFC Top 100 Fund | ₹3,20,000 | Overlap with Mirae (both hold Reliance, TCS, HDFC Bank) |
| Mirae Asset Large Cap Fund | ₹2,80,000 | Overlap with HDFC Top 100 — raises toxicity score |
| Axis Midcap Fund | ₹1,50,000 | XIRR below Nifty 50 — underperformance flag |
| Parag Parikh Flexi Cap | ₹4,50,000 | >30% of portfolio — concentration risk |
| SBI Small Cap Fund | ₹80,000 | Small-cap overweight for age 32 |
| ICICI Pru Bluechip Fund | ₹1,20,000 | Third large-cap — extreme overlap, triggers EXIT verdict |
| Franklin India Prima Fund | ₹40,000 | Tiny holding — rebalancing candidate |
| Kotak Debt Hybrid Fund | ₹60,000 | Adds hybrid — enables allocation analysis |

**Result:** Health score ~27/100, overlap toxicity 80/100, 3 underperformers, 1 concentration flag, allocation imbalance (100% equity vs 68% recommended for age 32). Every tab tells a story.

---

## 📁 Project Structure

```
portfolio-surgeon/
│
├── main.py                    # CLI entry point
├── graph.py                   # LangGraph pipeline — wires all 7 agents
├── state.py                   # PortfolioState TypedDict — shared state schema
├── create_test_pdf.py         # Synthetic CAMS PDF generator
├── demo_cache.py              # Demo pre-computation and cache loader
├── requirements.txt
├── .env                       # GROQ_API_KEY (not committed)
│
├── agents/
│   ├── parser.py              # Agent 1 — PDF extraction (regex + LLM fallback)
│   ├── enricher.py            # Agent 2 — NAV, XIRR, alias resolution
│   ├── diagnostician.py       # Agent 3 — 6 checks + health score
│   ├── debate_club.py         # Agent 4 — Bull / Bear / Judge per fund
│   ├── strategist.py          # Agent 5 — Tax-aware rebalancing plan
│   ├── executor.py            # Agent 6 — Action memo generation
│   └── monitor.py             # Agent 7 — SQLite watchlist alerts
│
├── utils/
│   ├── llm.py                 # Groq client wrapper with retry logic
│   ├── mfapi.py               # mfapi.in client + AMFI fallback
│   ├── calculations.py        # XIRR, expense drag, date parsing
│   ├── benchmark.py           # Nifty 50 CAGR computation
│   ├── fund_lookup.py         # Fuzzy scheme name → scheme code matching
│   └── tax.py                 # STCG / LTCG classification
│
├── ui/
│   ├── app.py                 # Streamlit 5-tab application
│   └── components.py          # Reusable UI components
│
└── data/
    ├── samples/               # PDF inputs (golden, minimal, custom)
    ├── action_memo.txt        # Latest generated memo
    ├── golden_cache.json      # Pre-computed demo cache
    └── watchlist.db           # SQLite watchlist database
```

---

## ⚙️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Orchestration** | LangGraph 0.2.28 | StateGraph with checkpoint-based fault recovery. Linear pipeline today, conditional branching ready for v2. |
| **LLM** | Groq + LLaMA 3.3 70B | Fastest free inference available. 30 req/min on free tier — sufficient for 15 calls per analysis. |
| **PDF Parsing** | pdfplumber + pypdf | pdfplumber handles complex table layouts; pypdf as fallback for encrypted/damaged files. |
| **XIRR** | pyxirr | Purpose-built for irregular cashflow IRR. Handles SIP timing correctly. numpy-backed, fast. |
| **NAV Data** | mfapi.in + AMFI | mfapi.in provides full historical NAV. AMFI NAVAll.txt provides same-day current NAV as fallback. Both free. |
| **Data** | pandas + numpy | Fuzzy matching, normalisation, allocation breakdown computation. |
| **UI** | Streamlit 1.39 | Rapid full-featured UI. Live agent progress, download buttons, 5-tab layout. |
| **Charts** | Plotly 5.24 | XIRR bar charts, allocation charts, expense drag bar charts. |
| **Database** | SQLite (built-in) | Zero-dependency persistent watchlist. Runs locally, no server needed. |
| **PDF Generation** | reportlab 4.2.5 | Generates synthetic CAMS PDFs for demo. Also used for memo export. |
| **HTTP** | requests + httpx | mfapi.in calls with LRU caching to prevent redundant API calls during demo. |

**Total API cost: ₹0.** Every external service used is either free tier or open data.

---

## 📊 Impact Model

### The Market

| Metric | Value | Source |
|---|---|---|
| Total demat accounts in India | 14+ crore (140 million) | SEBI Annual Report 2024 |
| % with no structured financial plan | ~95% | AMFI Investor Survey 2023 |
| SEBI-registered advisor annual fee | ₹25,000 – ₹50,000 | Market rate |
| Investors who can afford this | <1% | Calculated |
| **Underserved investors** | **~13.3 crore** | **Calculated** |

### What Portfolio Surgeon Changes

| Dimension | Before | After |
|---|---|---|
| Time to analyse a portfolio | 5+ hours (manual research) | 45 seconds |
| Insight quality | Surface-level NAV returns | XIRR + overlap + tax + benchmark |
| Decision quality | Gut feel or WhatsApp advice | Conviction-scored verdict from 3 AI agents |
| Cost | ₹25,000/year for a human advisor | ₹0 |
| Output | Nothing portable | Downloadable action memo |
| Continuity | One-time review | Persistent watchlist alerts across sessions |

### The Vision

Portfolio Surgeon is not a tool for people who already have wealth managers. It is financial intelligence for the 13.3 crore investors who have never had access to anyone who thinks rigorously about their money.

Integrating into a platform like ET Money, Coin by Zerodha, or MFCentral would put institutional-grade portfolio analysis in the hands of every Indian with a smartphone — at zero marginal cost per analysis.

---

## 📄 Sample Output

Below is a real action memo generated by Portfolio Surgeon on the golden demo portfolio (age 32, SIP ₹15,000/month, 8 funds, portfolio value ₹26,83,531):

```
================================================================
        PORTFOLIO SURGEON — PERSONALISED ACTION MEMO
================================================================
  Generated : 29 March 2026
  Funds     : 8 folios analysed
  Value     : Rs 26,83,531
  Score     : 27/100  (Critical — Act Now)
================================================================

EXECUTIVE SUMMARY
----------------------------------------
The portfolio carries extreme overlap toxicity at 80/100, with three
large-cap funds holding near-identical positions. Parag Parikh Flexi
Cap at 29.7% weight constitutes a concentration risk. ICICI Pru
Bluechip Fund has delivered a negative XIRR and should be exited
immediately. The recommended plan reduces overlap, exits the
underperformer, and rebalances toward a 40/20/15/25 allocation.

KEY DIAGNOSTIC FLAGS
----------------------------------------
  Overlap toxicity   : 80/100  [HIGH - action needed]
  Underperformers    : 3 fund(s) below Nifty 50
  Concentration risk : 1 fund(s) > 30% of portfolio
  Allocation status  : Imbalanced (actual equity 100% vs recommended 68%)
  Expense drag (20yr): Rs 5,000

RECOMMENDED ACTIONS
----------------------------------------
 1. [Full Redemption]  ICICI Pru Bluechip Fund
    Timing : Immediate
    Reason : Negative XIRR (-52.1%), conviction EXIT 8/10. Third
             large-cap in portfolio — all overlap with HDFC Top 100.

 2. [Partial Redemption]  Parag Parikh Flexi Cap Fund
    Timing : Immediate
    Reason : Reduce from 29.7% to 20% weight. Concentration risk.
             Redirect proceeds to mid-cap index fund.

 3. [Reduce SIP]  Mirae Asset Large Cap Fund
    Timing : Wait 3 months for LTCG
    SIP    : Rs 8,000/mo → Rs 4,000/mo

FUND VERDICTS SUMMARY
----------------------------------------
  [TRIM]  Parag Parikh Flexi Cap Fund       Conviction 8/10  |  XIRR 19.5%
  [TRIM]  Mirae Asset Large Cap Fund        Conviction 8/10  |  XIRR  8.8%
  [TRIM]  Axis Midcap Fund                  Conviction 7/10  |  XIRR 29.4%
  [HOLD]  SBI Small Cap Fund                Conviction 8/10  |  XIRR 13.9%
  [EXIT]  ICICI Pru Bluechip Fund           Conviction 8/10  |  XIRR -52.1%
================================================================
```

---

## 🛠️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | — | Get free at [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | LLM model identifier |

### Groq Rate Limits

The free Groq tier allows ~30 requests per minute for LLaMA 3.3 70B. Portfolio Surgeon makes 15 LLM calls per full analysis (3 agents × 5 funds) plus 1 strategy call and 1 parser fallback call if needed — well within limits. A `time.sleep(0.5)` between fund debates provides headroom.

### Adding Your Own PDF Formats

If your CAMS PDF uses a non-standard format and the regex parser returns zero folios, the LLM fallback kicks in automatically. To improve regex coverage for a specific AMC format, add the date format to `DATE_FMTS` in `utils/calculations.py` and the folio header pattern to `FOLIO_RE` in `agents/parser.py`.

---

## 🧪 Running Tests

```bash
# Test the full pipeline end-to-end on the golden portfolio
python main.py --pdf data/samples/golden.pdf --age 32 --sip 15000

# Test only the parser on a specific PDF
python -c "
from agents.parser import run_parser
import json
result = run_parser({'pdf_path': 'data/samples/golden.pdf'})
print(f'Folios found: {len(result[\"folios\"])}')
print(json.dumps(result[\"folios\"][0], indent=2))
"

# Test the Groq connection
python -c "from utils.llm import chat; print(chat([{'role':'user','content':'Hello'}]))"

# Test mfapi NAV fetch
python -c "from utils.mfapi import get_nav_history; h = get_nav_history('119598'); print(h[:3])"

# Verify demo cache
python demo_cache.py --verify
```

---

## ⚠️ Known Limitations

- **PDF format coverage:** Regex parser is tuned for standard CAMS format. KFintech and non-standard formats use LLM fallback, which adds ~5 seconds.
- **Overlap analysis:** Current implementation uses category-based heuristics rather than live AMC factsheet holdings. Actual stock-level overlap computation requires scraping AMC websites — planned for v2.
- **Rate limits:** On Groq free tier, analysing more than 5 funds in the Debate Club simultaneously could hit rate limits. The current `time.sleep(0.5)` guard handles this conservatively.
- **Historical NAV depth:** mfapi.in typically provides 3–5 years of NAV history. Older SIPs may have truncated XIRR calculations.

---

## 🗺️ Roadmap

**Post-hackathon v2 priorities:**

- [ ] Stock-level overlap using live AMC factsheets (replace heuristic category model)
- [ ] WhatsApp / Telegram delivery of action memo
- [ ] APScheduler-based monthly watchlist trigger re-evaluation
- [ ] Direct plan vs regular plan switch analysis with brokerage comparison
- [ ] Multi-investor household portfolio view (Couple's Money Planner extension)
- [ ] Integration with MFCentral API for live portfolio sync (no PDF upload needed)
- [ ] Parallel Debate Club execution to reduce 45-second runtime to ~20 seconds

---

## 👥 Team

Built for **ET AI Hackathon 2026** | Problem Statement **PS9 — AI Money Mentor**

| Role | Responsibility |
|---|---|
| P1 — Agent & Backend | LangGraph pipeline, all 7 agents, LLM prompting, XIRR engine |
| P2 — Data & UI | PDF parser, mfapi integration, Streamlit UI, synthetic PDF generator |

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [mfapi.in](https://mfapi.in) — Free mutual fund NAV API for India. This project would not exist without it.
- [AMFI India](https://amfiindia.com) — NAVAll.txt public data feed
- [Groq](https://console.groq.com) — Free LLM inference at production speed
- [LangGraph](https://github.com/langchain-ai/langgraph) — Agent orchestration framework
- [pyxirr](https://github.com/Anexen/pyxirr) — The only Python XIRR library that actually works correctly

---

<div align="center">

**Portfolio Surgeon · ET AI Hackathon 2026**

*Built in 72 hours. ₹0 in API costs. For 13.3 crore underserved investors.*

</div>
