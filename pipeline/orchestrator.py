"""
OIP - Pipeline Orchestrator
Coordinates the entire opportunity intelligence pipeline:
Collect → Extract → Detect → Analyze → Score → Brief
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import asyncio
import json

from engines.opportunity_detection.detector import (
    OpportunityDetectionEngine, DetectedOpportunity, OpportunityType
)
from engines.profitability.calculator import ProfitabilityEngine, ProfitabilityResult
from engines.risk.analyzer import RiskEngine, RiskAssessment
from engines.scoring.scorer import ScoringEngine, OpportunityScore
from ai.decision_engine import DecisionEngine, DailyBriefing, RecommendationType


@dataclass
class PipelineResult:
    """Complete result of one pipeline run."""
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Collection phase
    companies_collected: int = 0
    products_collected: int = 0
    demand_signals_collected: int = 0
    market_intel_collected: int = 0

    # Detection phase
    opportunities_detected: int = 0
    new_opportunities: int = 0
    detection_errors: List[str] = field(default_factory=list)

    # Analysis phase
    opportunities_analyzed: int = 0
    analysis_errors: List[str] = field(default_factory=list)

    # Scored opportunities
    scored_opportunities: List[Tuple[DetectedOpportunity, ProfitabilityResult, RiskAssessment, OpportunityScore]] = field(default_factory=list)

    # Briefing
    briefing: Optional[DailyBriefing] = None

    # Errors
    errors: List[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0

    def summary(self) -> str:
        """One-line summary of the pipeline run."""
        return (
            f"Pipeline completed in {self.duration_seconds:.1f}s | "
            f"Collected: {self.companies_collected}C/{self.products_collected}P/"
            f"{self.demand_signals_collected}D/{self.market_intel_collected}I | "
            f"Detected: {self.opportunities_detected} opportunities | "
            f"New: {self.new_opportunities} | "
            f"Scored: {self.opportunities_analyzed}"
        )


class OpportunityIntelligencePipeline:
    """
    The complete OIP pipeline.

    Runs continuously or on-demand, orchestrating:
    1. Data Collection
    2. Data Extraction
    3. Opportunity Detection
    4. Profitability Analysis
    5. Risk Assessment
    6. Scoring & Ranking
    7. Briefing Generation
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Initialize engines
        self.detection_engine = OpportunityDetectionEngine(config)
        self.profitability_engine = ProfitabilityEngine(config)
        self.risk_engine = RiskEngine(config)
        self.scoring_engine = ScoringEngine(config)
        self.decision_engine = DecisionEngine(config)

        # State
        self.previous_opportunity_ids: set = set()
        self.collectors: List[Any] = []
        self.running = False

    def register_collector(self, collector):
        """Register a data collector."""
        self.collectors.append(collector)

    async def run_collection_phase(self) -> Tuple[List, List, List, List]:
        """
        Phase 1: Collect data from all registered sources.
        Returns: companies, products, demand_signals, market_intel
        """
        all_companies = []
        all_products = []
        all_demand = []
        all_intel = []

        # Run collectors concurrently
        tasks = []
        for collector in self.collectors:
            if hasattr(collector, 'can_collect') and not collector.can_collect():
                continue
            tasks.append(collector.collect())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                import logging; logger = logging.getLogger("OIP")
                logger.error(f"Collector failed: {result}")
                continue

            all_companies.extend(result.companies)
            all_products.extend(result.products)
            all_demand.extend(result.demand_signals)
            all_intel.extend(result.market_intel)

        return all_companies, all_products, all_demand, all_intel

    def run_detection_phase(
        self,
        companies: List[Dict],
        products: List[Dict],
        demand_signals: List[Dict],
        market_intel: List[Dict],
    ) -> List[DetectedOpportunity]:
        """
        Phase 2: Detect opportunities from collected data.
        """
        opportunities = self.detection_engine.run_all_detectors(
            companies, products, demand_signals, market_intel
        )
        return opportunities

    def run_analysis_phase(
        self,
        opportunities: List[DetectedOpportunity],
    ) -> List[Tuple[DetectedOpportunity, ProfitabilityResult, RiskAssessment]]:
        """
        Phase 3-4: Analyze profitability and risk for each opportunity.
        """
        analyzed = []

        for opp in opportunities:
            try:
                # ── Profitability ──
                purchase_cost = opp.capital_required_estimate * 0.7  # Estimate purchase as 70% of capital
                is_brokerage = opp.opportunity_type == OpportunityType.BROKERAGE

                profitability = self.profitability_engine.calculate(
                    purchase_cost_usd=purchase_cost,
                    source_country=opp.source_country,
                    target_country=opp.target_country,
                    commission_based=is_brokerage,
                    deal_size_usd=(opp.buyers_found[0].get('estimated_budget_usd', opp.capital_required_estimate) if opp.buyers_found else opp.capital_required_estimate) if is_brokerage else None,
                )

                # ── Risk Assessment ──
                supplier_data = opp.suppliers_found[0] if opp.suppliers_found else None
                buyer_data = opp.buyers_found[0] if opp.buyers_found else None

                risk_assessment = self.risk_engine.assess(
                    source_country=opp.source_country,
                    target_country=opp.target_country,
                    supplier_data=supplier_data,
                    buyer_data=buyer_data,
                    opportunity_type=opp.opportunity_type.value,
                )

                analyzed.append((opp, profitability, risk_assessment))

            except Exception as e:
                import logging; logger = logging.getLogger("OIP")
                logger.error(f"Analysis failed for {opp.title}: {e}")

        return analyzed

    def run_scoring_phase(
        self,
        analyzed: List[Tuple[DetectedOpportunity, ProfitabilityResult, RiskAssessment]],
    ) -> List[Tuple[DetectedOpportunity, ProfitabilityResult, RiskAssessment, OpportunityScore]]:
        """
        Phase 5: Score and rank all opportunities.
        """
        scored = []

        for opp, profitability, risk_assessment in analyzed:
            try:
                score = self.scoring_engine.score(
                    expected_net_profit=profitability.expected_net_profit_usd,
                    expected_roi_pct=profitability.expected_roi_pct,
                    probability_of_success=opp.confidence,
                    capital_required=profitability.cost_breakdown.total_cost_usd,
                    risk_score=risk_assessment.composite_risk_score,
                    cash_conversion_days=profitability.cash_conversion_cycle_days,
                    is_repeatable=opp.is_repeatable,
                    opportunity_type=opp.opportunity_type.value,
                )

                # Update opportunity with financial data
                opp.capital_required_estimate = profitability.cost_breakdown.total_cost_usd

                scored.append((opp, profitability, risk_assessment, score))

            except Exception as e:
                import logging; logger = logging.getLogger("OIP")
                logger.error(f"Scoring failed for {opp.title}: {e}")

        return scored

    def run_briefing_phase(
        self,
        scored: List[Tuple[DetectedOpportunity, ProfitabilityResult, RiskAssessment, OpportunityScore]],
    ) -> DailyBriefing:
        """
        Phase 6: Generate the daily briefing.
        """
        # Build score map
        score_map = {}
        opportunity_list = []

        for opp, profitability, risk_assessment, score in scored:
            opp_id = getattr(opp, 'title', str(opp))
            score_map[opp_id] = score

            # Attach financial data to opportunity for briefing
            opp.expected_net_profit = profitability.expected_net_profit_usd
            opp.expected_roi_pct = profitability.expected_roi_pct
            opp.risk_score = risk_assessment.composite_risk_score
            opp.capital_required_usd = profitability.cost_breakdown.total_cost_usd

            opportunity_list.append(opp)

        # Count new opportunities
        current_ids = set()
        for opp in opportunity_list:
            opp_id = getattr(opp, 'title', str(opp))
            current_ids.add(opp_id)

        new_count = len(current_ids - self.previous_opportunity_ids)
        self.previous_opportunity_ids = current_ids

        # Generate briefing
        briefing = self.decision_engine.generate_briefing(
            opportunities=opportunity_list,
            scores=score_map,
        )

        briefing.new_opportunities_24h = new_count

        return briefing

    async def run_full_pipeline(self) -> PipelineResult:
        """
        Run the complete OIP pipeline end-to-end.
        """
        result = PipelineResult()
        self.running = True

        try:
            # ── Phase 1: Collection ──
            import logging; logger = logging.getLogger("OIP")
            logger.info("Phase 1: Data Collection starting...")
            phase1_start = datetime.utcnow()

            if self.collectors:
                companies, products, demand, intel = await self.run_collection_phase()
            else:
                # Demo mode — generate synthetic data for testing
                companies, products, demand, intel = self._generate_demo_data()

            result.companies_collected = len(companies)
            result.products_collected = len(products)
            result.demand_signals_collected = len(demand)
            result.market_intel_collected = len(intel)

            logger.info(
                f"Phase 1 complete in {(datetime.utcnow() - phase1_start).total_seconds():.1f}s. "
                f"Collected: {result.companies_collected}C/{result.products_collected}P/"
                f"{result.demand_signals_collected}D/{result.market_intel_collected}I"
            )

            # ── Phase 2: Detection ──
            logger.info("Phase 2: Opportunity Detection starting...")
            phase2_start = datetime.utcnow()

            opportunities = self.run_detection_phase(companies, products, demand, intel)

            result.opportunities_detected = len(opportunities)
            logger.info(
                f"Phase 2 complete in {(datetime.utcnow() - phase2_start).total_seconds():.1f}s. "
                f"Detected: {result.opportunities_detected} opportunities"
            )

            # ── Phase 3-4: Analysis ──
            logger.info("Phase 3-4: Profitability & Risk Analysis starting...")
            phase3_start = datetime.utcnow()

            analyzed = self.run_analysis_phase(opportunities)

            result.opportunities_analyzed = len(analyzed)
            logger.info(
                f"Phase 3-4 complete in {(datetime.utcnow() - phase3_start).total_seconds():.1f}s. "
                f"Analyzed: {len(analyzed)} opportunities"
            )

            # ── Phase 5: Scoring ──
            logger.info("Phase 5: Scoring & Ranking starting...")
            phase5_start = datetime.utcnow()

            scored = self.run_scoring_phase(analyzed)
            result.scored_opportunities = scored

            logger.info(
                f"Phase 5 complete in {(datetime.utcnow() - phase5_start).total_seconds():.1f}s. "
                f"Scored: {len(scored)} opportunities"
            )

            # ── Phase 6: Briefing ──
            logger.info("Phase 6: Briefing Generation starting...")
            phase6_start = datetime.utcnow()

            briefing = self.run_briefing_phase(scored)
            result.briefing = briefing

            logger.info(
                f"Phase 6 complete in {(datetime.utcnow() - phase6_start).total_seconds():.1f}s."
            )

            result.completed_at = datetime.utcnow()

        except Exception as e:
            import logging; logger = logging.getLogger("OIP")
            logger.error(f"Pipeline failed: {e}")
            result.errors.append(str(e))
            result.completed_at = datetime.utcnow()

        finally:
            self.running = False

        return result

    def answer_capital_question(
        self, available_capital: float
    ) -> Dict[str, Any]:
        """
        Answer: "Where should I deploy $X today?"
        Requires pipeline to have been run first.
        """
        if not hasattr(self, '_last_opportunities') or not self._last_opportunities:
            return {"error": "No pipeline data available. Run pipeline first."}

        return self.decision_engine.answer_capital_question(
            available_capital=available_capital,
            opportunities=self._last_opportunities,
            scores=self._last_scores or {},
        )

    def _generate_demo_data(self) -> Tuple[List, List, List, List]:
        """
        Generate synthetic demo data for testing the pipeline.
        This allows the system to demonstrate capability without live collectors.
        """
        companies = [
            {
                "name": "Ankara Steel Industries",
                "country_code": "TR",
                "city": "Ankara",
                "company_type": "manufacturer",
                "verified": True,
                "reliability_score": 8.5,
                "years_in_business": 15,
                "certifications": ["ISO 9001", "CE"],
                "email": "export@ankarasteel.com.tr",
                "phone": "+90 312 555 0190",
            },
            {
                "name": "Istanbul Textile Group",
                "country_code": "TR",
                "city": "Istanbul",
                "company_type": "manufacturer",
                "verified": True,
                "reliability_score": 8.0,
                "years_in_business": 22,
                "certifications": ["ISO 9001", "OEKO-TEX"],
                "email": "sales@istanbultextile.com.tr",
                "phone": "+90 212 444 0155",
            },
            {
                "name": "Guangzhou Electronics Co",
                "country_code": "CN",
                "city": "Guangzhou",
                "company_type": "manufacturer",
                "verified": False,
                "reliability_score": 6.0,
                "years_in_business": 8,
                "certifications": ["ISO 9001"],
                "email": "export@gz-electronics.cn",
            },
            {
                "name": "Baghdad Building Materials LLC",
                "country_code": "IQ",
                "city": "Baghdad",
                "company_type": "distributor",
                "verified": False,
                "reliability_score": 5.5,
                "years_in_business": 4,
                "certifications": [],
                "phone": "+964 780 123 4567",
            },
            {
                "name": "Dubai Trading House",
                "country_code": "AE",
                "city": "Dubai",
                "company_type": "trader",
                "verified": True,
                "reliability_score": 7.5,
                "years_in_business": 12,
                "certifications": ["ISO 9001"],
                "email": "trade@dubaitrading.ae",
            },
        ]

        products = [
            {
                "name": "Steel Rebar 12mm",
                "category": "construction_materials",
                "hs_code": "72142000",
                "unit_price_usd": 580,
                "moq": 50,
                "unit": "ton",
                "origin_country": "TR",
                "company_name": "Ankara Steel Industries",
                "lead_time_days": 14,
                "weight_kg": 1000,
            },
            {
                "name": "Steel Rebar 12mm",
                "category": "construction_materials",
                "hs_code": "72142000",
                "unit_price_usd": 520,
                "moq": 100,
                "unit": "ton",
                "origin_country": "CN",
                "company_name": "Unnamed Chinese Supplier",
                "lead_time_days": 35,
                "weight_kg": 1000,
            },
            {
                "name": "Medical Scrubs",
                "category": "medical",
                "hs_code": "62114300",
                "unit_price_usd": 8.50,
                "moq": 500,
                "unit": "piece",
                "origin_country": "TR",
                "company_name": "Istanbul Textile Group",
                "lead_time_days": 10,
                "weight_kg": 0.3,
            },
            {
                "name": "Medical Scrubs",
                "category": "medical",
                "hs_code": "62114300",
                "unit_price_usd": 4.20,
                "moq": 1000,
                "unit": "piece",
                "origin_country": "CN",
                "company_name": "Unnamed Chinese Supplier",
                "lead_time_days": 30,
                "weight_kg": 0.3,
            },
            {
                "name": "Cement Portland 42.5",
                "category": "construction_materials",
                "hs_code": "25232900",
                "unit_price_usd": 85,
                "moq": 100,
                "unit": "ton",
                "origin_country": "TR",
                "company_name": "Turkish Cement Co",
                "lead_time_days": 5,
                "weight_kg": 1000,
            },
            {
                "name": "LED Light Fixtures",
                "category": "electrical",
                "hs_code": "94054090",
                "unit_price_usd": 22.00,
                "moq": 200,
                "unit": "piece",
                "origin_country": "CN",
                "company_name": "Guangzhou Electronics Co",
                "lead_time_days": 25,
                "weight_kg": 2.0,
            },
            {
                "name": "Ceramic Floor Tiles 60x60",
                "category": "construction_materials",
                "hs_code": "69072100",
                "unit_price_usd": 6.50,
                "moq": 500,
                "unit": "sqm",
                "origin_country": "TR",
                "company_name": "Turkish Ceramics Inc",
                "lead_time_days": 14,
                "weight_kg": 22,
            },
            {
                "name": "Generator Diesel 100kVA",
                "category": "power_generation",
                "hs_code": "85021100",
                "unit_price_usd": 8500,
                "moq": 1,
                "unit": "unit",
                "origin_country": "CN",
                "company_name": "Guangzhou Electronics Co",
                "lead_time_days": 45,
                "weight_kg": 1200,
            },
            {
                "name": "Generator Diesel 100kVA",
                "category": "power_generation",
                "hs_code": "85021100",
                "unit_price_usd": 12000,
                "moq": 1,
                "unit": "unit",
                "origin_country": "TR",
                "company_name": "Turkish Power Systems",
                "lead_time_days": 20,
                "weight_kg": 1200,
            },
            {
                "name": "PVC Pipes 110mm",
                "category": "construction_materials",
                "hs_code": "39172300",
                "unit_price_usd": 3.20,
                "moq": 1000,
                "unit": "meter",
                "origin_country": "TR",
                "company_name": "Turkish Plastics Co",
                "lead_time_days": 7,
                "weight_kg": 2.5,
            },
        ]

        demand_signals = [
            {
                "signal_type": "tender",
                "title": "Basra Hospital Reconstruction — Medical Equipment",
                "description": "Tender for supply of medical equipment and consumables for Basra General Hospital reconstruction. Phase 2.",
                "buyer_name": "Iraq Ministry of Health",
                "buyer_country": "IQ",
                "products_needed": ["medical equipment", "medical scrubs", "hospital beds", "surgical instruments"],
                "estimated_budget_usd": 2500000,
                "tender_status": "open",
                "deadline_date": "2026-08-15",
                "confidence": 0.85,
            },
            {
                "signal_type": "project_requirement",
                "title": "New Baghdad Residential Complex — Construction Materials",
                "description": "5,000-unit residential project in Baghdad requiring steel, cement, tiles, and plumbing." ,
                "buyer_name": "Al-Rafidain Development Co",
                "buyer_country": "IQ",
                "products_needed": ["steel rebar", "cement", "ceramic tiles", "pvc pipes"],
                "estimated_budget_usd": 15000000,
                "deadline_date": "2026-09-01",
                "confidence": 0.75,
            },
            {
                "signal_type": "rfq",
                "title": "Emergency Generator Procurement — Erbil",
                "description": "RFQ for 20 diesel generators for Erbil industrial zone power backup.",
                "buyer_name": "Erbil Industrial Authority",
                "buyer_country": "IQ",
                "products_needed": ["diesel generator", "generator spare parts"],
                "estimated_budget_usd": 250000,
                "deadline_date": "2026-07-10",
                "confidence": 0.90,
            },
            {
                "signal_type": "infrastructure_project",
                "title": "Saudi NEOM Extension — Supplier Registration Open",
                "description": "NEOM project opening supplier registration for construction materials, electrical, and HVAC.",
                "buyer_name": "NEOM Project",
                "buyer_country": "SA",
                "products_needed": ["steel rebar", "led lighting", "hvac systems", "cement", "ceramic tiles"],
                "estimated_budget_usd": 500000000,
                "deadline_date": "2026-12-31",
                "confidence": 0.95,
            },
            {
                "signal_type": "buyer_inquiry",
                "title": "UAE Hospital Group — Medical Consumables Annual Contract",
                "description": "Annual contract for medical consumables supply to 5 hospitals in UAE.",
                "buyer_name": "Emirates Healthcare Group",
                "buyer_country": "AE",
                "products_needed": ["medical scrubs", "surgical gloves", "disposable syringes"],
                "estimated_budget_usd": 500000,
                "confidence": 0.70,
            },
            {
                "signal_type": "reconstruction_need",
                "title": "Aleppo Reconstruction — Phase 3 Materials",
                "description": "Reconstruction of 2,000 housing units in Aleppo. Seeking reliable suppliers of construction materials.",
                "buyer_name": "Syria Reconstruction Authority",
                "buyer_country": "SY",
                "products_needed": ["steel rebar", "cement", "ceramic tiles", "pvc pipes", "electrical cable"],
                "estimated_budget_usd": 8500000,
                "deadline_date": "2026-10-01",
                "confidence": 0.60,
            },
            {
                "signal_type": "tender",
                "title": "Kuwait Oil Company — Pipeline Materials Tender",
                "description": "Annual tender for oil pipeline materials and fittings.",
                "buyer_name": "Kuwait Oil Company",
                "buyer_country": "KW",
                "products_needed": ["steel pipes", "pvc pipes", "pipe fittings"],
                "estimated_budget_usd": 5000000,
                "tender_status": "announced",
                "deadline_date": "2026-09-15",
                "confidence": 0.80,
            },
        ]

        market_intel = [
            {
                "intel_type": "regulation_change",
                "title": "Iraq Lifts Import Ban on Turkish Steel Products",
                "summary": "Iraq has lifted the 2024 import ban on Turkish steel products, effective immediately. 15% tariff applies. This opens a $200M/year market.",
                "countries_affected": ["IQ", "TR"],
                "products_affected": ["steel rebar", "structural steel", "steel pipes"],
                "sentiment": "opportunity",
                "impact_score": 85,
                "confidence": 0.95,
            },
            {
                "intel_type": "market_shortage",
                "title": "Generator Shortage in Iraq — Summer Demand Surge",
                "summary": "Iraq faces acute generator shortage as summer temperatures hit 50°C. Local suppliers sold out. Import window: urgent.",
                "countries_affected": ["IQ"],
                "products_affected": ["diesel generator", "power generator"],
                "sentiment": "opportunity",
                "impact_score": 90,
                "confidence": 0.90,
            },
            {
                "intel_type": "infrastructure_announcement",
                "title": "Qatar Announces $2B Healthcare Expansion Program",
                "summary": "Qatar's Ministry of Health announces $2 billion hospital construction and medical equipment procurement program for 2026-2028.",
                "countries_affected": ["QA"],
                "products_affected": ["medical equipment", "hospital beds", "medical consumables"],
                "sentiment": "opportunity",
                "impact_score": 75,
                "confidence": 0.85,
            },
            {
                "intel_type": "currency_event",
                "title": "Turkish Lira Depreciates 12% Against USD",
                "summary": "TRY fell 12% this quarter, making Turkish exports significantly more competitive. Window for TR-sourced goods.",
                "countries_affected": ["TR"],
                "products_affected": [],
                "sentiment": "opportunity",
                "impact_score": 70,
                "confidence": 0.95,
            },
            {
                "intel_type": "sanctions_update",
                "title": "EU Sanctions on Iran — Opportunity for Alternative Supply Routes",
                "summary": "Updated EU sanctions on Iran create supply gaps in regional markets. Turkey positioned as alternative source.",
                "countries_affected": ["IR", "TR"],
                "products_affected": ["industrial equipment", "chemicals"],
                "sentiment": "opportunity",
                "impact_score": 60,
                "confidence": 0.80,
            },
        ]

        return companies, products, demand_signals, market_intel

    def print_opportunity_card(
        self,
        opp: DetectedOpportunity,
        profitability: ProfitabilityResult,
        risk: RiskAssessment,
        score: OpportunityScore,
    ) -> str:
        """Generate a formatted opportunity card."""
        rec_type, rec_msg = self.decision_engine.recommend_action(opp, score, risk)

        return f"""
╔══════════════════════════════════════════════════════════════════════════╗
║  {opp.title[:64]} 
╠══════════════════════════════════════════════════════════════════════════╣
║  Type:        {opp.opportunity_type.value:<45s} Score: {score.final_score:5.1f}/100 │ Tier: {score.tier}
║  Source:      {opp.source_country:<10s} → Target: {opp.target_country:<10s}
║  Product:      {opp.product_category or 'N/A':<50s}
╠══════════════════════════════════════════════════════════════════════════╣
║  FINANCIALS
║  Capital Required:  ${profitability.cost_breakdown.total_cost_usd:>14,.2f}
║  Expected Revenue:  ${profitability.expected_selling_price_usd:>14,.2f}
║  Expected Profit:   ${profitability.expected_net_profit_usd:>14,.2f}
║  Expected ROI:      {profitability.expected_roi_pct:>13.1f}%
║  Cash Cycle:        {profitability.cash_conversion_cycle_days:>10} days
╠══════════════════════════════════════════════════════════════════════════╣
║  RISK ASSESSMENT
║  Composite Risk:    {risk.composite_risk_score:>10.1f}/100 ({risk.risk_level})
║  Key Risks:         {risk.key_risks[0] if risk.key_risks else 'None identified':<46s}
╠══════════════════════════════════════════════════════════════════════════╣
║  WHY THIS EXISTS
║  {opp.why_exists[:62]}
║  Window: {opp.window_estimate or 'Unknown':<54s}
║  Repeatable: {'Yes' if opp.is_repeatable else 'No':<50s}
╠══════════════════════════════════════════════════════════════════════════╣
║  RECOMMENDATION: {rec_type.value.upper()}
║  {rec_msg[:62]}
╚══════════════════════════════════════════════════════════════════════════╝
"""