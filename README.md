# Opportunity Intelligence Platform (OIP)

**Personal AI-Powered Opportunity Radar — Not SaaS. Single operator.**

```
╔══════════════════════════════════════════════════════════════╗
║         OPPORTUNITY INTELLIGENCE PLATFORM (OIP)              ║
║         Personal AI-Powered Opportunity Radar                ║
║         v1.0.0  |  Solo Operator  |  Not SaaS               ║
╚══════════════════════════════════════════════════════════════╝
```

## What It Does

OIP continuously discovers, evaluates, ranks, and monitors the highest-value business opportunities across international markets — **before they become obvious to competitors**.

It answers one question daily:

> *"If I had $X available today, where should I deploy it for the highest probability-adjusted profit?"*

## Quick Start

```bash
pip install -r requirements.txt
python main.py demo       # Demo with synthetic data
python main.py run        # Full pipeline
python main.py capital 100000  # Where to deploy $100K?
python main.py top        # Top 10 opportunities
python main.py brief      # Daily briefing
python main.py schedule   # Continuous radar mode
```

## Architecture

```
DATA COLLECTION → EXTRACTION → DETECTION → PROFITABILITY → RISK → SCORING → BRIEFING
      ↑                                                                        ↓
                          SCHEDULER / ORCHESTRATOR                              │
                                    ↓                                          ↓
                           POSTGRESQL DATABASE                          CLI OUTPUT
```

## Core Engines

| Engine | Function | Output |
|--------|----------|--------|
| **Detection** (14 detectors) | Find opportunities in raw data | DetectedOpportunity list |
| **Profitability** | Full cost model + ROI | ProfitabilityResult |
| **Risk** | 11-dimension risk assessment | RiskAssessment (0-100) |
| **Scoring** | 8-dimension weighted score | OpportunityScore (0-100) |
| **Decision** | Daily briefing + capital allocation | Actionable recommendations |

## Opportunity Types Detected

Trade Arbitrage · Information Arbitrage · Supply Gaps · Demand Gaps
Inventory Liquidation · Project Procurement · Tender Opportunities
Reconstruction · Regional Shortages · Emerging Demand
Regulatory Changes · Shipping Route Advantages · Supplier-Buyer Matches · Brokerage

## Target Geography

**Sourcing:** Turkey, Iraq, Syria, Iran, China
**Demand:** Iraq, Syria, Iran, Saudi Arabia, UAE, Qatar, Kuwait, Oman, Bahrain
**Secondary:** Europe, Central Asia, North Africa

## Key Files

```
oip/
├── main.py                          # Entry point & CLI
├── ARCHITECTURE.md                  # Full architecture document
├── config/settings.yaml             # Configuration
├── database/schema.sql              # PostgreSQL schema (10 tables, 2 views)
├── engines/
│   ├── opportunity_detection/detector.py   # 14 opportunity detectors
│   ├── profitability/calculator.py         # Cost, revenue, ROI engine
│   ├── risk/analyzer.py                    # 11-dimension risk engine
│   └── scoring/scorer.py                   # 0-100 composite scorer
├── ai/decision_engine.py            # Daily briefing & recommendations
├── pipeline/orchestrator.py         # 6-phase pipeline orchestrator
└── data_collection/collectors/      # Extensible collector framework
```

## Design Philosophy

- **Opportunity-first, not product-first** — the radar scans for gaps, not catalogs
- **Multi-source intelligence fusion** — B2B + trade data + tenders + news
- **Geography-optimized** — built for the Turkey-Iraq-China-GCC corridor
- **Capital-tier thinking** — answers "What can I do with $X?" directly
- **Risk-adjusted** — every opportunity has a composite risk score
- **Forward-looking** — detects emerging opportunities 3-24 months out
- **Personal tool** — no users, no billing, no SaaS complexity
