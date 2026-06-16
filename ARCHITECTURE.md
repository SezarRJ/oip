# Opportunity Intelligence Platform (OIP)
## Complete Architecture & Design Document

---

### 1. Executive Summary

The **Opportunity Intelligence Platform (OIP)** is a personal-use AI-powered system designed for a solo international trader, broker, and market intelligence analyst. Its singular purpose is to **continuously discover, evaluate, rank, and monitor the highest-value business opportunities across international markets** — before they become obvious to competitors.

**Core Question Answered Daily:**
> "If I had $0, $10,000, $50,000, $100,000, $500,000, or $1,000,000 available today, where should I deploy it for the highest probability-adjusted profit?"

**This is NOT a SaaS product.** There are no users, teams, CRM, billing, subscriptions, or public dashboards. It is a personal intelligence system.

---

### 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OIP SYSTEM ARCHITECTURE                           │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ DATA         │  │ DATA         │  │ OPPORTUNITY  │              │
│  │ COLLECTION   │→ │ EXTRACTION   │→ │ DETECTION    │              │
│  │ LAYER        │  │ LAYER        │  │ ENGINE       │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│         ↑                                   ↓                       │
│  ┌──────────────────────────────────────────────────┐              │
│  │             SCHEDULER / ORCHESTRATOR              │              │
│  └──────────────────────────────────────────────────┘              │
│                                                      ↓              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ PROFITABILITY│  │ RISK         │  │ SCORING      │              │
│  │ ENGINE       │  │ ENGINE       │  │ ENGINE       │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│         ↓                 ↓                  ↓                      │
│  ┌──────────────────────────────────────────────────┐              │
│  │              AI DECISION ENGINE                   │              │
│  │         Daily Briefing | Capital Allocation       │              │
│  └──────────────────────────────────────────────────┘              │
│                                                      ↓              │
│  ┌──────────────────────────────────────────────────┐              │
│  │              OUTPUT & REPORTING                   │              │
│  │    CLI Briefing | CSV Export | Email Digest       │              │
│  └──────────────────────────────────────────────────┘              │
│                                                                     │
│  ┌──────────────────────────────────────────────────┐              │
│  │              POSTGRESQL DATABASE                  │              │
│  │   Companies | Products | Demand | Opportunities   │              │
│  └──────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 3. Philosophy: Opportunity-First, Not Product-First

Traditional trade platforms start with a product catalog and let users search. OIP inverts this:

```
Traditional:          Products → Search → Match → Maybe Opportunity
OIP Approach:         Signals → Detection → Opportunity → Product as Component
```

The system thinks like an **investor**, **trader**, **broker**, and **intelligence analyst** simultaneously.

For every detected opportunity, the system answers:
- **Why** does this opportunity exist?
- **Why** have competitors not fully exploited it?
- **How long** will the window remain open?
- **What** is required to capture it?
- **What risks** exist?
- **Is it repeatable?**

---

### 4. Data Collection Layer

#### 4.1 Source Categories

| Category | Examples | Frequency |
|----------|----------|-----------|
| B2B Marketplaces | Alibaba, Made-in-China, TradeKey, TurkExim | Every 60 min |
| Trade Databases | UN Comtrade, ITC Trade Map | Daily |
| Tender Platforms | DG Market, EKAP, Etimad | Every 60 min |
| News Sources | Reuters, Bloomberg, Trade Arabia | Every 30 min |
| Government Portals | Customs databases, procurement sites | Daily |
| Social Media | LinkedIn, industry forums | Every 6 hours |
| Economic Reports | IMF, World Bank, Central Banks | Weekly |

#### 4.2 Collector Architecture

Each collector is a standalone Python module implementing the `BaseCollector` interface:

```python
class BaseCollector(ABC):
    source_name: str
    source_type: SourceType
    frequency: Frequency
    target_countries: List[str]

    @abstractmethod
    async def collect(self) -> CollectionResult: ...
    @abstractmethod
    def can_collect(self) -> bool: ...
```

Collectors run **independently and concurrently**. One failing does not affect others.

---

### 5. Data Extraction

#### 5.1 Company Extraction
For every company discovered:
- Name (in Latin, Arabic, Chinese, Turkish scripts)
- Country, City, Address, GPS coordinates
- Website, Email, Phone, WhatsApp
- Decision makers (name, title, department)
- Company size, annual revenue, export volume
- Products manufactured/traded
- Production capacity
- Certifications (ISO, CE, etc.)
- Reliability indicators (years in business, verifications)

#### 5.2 Product Extraction
- Product name, category, subcategory
- HS code (Harmonized System)
- Specifications (JSON)
- MOQ, unit price, bulk pricing
- Lead time, packaging
- Weight, dimensions
- Manufacturer, origin country

#### 5.3 Demand Signal Extraction
- Buyer identity
- RFQ / Tender / Procurement notice reference
- Products needed, estimated volume
- Timeline (published, deadline, execution)
- Budget indicators
- Tender status, bid bond requirements

---

### 6. Opportunity Detection Engine

The heart of OIP. **14 detectors** run simultaneously:

| Detector | What It Finds |
|----------|---------------|
| Trade Arbitrage | Price gaps between source and demand markets |
| Information Arbitrage | Knowing something others don't |
| Supply Gap | Markets where demand exists but supply is absent |
| Demand Gap | Supply that exists but demand isn't visible yet |
| Inventory Liquidation | Products priced significantly below market |
| Project Procurement | Large projects needing materials |
| Tender Opportunities | Open tenders matching supplier capability |
| Reconstruction | Post-conflict rebuilding needs |
| Regional Shortage | Products in short supply region-wide |
| Emerging Demand | Demand trends before they peak |
| Regulatory Change | Opportunities from new laws/tariffs |
| Shipping Route Advantage | Geographic/logistics edges |
| Supplier-Buyer Match | Direct match of supply to demand |
| Brokerage | Commission opportunities requiring no capital |

---

### 7. Profitability Engine

Calculates complete financial picture for every opportunity.

**Full Cost Model:**
```
Total Cost = Purchase Cost
           + Shipping Cost
           + Insurance (1% of cargo value)
           + Customs Duties (country-pair and HS-code specific)
           + VAT / Sales Tax
           + Handling (2%)
           + Warehousing (1% per month)
           + Financing (annualized rate for cash cycle period)
           + Brokerage Fee (if applicable)
           + Miscellaneous (2% contingency)
```

**Revenue Model (Trade):**
```
Expected Revenue = Total Cost × (1 + Target Margin)
Net Profit = Expected Revenue - Total Cost
ROI = Net Profit / Total Cost × 100
```

**Revenue Model (Brokerage):**
```
Commission = Deal Size × 3%
Net Profit = Commission (zero capital cost)
ROI = ∞ (no capital deployed)
```

**Shipping Cost Estimates:**

| Corridor | Mode | 20GP Container | Per KG | Transit |
|----------|------|---------------|--------|---------|
| Turkey → Iraq | Land | $1,500 | $0.08/kg | 2 days |
| China → Iraq | Sea | $3,500 | $0.15/kg | 30 days |
| Turkey → Saudi | Sea | $2,200 | $0.10/kg | 7 days |
| China → UAE | Sea | $2,500 | $0.10/kg | 20 days |
| Turkey → Syria | Land | $800 | $0.05/kg | 1 day |

---

### 8. Risk Engine

**11 risk dimensions** combined into a unified composite risk score (0-100):

| Dimension | Weight | Assessment Method |
|-----------|--------|-------------------|
| Supplier Risk | 20% | Verification status, years in business, certifications, country |
| Buyer Risk | 15% | Type (government vs private), verification, country |
| Country Risk | 15% | Baselined per country, political stability |
| Political Risk | 8% | Sanctions exposure, conflict zones |
| Currency Risk | 10% | Volatility (TRY 25%, IRR 35%, SAR 1%) |
| Logistics Risk | 10% | Distance, border crossings, port efficiency |
| Customs Risk | 10% | Country-specific clearance complexity |
| Payment Risk | 10% | Method (LC=20, advance=10, open account=60), banking restrictions |
| Fraud Risk | 5% | Verification gaps, email-only contacts |
| Market Risk | 5% | Opportunity-type volatility |
| Execution Risk | 7% | Language/cultural barriers, complexity |

**Risk Levels:**
- **Low** (<25): Execute with standard precautions
- **Medium** (25-50): Execute with mitigations
- **High** (50-75): Requires significant risk management
- **Extreme** (>75): Avoid unless unique strategic value

---

### 9. Opportunity Scoring Engine

Scores every opportunity from **0-100** using 8 weighted dimensions:

| Dimension | Weight | What Drives It |
|-----------|--------|----------------|
| Profit | 25% | Absolute expected net profit |
| Probability | 20% | Confidence × evidence strength |
| Capital Efficiency | 15% | ROI percentage |
| Execution Ease | 10% | Inverted complexity (1-10 scale) |
| Speed to Revenue | 10% | Cash conversion cycle (days) |
| Repeatability | 8% | Can this be done again? |
| Risk Inverse | 7% | 100 - risk score |
| Scalability | 5% | Can the deal size grow? |

**Score Tiers:**
- **S (85-100)**: Exceptional — execute immediately
- **A (70-84)**: Strong — investigate and pursue
- **B (50-69)**: Solid — pursue with standard risk management
- **C (30-49)**: Marginal — additional validation required
- **D (0-29)**: Weak — not recommended

---

### 10. AI Decision Engine

#### 10.1 Daily Briefing (07:00 Baghdad Time)

Every day the platform answers:

**By Capital Tier:**
- Top opportunities requiring **no capital** (brokerage/commission)
- Top opportunities requiring **under $10,000**
- Top opportunities requiring **under $50,000**
- Top opportunities requiring **under $100,000**
- Top opportunities requiring **under $500,000**
- Top opportunities requiring **under $1,000,000**

**By Category:**
- Top brokerage opportunities
- Top trading opportunities
- Top low-risk opportunities
- Top high-margin opportunities
- Top repeatable opportunities
- Top long-term strategic opportunities

**Forward-Looking:**
- Opportunities expected to emerge in **3, 6, 12, and 24 months**

#### 10.2 Capital Allocation

For any given amount, the engine builds a **portfolio** of opportunities:
- Sorts by score within capital constraint
- Allocates capital to highest-scoring opportunities first
- Reports: total deployed, remaining capital, blended ROI, total expected profit

#### 10.3 Action Recommendations

| Score | Risk | Recommendation |
|-------|------|----------------|
| ≥80 | <40 | **EXECUTE NOW** |
| ≥70 | <60 | **INVESTIGATE** |
| ≥50 | <70 | **MONITOR** |
| <50 | any | **PASS** |

---

### 11. Database Design (PostgreSQL)

**7 core tables:**
- `countries` — Geography, currency, risk baselines
- `companies` — Full company profiles with spatial indexing
- `products` — With HS codes, pricing, logistics data
- `demand_signals` — Tenders, RFQs, project requirements
- `market_intel` — News, regulations, economic indicators
- `opportunities` — The central table: every discovered opportunity
- `daily_briefings` — Historical record of every briefing

**Materialized Views:**
- `mv_ranked_opportunities` — Always-updated ranking view
- `mv_market_summary` — Country-level opportunity aggregation

**Key design decisions:**
- PostgreSQL with `pg_trgm` for fuzzy company name matching
- PostGIS for geographic queries
- UUID primary keys (portability)
- Trigger-maintained `updated_at` and capital tier classification

---

### 12. Pipeline Orchestration

The pipeline runs in **6 phases**:

```
Phase 1: COLLECTION    →  Gather raw data from all sources
Phase 2: DETECTION     →  Run 14 detectors on collected data
Phase 3: PROFITABILITY →  Calculate costs, revenue, ROI
Phase 4: RISK          →  Assess 11 risk dimensions
Phase 5: SCORING       →  Score 0-100, assign tier, rank
Phase 6: BRIEFING      →  Generate daily briefing and recommendations
```

Each phase feeds the next. The pipeline can run:
- **On-demand**: `python main.py run`
- **Scheduled**: `python main.py schedule` (continuous mode)
- **Capital query**: `python main.py capital 100000`

---

### 13. Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Language | Python 3.12+ | Data ecosystem, async support |
| Database | PostgreSQL 15+ | Geospatial, fuzzy search |
| ORM | SQLAlchemy 2.0 | Mature, async support |
| Scheduling | APScheduler + asyncio | Lightweight, no external deps |
| Scraping | httpx + BeautifulSoup4 | Async HTTP, HTML parsing |
| Browser | Playwright | JavaScript-heavy sites |
| AI/LLM | Anthropic Claude API | Deep opportunity analysis |
| CLI | Rich + Typer | Beautiful terminal output |
| Config | YAML + Pydantic | Type-safe configuration |
| Logging | Loguru | Simple structured logging |

---

### 14. Target Geography

**Primary Sourcing Markets:**
Turkey (TR), Iraq (IQ), Syria (SY), Iran (IR), China (CN)

**Primary Demand Markets:**
Iraq (IQ), Syria (SY), Iran (IR), Saudi Arabia (SA), UAE (AE), Qatar (QA), Kuwait (KW), Oman (OM), Bahrain (BH)

**Secondary Markets:**
Germany (DE), United Kingdom (GB), Kazakhstan (KZ), Egypt (EG), Libya (LY), Algeria (DZ)

**Adding new countries** requires only:
1. Adding an entry to `config/settings.yaml`
2. Adding risk/currency/shipping baselines in the respective engines
3. Adding or registering a data collector for the country

---

### 15. Opportunity Types Detected

| Type | Description | Capital Required | Example |
|------|-------------|-----------------|---------|
| Trade Arbitrage | Buy low in source, sell high in target | Yes | Turkish steel → Iraq at 30% margin |
| Information Arbitrage | Know about demand before others | No | Early awareness of tender |
| Supply Gap | Demand exists, no local supply | Yes | Medical equipment in Syria |
| Demand Gap | Supply exists, no visible demand yet | Yes | Turkish products unknown in GCC |
| Inventory Liquidation | Seller distressed, below-market price | Yes | Factory overstock at 60% discount |
| Project Procurement | Large project needs materials | Yes | NEOM supplier registration |
| Tender Opportunity | Open tender matching capability | Bid bond | Iraq hospital equipment tender |
| Reconstruction | Post-conflict rebuilding | Yes | Aleppo housing reconstruction |
| Regional Shortage | Crisis-driven supply deficit | Yes | Generator shortage in Iraq summer |
| Emerging Demand | Trend detected early | Yes | Repeated RFQs for same product |
| Regulatory Change | New law creates window | Varies | Iraq lifts Turkish steel ban |
| Shipping Advantage | Faster/cheaper than competitors | Yes | Turkey→Iraq: 2 days vs 30 by sea |
| Supplier-Buyer Match | Direct connection | No | Match Chinese factory to Iraqi buyer |
| Brokerage | Commission on connecting parties | **$0** | 3% on $5M deal = $150K commission |

---

### 16. Key Differentiators

1. **Opportunity-first, not product-first** — The radar scans for gaps, not catalogs
2. **Multi-source intelligence fusion** — B2B + trade data + tenders + news + social
3. **Geography-optimized** — Designed for Turkey-Iraq-China-GCC corridor
4. **Capital-tier thinking** — Answers "What can I do with $X?" directly
5. **Risk-adjusted** — Every opportunity carries a composite risk score
6. **Forward-looking** — Detects emerging opportunities 3-24 months out
7. **Personal, not SaaS** — Zero user management, zero billing, pure intelligence
8. **Repeatable vs one-shot** — Distinguishes sustainable opportunities from windfalls

---

### 17. Deployment

```bash
# 1. Clone and install
cd oip
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with API keys and database credentials

# 3. Initialize database
psql -f database/schema.sql

# 4. Run
python main.py demo       # Demo with synthetic data
python main.py run        # Full pipeline
python main.py capital 100000  # Where to deploy $100K?
python main.py schedule   # Continuous mode
```

---

### 18. Roadmap

**Phase 1 (Current):** Core engines, demo data, CLI interface
**Phase 2:** Live collectors for top 10 data sources
**Phase 3:** LLM-powered deep opportunity analysis
**Phase 4:** Email/SMS alerting on critical opportunities
**Phase 5:** Automated execution workflows (document generation)
**Phase 6:** Counterparty network graph and relationship tracking

---

*OIP v1.0.0 — Personal Opportunity Intelligence System — June 2026*
