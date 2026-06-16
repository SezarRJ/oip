"""OIP - Risk Engine"""
from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class RiskComponents:
    supplier_risk:float=50.0;buyer_risk:float=50.0;country_risk:float=50.0
    political_risk:float=50.0;currency_risk:float=50.0;logistics_risk:float=50.0
    customs_risk:float=50.0;payment_risk:float=50.0;fraud_risk:float=50.0
    market_risk:float=50.0;execution_risk:float=50.0
    def to_dict(self):return{k:v for k,v in self.__dict__.items()}

@dataclass
class RiskAssessment:
    components:RiskComponents=field(default_factory=RiskComponents)
    composite_risk_score:float=50.0;risk_level:str="medium"
    key_risks:List[str]=field(default_factory=list)
    mitigations:List[str]=field(default_factory=list)
    red_flags:List[str]=field(default_factory=list)

class RiskEngine:
    def __init__(self,config=None):
        self.config=config or {}
        self.w={"supplier_risk":0.20,"buyer_risk":0.15,"country_risk":0.15,"political_risk":0.08,
                "currency_risk":0.10,"logistics_risk":0.10,"customs_risk":0.10,"payment_risk":0.10,
                "fraud_risk":0.05,"market_risk":0.05,"execution_risk":0.07}
        self.cr={"TR":0.35,"IQ":0.50,"SY":0.70,"IR":0.60,"CN":0.20,"SA":0.20,"AE":0.15,"QA":0.15,
                 "KW":0.18,"OM":0.25,"BH":0.22,"DE":0.10,"GB":0.12,"KZ":0.35,"EG":0.40,"LY":0.55,"DZ":0.40}
        self.cv={"TRY":0.25,"IQD":0.05,"SYP":0.40,"IRR":0.35,"CNY":0.05,"SAR":0.01,"AED":0.01,
                 "QAR":0.01,"KWD":0.03,"OMR":0.01,"BHD":0.01,"EUR":0.05,"GBP":0.07}

    def assess(self,source_country,target_country,supplier_data=None,buyer_data=None,
               opportunity_type="trade",payment_method="lc",shipping_mode="sea"):
        c=RiskComponents()
        c.supplier_risk=self._sr(supplier_data,source_country)
        c.buyer_risk=self._br(buyer_data,target_country)
        c.country_risk=max(self.cr.get(source_country,0.4),self.cr.get(target_country,0.35))*100
        c.political_risk=self._pr(source_country,target_country)
        c.currency_risk=self._cur(source_country,target_country)
        c.logistics_risk=self._lr(source_country,target_country,shipping_mode)
        c.customs_risk=self._cust(source_country,target_country)
        c.payment_risk=self._pay(payment_method,target_country)
        c.fraud_risk=self._fr(supplier_data,buyer_data,source_country,target_country)
        c.market_risk=self._mr(opportunity_type)
        c.execution_risk=self._er(source_country,target_country,shipping_mode)
        comp=sum(self.w[k]*getattr(c,k) for k in self.w)
        lvl="low" if comp<25 else "medium" if comp<50 else "high" if comp<75 else "extreme"
        krs=[f"{n.replace('_',' ').title()}:{s:.0f}/100" for n,s in sorted(c.to_dict().items(),key=lambda x:x[1],reverse=True) if s>60]
        return RiskAssessment(components=c,composite_risk_score=round(comp,1),risk_level=lvl,
                              key_risks=krs,mitigations=self._gm(c),red_flags=self._rf(c,supplier_data,source_country,target_country))

    def _sr(self,s,cnt):
        if not s:return 60.0
        r=50.0
        if s.get("verified"):r-=20
        rel=s.get("reliability_score",5);r-=(rel-5)*5
        y=s.get("years_in_business",0)
        if y>10:r-=15
        elif y>5:r-=8
        elif y<2:r+=15
        certs=s.get("certifications",[]);r-=len(certs)*2 if certs else 0
        r+=self.cr.get(cnt,0.4)*15
        return max(0,min(100,r))

    def _br(self,b,cnt):
        if not b:return 55.0
        r=50.0
        if b.get("verified"):r-=15
        if b.get("company_type")=="government_entity":r-=20
        r+=self.cr.get(cnt,0.35)*20
        return max(0,min(100,r))

    def _pr(self,s,d):
        hr={"SY":85,"IR":65,"IQ":60,"LY":75}
        return max(hr.get(s,25),hr.get(d,25))

    def _cur(self,s,d):
        curs={"TR":"TRY","IQ":"IQD","SY":"SYP","IR":"IRR","CN":"CNY","SA":"SAR","AE":"AED","QA":"QAR","KW":"KWD","OM":"OMR","BH":"BHD"}
        sc=curs.get(s,"USD");dc=curs.get(d,"USD")
        r=(self.cv.get(sc,0.1)+self.cv.get(dc,0.1))*100
        if sc in("IRR","SYP"):r+=20
        return min(100,r)

    def _lr(self,s,d,m):
        r=20.0
        if not self._nb(s,d):r+=20
        else:r+=5
        if m=="air":r-=5
        elif m=="land" and s in("SY","IR"):r+=15
        elif m=="sea":r+=10
        pp={"IQ":15,"SY":20,"LY":20};r+=pp.get(d,0)
        return min(100,r)

    def _cust(self,s,d):
        r=25.0;hc={"IQ":20,"SY":30,"IR":25,"LY":25}
        r+=hc.get(d,0)+hc.get(s,0)*0.3
        return min(100,r)

    def _pay(self,m,d):
        rm={"lc":20,"advance":10,"tt":35,"open_account":60}
        r=rm.get(m.lower(),40);sc={"IR":30,"SY":35};r+=sc.get(d,0)
        return min(100,r)

    def _fr(self,s,b,src,dst):
        r=25.0;hf={"SY":20,"IR":10,"IQ":10}
        r+=hf.get(src,0)+hf.get(dst,0)*0.5
        if s and not s.get("verified"):r+=15
        if b and not b.get("verified"):r+=10
        if s and s.get("email") and not s.get("phone"):r+=10
        return min(100,r)

    def _mr(self,ot):
        return{"trade_arbitrage":30,"brokerage":25,"tender_opportunity":35,"project_procurement":30,
               "inventory_liquidation":20,"supply_gap":35,"demand_gap":40,"reconstruction":45,
               "regional_shortage":25,"regulatory_change":50}.get(ot,35)

    def _er(self,s,d,m):
        r=30.0
        if not self._nb(s,d):r+=15
        lm={("CN","IQ"):10,("CN","SY"):10,("CN","SA"):8,("CN","IR"):5};r+=lm.get((s,d),0)
        r+=({"sea":5,"land":10,"air":3}).get(m,8)
        return min(100,r)

    def _gm(self,c):
        mg=[]
        if c.supplier_risk>60:mg.append("Third-party inspection")
        if c.buyer_risk>60:mg.append("Require LC or advance")
        if c.country_risk>60:mg.append("Political risk insurance")
        if c.currency_risk>60:mg.append("Denominate in USD/EUR")
        if c.logistics_risk>60:mg.append("Established forwarders")
        if c.customs_risk>60:mg.append("Local customs broker")
        if c.payment_risk>60:mg.append("Confirmed irrevocable LC")
        if c.fraud_risk>60:mg.append("Independent due diligence")
        return mg or["Standard diligence"]

    def _rf(self,c,s,src,dst):
        rf=[]
        if c.supplier_risk>75 or c.country_risk>75:rf.append("CRITICAL:Risk>75/100")
        if src in("SY","IR")and dst in("SY","IR"):rf.append("Sanctions corridor")
        if c.payment_risk>80:rf.append("Severe payment risk")
        if c.fraud_risk>70:rf.append("Fraud risk elevated")
        if s and s.get("years_in_business",0)<1:rf.append("Supplier<1 year")
        return rf

    def _nb(self,a,b):
        return b in{"TR":{"IQ","SY","IR"},"IQ":{"TR","SY","IR","SA","KW"},"SY":{"TR","IQ"},"IR":{"TR","IQ"},"SA":{"IQ","KW","AE","QA","OM","BH"}}.get(a,set())
