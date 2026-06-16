"""OIP - Profitability Engine"""
from dataclasses import dataclass, field
from typing import Dict, Any, Tuple

@dataclass
class CostBreakdown:
    purchase_cost_usd: float = 0.0; shipping_cost_usd: float = 0.0
    insurance_cost_usd: float = 0.0; customs_duty_usd: float = 0.0
    vat_tax_usd: float = 0.0; other_taxes_usd: float = 0.0
    handling_cost_usd: float = 0.0; warehousing_cost_usd: float = 0.0
    financing_cost_usd: float = 0.0; brokerage_fee_usd: float = 0.0
    miscellaneous_usd: float = 0.0
    @property
    def total_cost_usd(self):
        return sum([self.purchase_cost_usd,self.shipping_cost_usd,self.insurance_cost_usd,
                    self.customs_duty_usd,self.vat_tax_usd,self.other_taxes_usd,
                    self.handling_cost_usd,self.warehousing_cost_usd,
                    self.financing_cost_usd,self.brokerage_fee_usd,self.miscellaneous_usd])

@dataclass
class ProfitabilityResult:
    cost_breakdown: CostBreakdown = field(default_factory=CostBreakdown)
    expected_selling_price_usd: float = 0.0; expected_commission_usd: float = 0.0
    expected_gross_profit_usd: float = 0.0; expected_net_profit_usd: float = 0.0
    expected_roi_pct: float = 0.0; cash_conversion_cycle_days: int = 0
    profit_per_dollar_invested: float = 0.0; annualized_roi_pct: float = 0.0
    optimistic_net_profit: float = 0.0; pessimistic_net_profit: float = 0.0

class ProfitabilityEngine:
    def __init__(self, config=None):
        self.config = config or {}
        self.defaults = {"insurance_rate":0.01,"handling_rate":0.02,"warehousing_rate":0.01,
                         "financing_rate":0.12,"brokerage_rate":0.03,"contingency_rate":0.02,"target_margin":0.25}
        self.shipping = {
            ("CN","IQ"):{"sea_20gp":3500,"sea_kg":0.15,"days":30,"mode":"sea"},
            ("CN","AE"):{"sea_20gp":2500,"sea_kg":0.10,"days":20,"mode":"sea"},
            ("CN","SA"):{"sea_20gp":2800,"sea_kg":0.12,"days":22,"mode":"sea"},
            ("CN","IR"):{"sea_20gp":3000,"sea_kg":0.13,"days":25,"mode":"sea"},
            ("TR","IQ"):{"land_truck":1500,"land_kg":0.08,"days":2,"mode":"land"},
            ("TR","SY"):{"land_truck":800,"land_kg":0.05,"days":1,"mode":"land"},
            ("TR","SA"):{"sea_20gp":2200,"sea_kg":0.10,"days":7,"mode":"sea"},
            ("TR","AE"):{"sea_20gp":2000,"sea_kg":0.09,"days":8,"mode":"sea"},
            ("TR","IR"):{"land_truck":1200,"land_kg":0.07,"days":2,"mode":"land"},
            ("IQ","TR"):{"land_truck":1500,"land_kg":0.08,"days":2,"mode":"land"},
        }
        self.customs = {
            ("TR","IQ"):0.05,("CN","IQ"):0.15,("CN","IR"):0.20,("TR","SY"):0.08,
            ("TR","SA"):0.05,("CN","SA"):0.12,("CN","AE"):0.05,("TR","AE"):0.05,("IQ","TR"):0.03,
        }
        self.vat = {"IQ":0.0,"SA":0.15,"AE":0.05,"QA":0.0,"KW":0.0,"OM":0.05,"BH":0.10,"IR":0.09,"SY":0.0,"TR":0.18}

    def calculate(self, purchase_cost_usd, source_country, target_country, weight_kg=None,
                  shipping_mode=None, product_value_usd=None, quantity=1, custom_costs=None,
                  commission_based=False, deal_size_usd=None, cash_cycle_days=60):
        cost = CostBreakdown()
        cost.purchase_cost_usd = purchase_cost_usd
        cv = product_value_usd or purchase_cost_usd
        cost.shipping_cost_usd = self._ship(source_country,target_country,weight_kg,shipping_mode,quantity)
        cost.insurance_cost_usd = cv * self.defaults["insurance_rate"]
        duty = self.customs.get((source_country,target_country),0.10)
        cif = cv + cost.shipping_cost_usd + cost.insurance_cost_usd
        cost.customs_duty_usd = cif * duty
        v = self.vat.get(target_country,0.05)
        cost.vat_tax_usd = (cif + cost.customs_duty_usd) * v
        cost.handling_cost_usd = purchase_cost_usd * self.defaults["handling_rate"]
        cost.warehousing_cost_usd = purchase_cost_usd * self.defaults["warehousing_rate"]
        cost.financing_cost_usd = purchase_cost_usd * self.defaults["financing_rate"] * (cash_cycle_days/365)
        cost.miscellaneous_usd = purchase_cost_usd * self.defaults["contingency_rate"]
        if custom_costs:
            for k,v in custom_costs.items():
                if hasattr(cost,k): setattr(cost,k,v)
        # Get market-driven margin if available, fall back to 25%
        market_margin = self._estimate_market_margin(source_country, target_country, purchase_cost_usd)
        
        if commission_based:
            sp=0;comm=(deal_size_usd or 0)*self.defaults["brokerage_rate"]
        else:
            sp=cost.total_cost_usd*(1+market_margin);comm=0
        gp=sp-cost.purchase_cost_usd
        np_=sp-cost.total_cost_usd+comm
        roi=(np_/cost.total_cost_usd*100) if cost.total_cost_usd>0 else float('inf')
        ppd=np_/cost.total_cost_usd if cost.total_cost_usd>0 else 0
        turns=365/cash_cycle_days if cash_cycle_days>0 else 1
        return ProfitabilityResult(cost_breakdown=cost,expected_selling_price_usd=sp,
                                   expected_commission_usd=comm,expected_gross_profit_usd=gp,
                                   expected_net_profit_usd=np_,expected_roi_pct=round(roi,2),
                                   cash_conversion_cycle_days=cash_cycle_days,
                                   profit_per_dollar_invested=round(ppd,4),
                                   annualized_roi_pct=round(roi*turns,2),
                                   optimistic_net_profit=np_*1.30,pessimistic_net_profit=np_*0.50)

    
    def _estimate_market_margin(self, src: str, dst: str, purchase_cost: float) -> float:
        """Estimate realistic market margin based on corridor and product value."""
        # Base margins by corridor (reflecting real market conditions)
        corridor_margins = {
            ("TR","IQ"): 0.18,  # Competitive corridor, moderate margins
            ("TR","SY"): 0.22,  # Higher risk, higher margin
            ("TR","SA"): 0.15,  # Competitive GCC market
            ("TR","AE"): 0.15,
            ("TR","IR"): 0.20,
            ("CN","IQ"): 0.28,  # Long supply chain, higher margin justified
            ("CN","SA"): 0.20,
            ("CN","AE"): 0.18,
            ("CN","IR"): 0.25,
            ("IQ","TR"): 0.15,
        }
        base = corridor_margins.get((src, dst), 0.22)
        
        # Small deals deserve higher margins (compensates fixed costs)
        if purchase_cost < 5000:
            base += 0.10
        elif purchase_cost < 50000:
            base += 0.05
        
        # Large deals are more competitive
        if purchase_cost > 500000:
            base -= 0.05
            
        return max(0.10, min(0.50, base))
    def _ship(self,src,dst,w=None,mode=None,q=1):
        e=self.shipping.get((src,dst),{})
        if not e:
            if src==dst: return 500.0
            if self._nb(src,dst): return 1500.0
            return 3000.0
        if w:
            pk="land_kg" if e.get("mode")=="land" else "sea_kg"
            return w*e.get(pk,0.15)*q
        if e.get("mode")=="land": return e.get("land_truck",1500)
        return e.get("sea_20gp",3000)

    def _nb(self,a,b):
        return b in {"TR":{"IQ","SY","IR"},"IQ":{"TR","SY","IR","SA","KW"},"SY":{"TR","IQ"},"IR":{"TR","IQ"},"SA":{"IQ","KW","AE","QA","OM","BH"}}.get(a,set())
