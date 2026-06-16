"""OIP - Scoring Engine"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple

@dataclass
class ScoreComponents:
    profit_score:float=0.0;probability_score:float=0.0
    capital_efficiency_score:float=0.0;execution_ease_score:float=0.0
    speed_score:float=0.0;repeatability_score:float=0.0
    scalability_score:float=0.0;market_demand_score:float=0.0
    supply_constraint_score:float=0.0;competitive_intensity_score:float=0.0
    risk_score_inverse:float=0.0

@dataclass
class OpportunityScore:
    components:ScoreComponents=field(default_factory=ScoreComponents)
    final_score:float=0.0;tier:str="C";summary:str="";global_rank:int=0

class ScoringEngine:
    def __init__(self,config=None):
        self.config=config or {}
        self.w={"profit_score":0.25,"probability_score":0.20,"capital_efficiency_score":0.15,
                "execution_ease_score":0.10,"speed_score":0.10,"repeatability_score":0.08,
                "risk_score_inverse":0.07,"scalability_score":0.05}

    def score(self,expected_net_profit,expected_roi_pct,probability_of_success,
              capital_required,risk_score,cash_conversion_days,is_repeatable,
              opportunity_type,execution_complexity=5.0,competitive_intensity=5.0,
              market_demand_strength=5.0,supply_constraint=5.0,scalability=5.0):
        c=ScoreComponents()
        c.profit_score=min(100,(max(0,expected_net_profit)/1000)**0.6*8) if expected_net_profit>0 else 50
        if expected_net_profit<0:c.profit_score=max(0,50+expected_net_profit/100)
        c.probability_score=probability_of_success*100
        c.capital_efficiency_score=100 if expected_roi_pct==float('inf') else min(100,expected_roi_pct)
        if capital_required==0:c.capital_efficiency_score=100
        elif capital_required<10000 and expected_roi_pct>50:
            c.capital_efficiency_score=min(100,c.capital_efficiency_score+20)
        c.execution_ease_score=max(0,(10-execution_complexity)/10*100)
        if cash_conversion_days<=7:c.speed_score=100
        elif cash_conversion_days<=30:c.speed_score=85
        elif cash_conversion_days<=60:c.speed_score=65
        elif cash_conversion_days<=120:c.speed_score=40
        else:c.speed_score=15
        c.repeatability_score=90 if is_repeatable else 20
        c.risk_score_inverse=max(0,100-risk_score)
        c.scalability_score=scalability/10*100
        c.market_demand_score=market_demand_strength/10*100
        c.supply_constraint_score=max(0,(10-supply_constraint)/10*100)
        c.competitive_intensity_score=max(0,(10-competitive_intensity)/10*100)
        fs=sum(self.w[k]*getattr(c,k) for k in self.w)
        if fs>=85:tier="S"
        elif fs>=70:tier="A"
        elif fs>=50:tier="B"
        elif fs>=30:tier="C"
        else:tier="D"
        return OpportunityScore(components=c,final_score=round(fs,1),tier=tier,summary=self._sum(fs,tier))

    def _sum(self,s,t):
        if t in("S","A"):return f"Exceptional (Tier {t},{s:.0f}/100)"
        elif t=="B":return f"Solid (Tier {t},{s:.0f}/100)"
        elif t=="C":return f"Marginal (Tier {t},{s:.0f}/100)"
        return f"Weak (Tier {t},{s:.0f}/100)"

    def rank(self,scores):
        ss=sorted(scores,key=lambda x:x.final_score,reverse=True)
        for i,s in enumerate(ss,1):s.global_rank=i
        return ss
