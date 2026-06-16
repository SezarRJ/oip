"""OIP - Opportunity Detection Engine"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import math

class OpportunityType(str, Enum):
    TRADE_ARBITRAGE = "trade_arbitrage"
    INFORMATION_ARBITRAGE = "information_arbitrage"
    SUPPLY_GAP = "supply_gap"
    DEMAND_GAP = "demand_gap"
    INVENTORY_LIQUIDATION = "inventory_liquidation"
    PROJECT_PROCUREMENT = "project_procurement"
    TENDER_OPPORTUNITY = "tender_opportunity"
    RECONSTRUCTION = "reconstruction"
    REGIONAL_SHORTAGE = "regional_shortage"
    EMERGING_DEMAND = "emerging_demand"
    REGULATORY_CHANGE = "regulatory_change"
    SHIPPING_ROUTE_ADVANTAGE = "shipping_route_advantage"
    SUPPLIER_BUYER_MATCH = "supplier_buyer_match"
    BROKERAGE = "brokerage"

@dataclass
class DetectedOpportunity:
    opportunity_type: OpportunityType
    title: str
    description: str
    source_country: str
    target_country: str
    product_category: Optional[str] = None
    hs_codes: List[str] = field(default_factory=list)
    why_exists: str = ""
    competitor_analysis: str = ""
    window_estimate: str = ""
    capital_required_estimate: float = 0.0
    requirements_summary: str = ""
    is_repeatable: bool = False
    evidence: List[Dict[str, str]] = field(default_factory=list)
    suppliers_found: List[Dict[str, Any]] = field(default_factory=list)
    buyers_found: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5
    urgency: str = "medium"
    detected_at: datetime = field(default_factory=datetime.utcnow)
    data_sources: List[str] = field(default_factory=list)
    expected_net_profit: float = 0.0
    expected_roi_pct: float = 0.0
    risk_score: float = 50.0
    capital_required_usd: float = 0.0

class OpportunityDetectionEngine:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.detectors = {
            OpportunityType.TRADE_ARBITRAGE: self._detect_trade_arbitrage,
            OpportunityType.SUPPLY_GAP: self._detect_supply_gap,
            OpportunityType.DEMAND_GAP: self._detect_demand_gap,
            OpportunityType.INVENTORY_LIQUIDATION: self._detect_inventory_liquidation,
            OpportunityType.PROJECT_PROCUREMENT: self._detect_project_procurement,
            OpportunityType.TENDER_OPPORTUNITY: self._detect_tender_opportunities,
            OpportunityType.RECONSTRUCTION: self._detect_reconstruction,
            OpportunityType.REGIONAL_SHORTAGE: self._detect_regional_shortage,
            OpportunityType.EMERGING_DEMAND: self._detect_emerging_demand,
            OpportunityType.REGULATORY_CHANGE: self._detect_regulatory_opportunities,
            OpportunityType.SHIPPING_ROUTE_ADVANTAGE: self._detect_shipping_advantages,
            OpportunityType.SUPPLIER_BUYER_MATCH: self._detect_supplier_buyer_matches,
            OpportunityType.BROKERAGE: self._detect_brokerage_opportunities,
        }

    def run_all_detectors(self, companies, products, demand_signals, market_intel) -> List[DetectedOpportunity]:
        all_opps = []
        for opp_type, fn in self.detectors.items():
            try: all_opps.extend(fn(companies, products, demand_signals, market_intel))
            except Exception: pass
        all_opps = self._deduplicate(all_opps)
        w = {"critical":1.0,"high":0.7,"medium":0.4,"low":0.1}
        all_opps.sort(key=lambda o: o.confidence * w.get(o.urgency, 0.0), reverse=True)
        return all_opps

    def _detect_trade_arbitrage(self, c, p, d, i):
        opps = []
        by_cat = {}
        for pr in p:
            cat = pr.get("category","unknown")
            by_cat.setdefault(cat,[]).append(pr)
        for cat, items in by_cat.items():
            if len(items) < 2: continue
            by_cnt = {}
            for it in items:
                cnt = it.get("origin_country",it.get("country_code",""))
                prc = it.get("unit_price_usd")
                if cnt and prc: by_cnt.setdefault(cnt,[]).append(prc)
            if len(by_cnt) < 2: continue
            srcs = {"TR","CN","IR","IQ","SY"}
            dsts = {"IQ","SA","AE","QA","KW","OM","BH","SY","IR"}
            for src in srcs & set(by_cnt.keys()):
                for dst in dsts & set(by_cnt.keys()):
                    if src == dst: continue
                    sa = sum(by_cnt[src])/len(by_cnt[src])
                    da = sum(by_cnt[dst])/len(by_cnt[dst])
                    margin = (da-sa)/sa if sa > 0 else 0
                    if margin > 0.30:
                        opps.append(DetectedOpportunity(
                            opportunity_type=OpportunityType.TRADE_ARBITRAGE,
                            title=f"{cat} Arbitrage: {src} → {dst}",
                            description=f"Price gap ${sa:.2f}→${da:.2f}, margin {margin:.1%}",
                            source_country=src,target_country=dst,product_category=cat,
                            why_exists=f"{margin:.0%} price gap",
                            window_estimate="3-6 months",is_repeatable=True,
                            confidence=min(0.95,0.5+margin*1.5),
                            urgency="high" if margin > 0.5 else "medium"))
        return opps

    def _detect_supply_gap(self, c, p, d, i):
        opps = []
        dem = set()
        for ds in d:
            for pr in ds.get("products_needed",[]):
                dem.add((ds.get("buyer_country",""),pr.lower()))
        sup = set()
        for pr in p:
            sup.add((pr.get("origin_country",""),pr.get("name","").lower()))
        for cnt, prod in dem:
            if cnt and prod:
                if not any(s[0]==cnt and prod in s[1] for s in sup):
                    alt = [s[0] for s in sup if prod in s[1]]
                    if alt:
                        opps.append(DetectedOpportunity(
                            opportunity_type=OpportunityType.SUPPLY_GAP,
                            title=f"Supply Gap: {prod.title()} in {cnt}",
                            description=f"No local supply. Alt: {','.join(alt)}",
                            source_country=alt[0],target_country=cnt,product_category=prod,
                            why_exists=f"No domestic production in {cnt}",
                            is_repeatable=True,confidence=0.75,urgency="high"))
        return opps

    def _detect_demand_gap(self, c, p, d, i):
        opps = []
        sup_p = {}
        for pr in p:
            cnt=pr.get("origin_country","");nm=pr.get("name","").lower()
            if cnt and nm: sup_p.setdefault(cnt,[]).append(nm)
        dem = {}
        for ds in d:
            cnt=ds.get("buyer_country","")
            for pr in ds.get("products_needed",[]): dem.setdefault(cnt,set()).add(pr.lower())
        for src,prods in sup_p.items():
            for prod in set(prods):
                targets=["IQ","SA","AE","QA","KW","OM","BH"]
                mkts=[t for t in targets if t!=src and prod not in dem.get(t,set())]
                if mkts:
                    opps.append(DetectedOpportunity(
                        opportunity_type=OpportunityType.DEMAND_GAP,
                        title=f"Demand Gap: {prod.title()} → {mkts[0]}",
                        description=f"Supply in {src}. No demand visible.",
                        source_country=src,target_country=mkts[0],product_category=prod,
                        why_exists="Product unknown in target",is_repeatable=True,
                        confidence=0.55,urgency="medium"))
        return opps

    def _detect_inventory_liquidation(self, c, p, d, i):
        opps = []
        by_cat = {}
        for pr in p:
            cat=pr.get("category","unknown");prc=pr.get("unit_price_usd")
            if prc and prc>0: by_cat.setdefault(cat,[]).append(pr)
        for cat,items in by_cat.items():
            if len(items)<3: continue
            prices=[it.get("unit_price_usd",0) for it in items]
            avg=sum(prices)/len(prices)
            std=math.sqrt(sum((x-avg)**2 for x in prices)/len(prices)) if len(prices)>1 else 0
            for it in items:
                prc=it.get("unit_price_usd",0)
                if std>0 and prc>0 and prc<avg-2*std:
                    opps.append(DetectedOpportunity(
                        opportunity_type=OpportunityType.INVENTORY_LIQUIDATION,
                        title=f"Liquidation: {it.get('name',cat)}",
                        description=f"${prc:.2f} vs avg ${avg:.2f}",
                        source_country=it.get("origin_country",""),target_country="IQ",
                        product_category=cat,why_exists="Excess inventory",
                        window_estimate="Days to weeks",urgency="critical",confidence=0.60))
        return opps

    def _detect_project_procurement(self, c, p, d, i):
        opps = []
        types={"infrastructure_project","industrial_project","energy_project","healthcare_project",
               "education_project","tourism_project","real_estate_project","hotel_project",
               "port_project","special_economic_zone","industrial_park","project_requirement"}
        for ds in d:
            if ds.get("signal_type","") in types and ds.get("estimated_budget_usd",0)>100000:
                opps.append(DetectedOpportunity(
                    opportunity_type=OpportunityType.PROJECT_PROCUREMENT,
                    title=f"Project: {ds.get('title','Untitled')}",
                    description=ds.get("description",""),
                    source_country=ds.get("buyer_country",""),
                    target_country=ds.get("buyer_country",""),
                    product_category="project_materials",
                    why_exists="Large project needs procurement",
                    capital_required_estimate=ds.get("estimated_budget_usd",0)*0.05,
                    urgency="high" if ds.get("deadline_date") else "medium",confidence=0.70))
        return opps

    def _detect_tender_opportunities(self, c, p, d, i):
        opps = []
        for t in d:
            if t.get("signal_type") in ("tender","procurement_notice") and t.get("tender_status") in ("open","announced","closing_soon"):
                needed=t.get("products_needed",[])
                matches=[pr for pr in p if pr.get("name","").lower() in [n.lower() for n in needed]]
                if matches:
                    opps.append(DetectedOpportunity(
                        opportunity_type=OpportunityType.TENDER_OPPORTUNITY,
                        title=f"Tender: {t.get('title','Tender')}",
                        description=f"Needs {', '.join(needed[:5])}. {len(matches)} suppliers.",
                        source_country=matches[0].get("origin_country",""),
                        target_country=t.get("buyer_country",""),
                        why_exists="Open tender with matching supply",
                        urgency="critical" if t.get("tender_status")=="closing_soon" else "high",
                        confidence=0.80,suppliers_found=matches[:10]))
        return opps

    def _detect_reconstruction(self, c, p, d, i):
        opps = []
        kw=["reconstruction","rebuild","rehabilitation","post-conflict","restoration"]
        rc={"SY","IQ","LY"}
        for intel in i:
            txt=f"{intel.get('title','')} {intel.get('summary','')}"
            if any(k.lower() in txt.lower() for k in kw):
                aff=set(intel.get("countries_affected",[]))&rc
                if aff:
                    opps.append(DetectedOpportunity(
                        opportunity_type=OpportunityType.RECONSTRUCTION,
                        title=f"Recon: {intel.get('title','Rebuild')}",
                        description=intel.get("summary",""),
                        source_country="TR",target_country=list(aff)[0],
                        product_category="construction_materials",
                        why_exists="Post-conflict reconstruction",window_estimate="2-5 years",
                        is_repeatable=True,urgency="high",confidence=0.70))
        return opps

    def _detect_regional_shortage(self, c, p, d, i):
        opps = []
        for intel in i:
            txt=f"{intel.get('title','')} {intel.get('summary','')}"
            if any(w in txt.lower() for w in ["shortage","deficit","supply disruption"]):
                aff=intel.get("countries_affected",[])
                for pn in intel.get("products_affected",[]):
                    alt=[pr for pr in p if pn.lower() in pr.get("name","").lower() and pr.get("origin_country","") not in aff]
                    if alt:
                        opps.append(DetectedOpportunity(
                            opportunity_type=OpportunityType.REGIONAL_SHORTAGE,
                            title=f"Shortage: {pn}",
                            description="Regional shortage. Alt sources found.",
                            source_country=alt[0].get("origin_country",""),
                            target_country=aff[0] if aff else "",
                            product_category=pn,why_exists="Supply disruption",
                            window_estimate="3-12 months",urgency="critical",confidence=0.75))
        return opps

    def _detect_emerging_demand(self, c, p, d, i):
        opps = []
        freq={}
        for ds in d:
            for pr in ds.get("products_needed",[]): freq[pr.lower()]=freq.get(pr.lower(),0)+1
        for pn,cnt in {k:v for k,v in freq.items() if v>=3}.items():
            matches=[pr for pr in p if pn in pr.get("name","").lower()]
            if matches:
                opps.append(DetectedOpportunity(
                    opportunity_type=OpportunityType.EMERGING_DEMAND,
                    title=f"Emerging: {pn.title()}",
                    description=f"Demand {cnt}× — trending.",
                    source_country=matches[0].get("origin_country",""),
                    target_country="IQ",product_category=pn,
                    why_exists=f"Multiple buyers seeking {pn}",
                    window_estimate="Now",is_repeatable=True,
                    urgency="high",confidence=0.55+min(0.35,cnt*0.05)))
        return opps

    def _detect_regulatory_opportunities(self, c, p, d, i):
        opps = []
        for intel in i:
            if intel.get("intel_type") in ("regulation_change","trade_policy","tariff_change","sanctions_update"):
                if intel.get("sentiment")=="opportunity":
                    opps.append(DetectedOpportunity(
                        opportunity_type=OpportunityType.REGULATORY_CHANGE,
                        title=f"Regulatory: {intel.get('title','Change')}",
                        description=intel.get("summary",""),
                        source_country="TR",target_country="IQ",
                        why_exists="Reg change creates inefficiency",window_estimate="1-3 months",
                        urgency="critical",confidence=0.60))
        return opps

    def _detect_shipping_advantages(self, c, p, d, i):
        opps = []
        fast={("TR","IQ"):"2 days vs 30 by sea",("TR","SY"):"Same-day possible",("TR","IR"):"Direct border"}
        urg={"medical","pharmaceutical","perishable","construction_materials","spare_parts"}
        for (src,dst),adv in fast.items():
            for pr in p:
                if pr.get("origin_country")==src and pr.get("category") in urg:
                    opps.append(DetectedOpportunity(
                        opportunity_type=OpportunityType.SHIPPING_ROUTE_ADVANTAGE,
                        title=f"Route: {pr.get('name','')} {src}→{dst}",
                        description=adv,source_country=src,target_country=dst,
                        product_category=pr.get("category"),
                        why_exists=adv,is_repeatable=True,urgency="medium",confidence=0.70))
        return opps

    def _detect_supplier_buyer_matches(self, c, p, d, i):
        opps = []
        for ds in d:
            needed=set(pr.lower() for pr in ds.get("products_needed",[]))
            if not needed: continue
            for pr in p:
                pn=pr.get("name","").lower()
                if any(np in pn or pn in np for np in needed):
                    opps.append(DetectedOpportunity(
                        opportunity_type=OpportunityType.SUPPLIER_BUYER_MATCH,
                        title=f"Match: {pr.get('name')} → {ds.get('buyer_name','Buyer')}",
                        description="Direct supply-demand match.",
                        source_country=pr.get("origin_country",""),
                        target_country=ds.get("buyer_country",""),
                        product_category=pr.get("category"),
                        why_exists="Direct match",urgency="high",confidence=0.85,
                        suppliers_found=[pr],buyers_found=[ds]))
        return opps

    def _detect_brokerage_opportunities(self, c, p, d, i):
        opps = []
        for ds in d:
            if not ds.get("products_needed"): continue
            matches=[pr for pr in p if any(np.lower() in pr.get("name","").lower() for np in ds.get("products_needed",[]))]
            if matches and ds.get("estimated_budget_usd",0)>10000:
                comm=ds.get("estimated_budget_usd",0)*0.03
                opps.append(DetectedOpportunity(
                    opportunity_type=OpportunityType.BROKERAGE,
                    title=f"Brokerage: {ds.get('title','Deal')} — ${comm:,.0f}",
                    description=f"Connect {len(matches)} suppliers. Zero capital.",
                    source_country=matches[0].get("origin_country",""),
                    target_country=ds.get("buyer_country",""),
                    product_category=ds.get("products_needed",[None])[0],
                    why_exists="Parties exist but disconnected",is_repeatable=True,
                    urgency="high",confidence=0.75,suppliers_found=matches,buyers_found=[ds]))
        return opps

    def _deduplicate(self, opps):
        seen=set();unique=[]
        for o in opps:
            key=f"{o.opportunity_type.value}:{o.source_country}:{o.target_country}:{o.product_category}"
            if key not in seen: seen.add(key);unique.append(o)
        return unique
