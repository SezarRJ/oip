"""
OIP - Configuration Loader. Loads settings.yaml. All engines use this.
"""
import os, yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class CapitalTier:
    label: str; min_amount: float; max_amount: float

@dataclass
class CountryConfig:
    code: str; name: str; currency: str; risk_base: float = 0.30

@dataclass
class ScoringWeights:
    expected_profit: float = 0.25; probability_of_success: float = 0.20
    capital_efficiency: float = 0.15; execution_difficulty_inverse: float = 0.10
    speed_to_revenue: float = 0.10; repeatability: float = 0.08
    risk_inverse: float = 0.07; scalability: float = 0.05

@dataclass
class RiskWeights:
    supplier_risk: float = 0.20; buyer_risk: float = 0.15; country_risk: float = 0.15
    currency_risk: float = 0.10; logistics_risk: float = 0.10; customs_risk: float = 0.10
    payment_risk: float = 0.10; fraud_risk: float = 0.05; execution_risk: float = 0.05

@dataclass
class OIPConfig:
    sourcing_markets: list = field(default_factory=list)
    demand_markets: list = field(default_factory=list)
    capital_tiers: list = field(default_factory=list)
    data_sources: Dict[str, list] = field(default_factory=dict)
    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)
    risk_weights: RiskWeights = field(default_factory=RiskWeights)
    opportunity_types: list = field(default_factory=list)
    collection_schedule: Dict[str, list] = field(default_factory=dict)
    ai: Dict[str, Any] = field(default_factory=dict)
    _raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def source_country_codes(self) -> set:
        codes = set()
        for tier in self.sourcing_markets:
            for m in (tier if isinstance(tier, list) else [tier]):
                if isinstance(m, dict) and m.get("code"): codes.add(m["code"])
        return codes

    @property
    def demand_country_codes(self) -> set:
        codes = set()
        for tier in self.demand_markets:
            for m in (tier if isinstance(tier, list) else [tier]):
                if isinstance(m, dict) and m.get("code"): codes.add(m["code"])
        return codes

    @property
    def all_country_codes(self) -> set:
        return self.source_country_codes | self.demand_country_codes

    @property
    def high_priority_sources(self) -> list:
        sources = []
        for srcs in self.data_sources.values():
            for src in srcs:
                if isinstance(src, dict) and src.get("priority") == "high":
                    sources.append(src)
        return sources

def load_config(path: str = None) -> OIPConfig:
    if path is None:
        path = os.environ.get("OIP_CONFIG_PATH", str(Path(__file__).parent / "settings.yaml"))
    if not os.path.exists(path): return OIPConfig()
    with open(path) as f: raw = yaml.safe_load(f)
    config = OIPConfig(_raw=raw)
    src = raw.get("sourcing_markets", {})
    config.sourcing_markets = [src.get("primary",[]), src.get("secondary",[]), src.get("tertiary",[])]
    dem = raw.get("demand_markets", {})
    config.demand_markets = [dem.get("primary",[]), dem.get("secondary",[]), dem.get("tertiary",[])]
    config.capital_tiers = raw.get("capital_tiers", [])
    config.data_sources = raw.get("data_sources", {})
    sw = raw.get("scoring_weights", {}); config.scoring_weights = ScoringWeights(**sw) if sw else ScoringWeights()
    rw = raw.get("risk_weights", {}); config.risk_weights = RiskWeights(**rw) if rw else RiskWeights()
    config.opportunity_types = raw.get("opportunity_types", [])
    config.collection_schedule = raw.get("collection_schedule", {})
    config.ai = raw.get("ai", {})
    return config

config = load_config()
