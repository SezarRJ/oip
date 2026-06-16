#!/usr/bin/env python3
"""
Opportunity Intelligence Platform (OIP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Personal-use AI-powered opportunity radar.
Discovers, evaluates, ranks, and monitors the highest-value
business opportunities across international markets.

Usage:
    python main.py run              Run full pipeline
    python main.py brief            Show latest briefing
    python main.py capital 50000    Where to deploy $50,000?
    python main.py top              Show top 10 opportunities
    python main.py schedule         Start scheduled continuous operation
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.orchestrator import OpportunityIntelligencePipeline
from engines.scoring.scorer import ScoringEngine


def print_banner():
    """Print the OIP banner."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║         OPPORTUNITY INTELLIGENCE PLATFORM (OIP)              ║
║         Personal AI-Powered Opportunity Radar                ║
║         v1.0.0  |  Solo Operator  |  Not SaaS               ║
╚══════════════════════════════════════════════════════════════╝
""")


def print_capital_response(response: dict):
    """Print the capital deployment recommendation."""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  CAPITAL DEPLOYMENT RECOMMENDATION                           ║
╠══════════════════════════════════════════════════════════════╣
║  Available Capital:      ${response['available_capital']:>12,.0f}
║  Recommended Allocation: ${response['recommended_allocation']:>12,.0f}
║  Remaining Capital:      ${response['remaining_capital']:>12,.0f}
║  Number of Deals:        {response['num_opportunities']:>12}
║  Total Expected Profit:  ${response['total_expected_profit']:>12,.0f}
║  Blended ROI:            {response['blended_roi']:>11.1f}%
╠══════════════════════════════════════════════════════════════╣
""")

    if response.get("recommendations"):
        for i, rec in enumerate(response["recommendations"], 1):
            print(f"""║  #{i} {rec['opportunity']['title'][:52]}
║     Score: {rec['score']:.0f}/100 | Tier: {rec['tier']} | Capital: ${rec['capital_required']:,.0f}
║     Profit: ${rec['expected_profit']:,.0f} | ROI: {rec['expected_roi']:.0f}% | Risk: {rec['risk_score']:.0f}/100
║""")

    print("╚══════════════════════════════════════════════════════════════╝\n")


async def main():
    print_banner()

    # Parse command
    args = sys.argv[1:] if len(sys.argv) > 1 else ["run"]

    command = args[0].lower() if args else "run"

    # ── Initialize Pipeline ──
    pipeline = OpportunityIntelligencePipeline()

    if command == "run":
        print("[OIP] Starting full pipeline...")
        print()

        result = await pipeline.run_full_pipeline()

        print()
        print(result.summary())

        if result.scored_opportunities:
            scored = result.scored_opportunities
            # Sort by score descending
            scored.sort(key=lambda x: x[3].final_score, reverse=True)

            print("\n📊 TOP OPPORTUNITIES\n")
            for i, (opp, profit, risk, score) in enumerate(scored[:10], 1):
                print(pipeline.print_opportunity_card(opp, profit, risk, score))

        if result.briefing:
            print("\n📋 DAILY BRIEFING\n")
            print(pipeline.decision_engine.format_briefing_text(result.briefing))

        print(f"\n[OIP] Pipeline complete. {result.summary()}")

    elif command == "capital":
        # User asks: "Where to deploy $X?"
        if len(args) < 2:
            print("Usage: python main.py capital <amount_usd>")
            print("Example: python main.py capital 50000")
            return

        try:
            amount = float(args[1])
        except ValueError:
            print(f"Invalid amount: {args[1]}")
            return

        print(f"[OIP] Calculating optimal deployment for ${amount:,.0f}...\n")

        # Run pipeline first
        result = await pipeline.run_full_pipeline()

        if result.scored_opportunities:
            # Build score map
            score_map = {}
            opp_list = []
            for opp, profitability, risk_assessment, score in result.scored_opportunities:
                opp_id = str(opp.title)
                score_map[opp_id] = score
                opp.expected_net_profit = profitability.expected_net_profit_usd
                opp.expected_roi_pct = profitability.expected_roi_pct
                opp.risk_score = risk_assessment.composite_risk_score
                opp.capital_required_usd = profitability.cost_breakdown.total_cost_usd
                opp_list.append(opp)

            response = pipeline.decision_engine.answer_capital_question(
                amount, opp_list, score_map
            )
            print_capital_response(response)
        else:
            print("[OIP] No opportunities detected. Try expanding data sources.")

    elif command == "top":
        print("[OIP] Running analysis for top opportunities...\n")
        result = await pipeline.run_full_pipeline()

        if result.scored_opportunities:
            scored = result.scored_opportunities
            scored.sort(key=lambda x: x[3].final_score, reverse=True)

            print(f"\nTOP 10 OPPORTUNITIES (out of {len(scored)})\n")
            for i, (opp, profit, risk, score) in enumerate(scored[:10], 1):
                print(pipeline.print_opportunity_card(opp, profit, risk, score))

    elif command == "brief":
        print("[OIP] Generating daily briefing...\n")
        result = await pipeline.run_full_pipeline()

        if result.briefing:
            print(pipeline.decision_engine.format_briefing_text(result.briefing))

    elif command == "schedule":
        print("[OIP] Starting scheduled operation mode...")
        print("[OIP] Pipeline will run on configured schedule.")
        print("[OIP] Press Ctrl+C to stop.\n")

        # Simple scheduling loop
        try:
            while True:
                print(f"\n{'='*60}")
                print(f"[OIP] Scheduled run at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                print(f"{'='*60}\n")

                result = await pipeline.run_full_pipeline()
                print(result.summary())

                if result.briefing:
                    top_rec = result.briefing.top_recommendation[:200]
                    print(f"\n📌 TOP: {top_rec}")

                # Wait for next cycle (demo: 30 seconds; production: hours)
                wait_seconds = 30
                print(f"\n[OIP] Next run in {wait_seconds}s...")
                await asyncio.sleep(wait_seconds)

        except KeyboardInterrupt:
            print("\n[OIP] Scheduled operation stopped.")

    elif command == "demo":
        print("[OIP] Running demonstration with synthetic data...\n")
        result = await pipeline.run_full_pipeline()

        print(result.summary())
        print()

        if result.scored_opportunities:
            scored = result.scored_opportunities
            scored.sort(key=lambda x: x[3].final_score, reverse=True)

            print("TOP OPPORTUNITIES (Demo Data):\n")
            for i, (opp, profit, risk, score) in enumerate(scored[:5], 1):
                print(pipeline.print_opportunity_card(opp, profit, risk, score))

        if result.briefing:
            print(pipeline.decision_engine.format_briefing_text(result.briefing))

    else:
        print(f"Unknown command: {command}")
        print()
        print("Available commands:")
        print("  run        Run full pipeline")
        print("  brief      Show daily briefing")
        print("  capital N  Where to deploy $N?")
        print("  top        Show top opportunities")
        print("  schedule   Start continuous scheduled operation")
        print("  demo       Run with synthetic demo data")
        print()
        print("Examples:")
        print("  python main.py run")
        print("  python main.py capital 100000")
        print("  python main.py top")


if __name__ == "__main__":
    asyncio.run(main())