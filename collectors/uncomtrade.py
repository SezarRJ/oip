"""
UN Comtrade Collector — International trade flow data.
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from data_collection.collectors.base import BaseCollector, CollectionResult, SourceType, Frequency

class UNComtradeCollector(BaseCollector):
    source_name = "un_comtrade"
    source_type = SourceType.TRADE_DATABASE
    frequency = Frequency.DAILY
    target_countries = ["IQ","SA","AE","QA","KW","OM","BH","SY","IR"]
    API_BASE = "https://comtradeapi.un.org/public/v1/preview"
    KEY_HS = {"7214":"steel_bars","2523":"cement","6907":"ceramic_tiles","3917":"plastic_pipes",
              "6211":"medical_garments","8502":"generators","9405":"lighting","8544":"electrical_cable",
              "8413":"pumps","8415":"hvac","9402":"medical_furniture","7304":"steel_pipes"}
    SOURCE_COUNTRIES = [792,368,156,364,760]

    def __init__(self, config=None):
        super().__init__(config)
        self.request_delay = 1.5
    def can_collect(self) -> bool: return True

    async def collect(self) -> CollectionResult:
        result = CollectionResult(source_name=self.source_name, source_type=self.source_type, started_at=datetime.utcnow())
        import httpx
        async with httpx.AsyncClient(headers={"Accept":"application/json"}, timeout=30.0) as client:
            for hs_code, category in self.KEY_HS.items():
                for src_code in self.SOURCE_COUNTRIES:
                    try:
                        flows = await self._fetch(client, src_code, hs_code)
                        for flow in flows:
                            p = self._to_product(flow, category)
                            if p: result.products.append(p)
                            intel = self._to_intel(flow, category)
                            if intel: result.market_intel.append(intel)
                        result.items_collected += len(flows)
                    except Exception as e: result.errors.append(f"{src_code}/{hs_code}: {e}")
                    await asyncio.sleep(self.request_delay)
        result.completed_at = datetime.utcnow()
        return result

    async def _fetch(self, client, reporter, cmd):
        try:
            resp = await client.get(f"{self.API_BASE}/C/A/{reporter}/all/{cmd}", params={"flowCode":"X","period":"2025"})
            return resp.json().get("data",[]) if resp.status_code==200 else []
        except: return []

    def _to_product(self, flow, cat):
        v=flow.get("primaryValue",0); q=flow.get("netWgt",flow.get("qty",0))
        if not q or q==0: return None
        return {"name":f"{cat} (trade flow)","category":cat,"hs_code":flow.get("cmdCode",""),
                "origin_country":self._iso(flow.get("reporterCode",0)),"unit_price_usd":round(v/q,2) if q else None,
                "trade_volume_kg":q,"trade_value_usd":v,"unit":"kg","source_name":self.source_name}

    def _to_intel(self, flow, cat):
        v=flow.get("primaryValue",0)
        if v<1_000_000: return None
        r=self._iso(flow.get("reporterCode",0)); p=self._iso(flow.get("partnerCode",0))
        return {"intel_type":"trade_flow","title":f"Trade: {cat} {r}→{p}",
                "summary":f"Annual {cat} trade: ${v:,.0f} {r}→{p}",
                "countries_affected":[r,p],"products_affected":[cat],"sentiment":"opportunity",
                "impact_score":min(100,int(v/100000)),"source_name":self.source_name,"confidence":0.90,"published_at":datetime.utcnow()}

    def _iso(self, c):
        return {792:"TR",368:"IQ",156:"CN",364:"IR",760:"SY",682:"SA",784:"AE",634:"QA",
                414:"KW",512:"OM",48:"BH",0:"WLD"}.get(int(c),str(c))
    async def search(self, q, c=None): return []
