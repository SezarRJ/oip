"""
OIP - AI Decision Engine
Generates daily briefings, recommendations, and forward-looking analysis.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, date
from enum import Enum
import json


class RecommendationType(str, Enum):
    EXECUTE_NOW = "execute_now"
    INVESTIGATE = "investigate"
    MONITOR = "monitor"
    PASS = "pass"


@dataclass
class DailyBriefing:
    """The daily opportunity briefing."""
    briefing_date: date
    generated_at: datetime = field(default_factory=datetime.utcnow)

    # Top picks by capital tier
    top_zero_capital: List[Dict[str, Any]] = field(default_factory=list)
    top_under_10k: List[Dict[str, Any]] = field(default_factory=list)
    top_under_50k: List[Dict[str, Any]] = field(default_factory=list)
    top_under_100k: List[Dict[str, Any]] = field(default_factory=list)
    top_under_500k: List[Dict[str, Any]] = field(default_factory=list)
    top_under_1m: List[Dict[str, Any]] = field(default_factory=list)

    # Top picks by category
    top_brokerage: List[Dict[str, Any]] = field(default_factory=list)
    top_trading: List[Dict[str, Any]] = field(default_factory=list)
    top_low_risk: List[Dict[str, Any]] = field(default_factory=list)
    top_high_margin: List[Dict[str, Any]] = field(default_factory=list)
    top_repeatable: List[Dict[str, Any]] = field(default_factory=list)
    top_long_term: List[Dict[str, Any]] = field(default_factory=list)

    # Forward-looking
    emerging_3mo: List[Dict[str, Any]] = field(default_factory=list)
    emerging_6mo: List[Dict[str, Any]] = field(default_factory=list)
    emerging_12mo: List[Dict[str, Any]] = field(default_factory=list)
    emerging_24mo: List[Dict[str, Any]] = field(default_factory=list)

    # Stats
    total_opportunities: int = 0
    new_opportunities_24h: int = 0
    opportunities_executed: int = 0
    total_potential_profit: float = 0.0

    # Narrative
    executive_summary: str = ""
    market_commentary: str = ""
    top_recommendation: str = ""


class DecisionEngine:
    """
    Makes the final call on every opportunity.

    Answers the core question:
    "If I had $X available today, where should I deploy it?"

    Generates the daily briefing at 07:00 Baghdad time.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.briefing_time = self.config.get("daily_briefing_time", "07:00")
        self.briefing_tz = self.config.get("daily_briefing_timezone", "Asia/Baghdad")

    def generate_briefing(
        self,
        opportunities: List[Any],
        scores: Dict[str, Any],
        new_since: datetime = None,
    ) -> DailyBriefing:
        """
        Generate the complete daily briefing.
        """
        if new_since is None:
            new_since = datetime.utcnow() - timedelta(hours=24)

        briefing = DailyBriefing(briefing_date=date.today())

        # Pair opportunities with their scores
        scored_opps = self._pair_with_scores(opportunities, scores)

        # Sort by score descending
        scored_opps.sort(key=lambda x: x[1].final_score if x[1] else 0, reverse=True)

        # ── Top by Capital Tier ──
        briefing.top_zero_capital = self._top_by_capital(scored_opps, 0, 0, limit=5)
        briefing.top_under_10k = self._top_by_capital(scored_opps, 1, 10000, limit=5)
        briefing.top_under_50k = self._top_by_capital(scored_opps, 10001, 50000, limit=5)
        briefing.top_under_100k = self._top_by_capital(scored_opps, 50001, 100000, limit=5)
        briefing.top_under_500k = self._top_by_capital(scored_opps, 100001, 500000, limit=5)
        briefing.top_under_1m = self._top_by_capital(scored_opps, 500001, 1000000, limit=5)

        # ── Top by Category ──
        briefing.top_brokerage = self._top_by_type(scored_opps, ["brokerage"], limit=5)
        briefing.top_trading = self._top_by_type(
            scored_opps, ["trade_arbitrage", "supply_gap", "demand_gap"], limit=5
        )
        briefing.top_low_risk = self._top_by_risk(scored_opps, max_risk=30, limit=5)
        briefing.top_high_margin = self._top_by_roi(scored_opps, min_roi=50, limit=5)
        briefing.top_repeatable = self._top_repeatable(scored_opps, limit=5)
        briefing.top_long_term = self._top_long_term(scored_opps, limit=5)

        # ── Forward-looking ──
        briefing.emerging_3mo = self._emerging_opportunities(scored_opps, months=3, limit=5)
        briefing.emerging_6mo = self._emerging_opportunities(scored_opps, months=6, limit=5)
        briefing.emerging_12mo = self._emerging_opportunities(scored_opps, months=12, limit=5)
        briefing.emerging_24mo = self._emerging_opportunities(scored_opps, months=24, limit=5)

        # ── Stats ──
        briefing.total_opportunities = len(scored_opps)
        briefing.new_opportunities_24h = sum(
            1 for opp, _ in scored_opps
            if hasattr(opp, "discovered_at") and opp.discovered_at and opp.discovered_at >= new_since
        )
        briefing.total_potential_profit = sum(
            getattr(opp, "expected_net_profit", 0) or 0
            for opp, _ in scored_opps
        )

        # ── Narrative ──
        briefing.executive_summary = self._generate_executive_summary(briefing)
        briefing.market_commentary = self._generate_market_commentary(scored_opps)
        briefing.top_recommendation = self._generate_top_recommendation(briefing)

        return briefing

    def answer_capital_question(
        self,
        available_capital: float,
        opportunities: List[Any],
        scores: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Answer: "If I had $X today, where should I deploy it?"
        """
        scored = self._pair_with_scores(opportunities, scores)

        # Filter by capital requirement
        affordable = [
            (opp, s) for opp, s in scored
            if self._get_capital(opp) <= available_capital
        ]

        # Sort by score
        affordable.sort(key=lambda x: x[1].final_score if x[1] else 0, reverse=True)

        # Build portfolio recommendation
        top_picks = affordable[:5]

        total_allocated = 0
        recommendations = []

        for opp, score in top_picks:
            capital = self._get_capital(opp)
            if total_allocated + capital <= available_capital * 1.1:  # 10% buffer
                total_allocated += capital
                recommendations.append({
                    "opportunity": self._serialize_opp(opp),
                    "score": score.final_score if score else 0,
                    "tier": score.tier if score else "C",
                    "capital_required": capital,
                    "expected_profit": getattr(opp, "expected_net_profit", 0) or 0,
                    "expected_roi": getattr(opp, "expected_roi_pct", 0) or 0,
                    "risk_score": getattr(opp, "risk_score", 50) or 50,
                })

        remaining = available_capital - total_allocated

        return {
            "available_capital": available_capital,
            "recommended_allocation": total_allocated,
            "remaining_capital": remaining,
            "num_opportunities": len(recommendations),
            "total_expected_profit": sum(r["expected_profit"] for r in recommendations),
            "blended_roi": (
                sum(r["expected_profit"] for r in recommendations) / total_allocated * 100
                if total_allocated > 0 else 0
            ),
            "recommendations": recommendations,
        }

    def recommend_action(
        self,
        opportunity: Any,
        score: Any,
        risk_assessment: Any,
    ) -> Tuple[RecommendationType, str]:
        """
        Recommend what to do with a specific opportunity.
        """
        final_score = score.final_score if score else 0
        risk = risk_assessment.composite_risk_score if risk_assessment else 50

        if final_score >= 80 and risk < 40:
            return RecommendationType.EXECUTE_NOW, (
                "High score, low risk. Execute immediately. "
                "Contact counterparties, negotiate terms, prepare documentation."
            )
        elif final_score >= 70 and risk < 60:
            return RecommendationType.INVESTIGATE, (
                "Strong opportunity. Verify key details with counterparties, "
                "confirm pricing, check logistics availability."
            )
        elif final_score >= 50:
            return RecommendationType.MONITOR, (
                "Monitor for improved conditions. Set up alerts for price changes, "
                "new demand signals, or reduced risk factors."
            )
        else:
            return RecommendationType.PASS, (
                "Below threshold. Archive and revisit only if conditions change significantly."
            )

    # ── Private helpers ──

    def _pair_with_scores(self, opportunities, scores):
        """Pair each opportunity with its score."""
        result = []
        for opp in opportunities:
            opp_id = getattr(opp, "id", str(opp))
            score = scores.get(opp_id) if isinstance(scores, dict) else None
            result.append((opp, score))
        return result

    def _get_capital(self, opp) -> float:
        """Extract capital requirement from an opportunity."""
        if hasattr(opp, "capital_required_usd"):
            return opp.capital_required_usd or 0
        if hasattr(opp, "capital_required_estimate"):
            return opp.capital_required_estimate or 0
        return 0

    def _serialize_opp(self, opp) -> Dict[str, Any]:
        """Convert opportunity to serializable dict."""
        if hasattr(opp, "to_dict"):
            return opp.to_dict()
        result = {
            "title": getattr(opp, "title", ""),
            "description": getattr(opp, "description", ""),
            "source_country": getattr(opp, "source_country", ""),
            "target_country": getattr(opp, "target_country", ""),
            "product_category": getattr(opp, "product_category", ""),
            "why_exists": getattr(opp, "why_exists", ""),
        }
        if hasattr(opp, "opportunity_type"):
            ot = opp.opportunity_type
            result["opportunity_type"] = ot.value if hasattr(ot, "value") else str(ot)
        return result

    def _top_by_capital(self, scored, min_cap, max_cap, limit=5):
        """Top opportunities in a capital range."""
        filtered = [
            (opp, s) for opp, s in scored
            if min_cap <= self._get_capital(opp) <= max_cap
        ]
        filtered.sort(key=lambda x: x[1].final_score if x[1] else 0, reverse=True)
        return [self._format_opp_entry(opp, s) for opp, s in filtered[:limit]]

    def _top_by_type(self, scored, types, limit=5):
        """Top opportunities of specific types."""
        filtered = [
            (opp, s) for opp, s in scored
            if self._get_opp_type(opp) in types
        ]
        filtered.sort(key=lambda x: x[1].final_score if x[1] else 0, reverse=True)
        return [self._format_opp_entry(opp, s) for opp, s in filtered[:limit]]

    def _top_by_risk(self, scored, max_risk, limit=5):
        """Top low-risk opportunities."""
        filtered = [
            (opp, s) for opp, s in scored
            if (getattr(opp, "risk_score", 50) or 50) <= max_risk
        ]
        filtered.sort(key=lambda x: x[1].final_score if x[1] else 0, reverse=True)
        return [self._format_opp_entry(opp, s) for opp, s in filtered[:limit]]

    def _top_by_roi(self, scored, min_roi, limit=5):
        """Top high-margin opportunities."""
        filtered = [
            (opp, s) for opp, s in scored
            if (getattr(opp, "expected_roi_pct", 0) or 0) >= min_roi
        ]
        filtered.sort(key=lambda x: x[1].final_score if x[1] else 0, reverse=True)
        return [self._format_opp_entry(opp, s) for opp, s in filtered[:limit]]

    def _top_repeatable(self, scored, limit=5):
        """Top repeatable opportunities."""
        filtered = [
            (opp, s) for opp, s in scored
            if getattr(opp, "is_repeatable", False)
        ]
        filtered.sort(key=lambda x: x[1].final_score if x[1] else 0, reverse=True)
        return [self._format_opp_entry(opp, s) for opp, s in filtered[:limit]]

    def _top_long_term(self, scored, limit=5):
        """Top long-term (strategic) opportunities."""
        long_term_types = {"reconstruction", "project_procurement", "emerging_demand"}
        filtered = [
            (opp, s) for opp, s in scored
            if self._get_opp_type(opp) in long_term_types
        ]
        filtered.sort(key=lambda x: x[1].final_score if x[1] else 0, reverse=True)
        return [self._format_opp_entry(opp, s) for opp, s in filtered[:limit]]

    def _emerging_opportunities(self, scored, months, limit=5):
        """Opportunities expected to emerge in N months."""
        # These are opportunities with lower current scores but strong
        # underlying trends suggesting they'll improve
        filtered = [
            (opp, s) for opp, s in scored
            if s and 30 <= s.final_score < 55
        ]
        # Sort by potential (uses market demand and supply constraint as leading indicators)
        filtered.sort(
            key=lambda x: (
                (getattr(x[1].components, "market_demand_score", 0) +
                 getattr(x[1].components, "supply_constraint_score", 0)) / 2
            ),
            reverse=True,
        )
        return [self._format_opp_entry(opp, s) for opp, s in filtered[:limit]]

    def _get_opp_type(self, opp) -> str:
        """Extract opportunity type as string."""
        ot = getattr(opp, "opportunity_type", None)
        if ot is None:
            return "unknown"
        return ot.value if hasattr(ot, "value") else str(ot)

    def _format_opp_entry(self, opp, score) -> Dict[str, Any]:
        """Format an opportunity for the briefing."""
        return {
            "title": getattr(opp, "title", ""),
            "type": self._get_opp_type(opp),
            "source_country": getattr(opp, "source_country", ""),
            "target_country": getattr(opp, "target_country", ""),
            "product_category": getattr(opp, "product_category", ""),
            "capital_required": self._get_capital(opp),
            "expected_profit": getattr(opp, "expected_net_profit", 0) or 0,
            "expected_roi": getattr(opp, "expected_roi_pct", 0) or 0,
            "risk_score": getattr(opp, "risk_score", 50) or 50,
            "opportunity_score": score.final_score if score else 0,
            "tier": score.tier if score else "C",
            "why_exists": getattr(opp, "why_exists", ""),
            "is_repeatable": getattr(opp, "is_repeatable", False),
        }

    def _generate_executive_summary(self, briefing: DailyBriefing) -> str:
        """Generate an executive summary of the briefing."""
        return (
            f"OIP Daily Briefing — {briefing.briefing_date}\n"
            f"──────────────────────────────────────────\n"
            f"Total Active Opportunities: {briefing.total_opportunities}\n"
            f"New in Last 24h: {briefing.new_opportunities_24h}\n"
            f"Total Potential Profit: ${briefing.total_potential_profit:,.0f}\n\n"
            f"Top Zero-Capital: {briefing.top_zero_capital[0]['title'] if briefing.top_zero_capital else 'None'}\n"
            f"Top Under $10k: {briefing.top_under_10k[0]['title'] if briefing.top_under_10k else 'None'}\n"
            f"Top Under $50k: {briefing.top_under_50k[0]['title'] if briefing.top_under_50k else 'None'}\n"
            f"Top Under $100k: {briefing.top_under_100k[0]['title'] if briefing.top_under_100k else 'None'}\n"
        )

    def _generate_market_commentary(self, scored) -> str:
        """Generate market commentary."""
        if not scored:
            return "No opportunities in the pipeline. Consider expanding data sources."

        high_score = sum(1 for _, s in scored if s and s.final_score >= 70)
        total = len(scored)

        return (
            f"Market Commentary:\n"
            f"  • {high_score}/{total} opportunities score 70+ (Tier A/S)\n"
            f"  • Most active corridor: [to be determined from data]\n"
            f"  • Most active category: [to be determined from data]\n"
        )

    def _generate_top_recommendation(self, briefing: DailyBriefing) -> str:
        """Generate the single top recommendation."""
        all_top = (
            briefing.top_under_10k +
            briefing.top_under_50k +
            briefing.top_under_100k +
            briefing.top_under_500k
        )

        if not all_top:
            return "No actionable opportunities at this time."

        best = max(all_top, key=lambda x: x["opportunity_score"])
        return (
            f"TOP RECOMMENDATION: {best['title']}\n"
            f"  Type: {best['type']}\n"
            f"  Capital Required: ${best['capital_required']:,.0f}\n"
            f"  Expected Profit: ${best['expected_profit']:,.0f}\n"
            f"  Expected ROI: {best['expected_roi']:.0f}%\n"
            f"  Risk Score: {best['risk_score']:.0f}/100\n"
            f"  Opportunity Score: {best['opportunity_score']:.0f}/100 (Tier {best['tier']})\n"
            f"  Why: {best['why_exists']}"
        )

    def format_briefing_text(self, briefing: DailyBriefing) -> str:
        """Format the entire briefing as a readable text report."""
        sections = []

        # Header
        sections.append("=" * 70)
        sections.append("   OPPORTUNITY INTELLIGENCE PLATFORM — DAILY BRIEFING")
        sections.append(f"   Date: {briefing.briefing_date}")
        sections.append("=" * 70)
        sections.append("")

        # Executive Summary
        sections.append(briefing.executive_summary)
        sections.append("")

        # Top Recommendation
        sections.append(briefing.top_recommendation)
        sections.append("")
        sections.append("-" * 70)

        # By Capital Tier
        sections.append("\n📊 BY CAPITAL TIER\n")

        tiers = [
            ("Zero Capital", briefing.top_zero_capital),
            ("Under $10,000", briefing.top_under_10k),
            ("Under $50,000", briefing.top_under_50k),
            ("Under $100,000", briefing.top_under_100k),
            ("Under $500,000", briefing.top_under_500k),
            ("Under $1,000,000", briefing.top_under_1m),
        ]

        for name, opps in tiers:
            sections.append(f"\n  {name}:")
            if opps:
                for o in opps[:3]:
                    sections.append(
                        f"    • {o['title'][:60]} "
                        f"[Score: {o['opportunity_score']:.0f}, "
                        f"ROI: {o['expected_roi']:.0f}%, "
                        f"Risk: {o['risk_score']:.0f}]"
                    )
            else:
                sections.append("    (none)")

        # By Category
        sections.append("\n\n📂 BY CATEGORY\n")
        categories = [
            ("Brokerage", briefing.top_brokerage),
            ("Trading", briefing.top_trading),
            ("Low Risk", briefing.top_low_risk),
            ("High Margin", briefing.top_high_margin),
            ("Repeatable", briefing.top_repeatable),
            ("Long-Term", briefing.top_long_term),
        ]

        for name, opps in categories:
            if opps:
                sections.append(f"  {name}: {opps[0]['title'][:60]} "
                              f"[Score: {opps[0]['opportunity_score']:.0f}]")

        # Forward-looking
        sections.append("\n\n🔮 FORWARD-LOOKING\n")
        horizons = [
            ("3 Months", briefing.emerging_3mo),
            ("6 Months", briefing.emerging_6mo),
            ("12 Months", briefing.emerging_12mo),
            ("24 Months", briefing.emerging_24mo),
        ]
        for horizon, opps in horizons:
            if opps:
                sections.append(f"  {horizon}: {opps[0]['title'][:60]}")

        sections.append("\n" + "=" * 70)
        sections.append("END OF BRIEFING")
        sections.append("=" * 70)

        return "\n".join(sections)


class AIDecisionEngine(DecisionEngine):
    """
    Enhanced decision engine that can use LLM APIs for deeper analysis.
    Falls back to rule-based logic when API is unavailable.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.llm_enabled = False
        self._init_llm()

    def _init_llm(self):
        """Try to initialize LLM client."""
        try:
            import anthropic
            import os
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                self.llm_client = anthropic.Anthropic(api_key=api_key)
                self.llm_enabled = True
        except ImportError:
            pass

    async def analyze_opportunity_deep(
        self, opportunity: Any, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to provide deep qualitative analysis of an opportunity.
        Falls back to rule-based if LLM unavailable.
        """
        if not self.llm_enabled:
            return self._rule_based_deep_analysis(opportunity, context)

        # Build prompt
        prompt = self._build_analysis_prompt(opportunity, context)

        try:
            response = self.llm_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            return self._parse_llm_response(response.content[0].text)
        except Exception:
            return self._rule_based_deep_analysis(opportunity, context)

    def _build_analysis_prompt(self, opportunity, context) -> str:
        """Build the analysis prompt for the LLM."""
        return f"""You are an expert international trade analyst and opportunity evaluator.

Analyze this opportunity:

Title: {getattr(opportunity, 'title', 'Unknown')}
Type: {self._get_opp_type(opportunity)}
Source Market: {getattr(opportunity, 'source_country', '')}
Target Market: {getattr(opportunity, 'target_country', '')}
Product: {getattr(opportunity, 'product_category', '')}
Why It Exists: {getattr(opportunity, 'why_exists', '')}

Context:
{json.dumps(context, indent=2, default=str)}

Provide:
1. Why this opportunity exists (deeper analysis)
2. Why competitors haven't fully exploited it
3. How long the window may remain open
4. Key risks specific to this opportunity
5. What is required to capture it successfully
6. Whether it is repeatable
7. Recommended first 3 actions

Be specific and actionable. Focus on the Iraq-Turkey-China-GCC corridor."""

    def _parse_llm_response(self, text: str) -> Dict[str, Any]:
        """Parse LLM response into structured analysis."""
        # Simple extraction — in production, use structured output
        return {
            "deep_analysis": text,
            "why_exists": "",
            "competitor_analysis": "",
            "window_estimate": "",
            "key_risks": [],
            "requirements": "",
            "is_repeatable": "repeatable" in text.lower() and "not repeatable" not in text.lower(),
            "recommended_actions": [],
        }

    def _rule_based_deep_analysis(
        self, opportunity, context
    ) -> Dict[str, Any]:
        """Rule-based fallback analysis."""
        return {
            "deep_analysis": f"Rule-based analysis of {getattr(opportunity, 'title', 'opportunity')}",
            "why_exists": getattr(opportunity, "why_exists", ""),
            "competitor_analysis": "Information asymmetry — most market participants lack this data",
            "window_estimate": "3-6 months typical for this opportunity type",
            "key_risks": ["Counterparty verification", "Currency fluctuation", "Logistics execution"],
            "requirements": "Due diligence, supplier verification, logistics arrangement",
            "is_repeatable": getattr(opportunity, "is_repeatable", False),
            "recommended_actions": [
                "Verify supplier/buyer details",
                "Confirm pricing and availability",
                "Negotiate terms and payment method",
            ],
        }