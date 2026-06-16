"""DG Market Collector — Global tender/procurement platform."""
import asyncio, re
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from data_collection.collectors.base import BaseCollector, CollectionResult, SourceType, Frequency

class DGMarketCollector(BaseCollector):
    source_name = "dgmarket"
    source_type = SourceType.TENDER_PLATFORM
    frequency = Frequency.EVERY_6H
    target_countries = ["IQ","SA","AE","QA","KW","OM","BH","SY"]

    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.dgmarket.com"
        self.request_delay = 2.0
    def can_collect(self) -> bool: return True

    async def collect(self) -> CollectionResult:
        result = CollectionResult(source_name=self.source_name, source_type=self.source_type, started_at=datetime.utcnow())
        import httpx
        from bs4 import BeautifulSoup
        async with httpx.AsyncClient(headers={"User-Agent":"Mozilla/5.0","Accept":"text/html"}, timeout=30.0, follow_redirects=True) as client:
            for country in self.target_countries:
                try:
                    resp = await client.get(f"{self.base_url}/tenders/search?country={country}")
                    if resp.status_code != 200: continue
                    soup = BeautifulSoup(resp.text,"lxml")
                    for card in soup.select(".tender-item,.tender-card,.listing-item,tr")[:15]:
                        title_el = card.select_one("a,.title,h3")
                        desc_el = card.select_one(".description,.summary,p")
                        date_el = card.select_one(".date,.deadline,.closing")
                        if not title_el: continue
                        title = title_el.get_text(strip=True)
                        signal = {"signal_type":"tender","title":title,
                            "description":desc_el.get_text(strip=True) if desc_el else "",
                            "buyer_country":country,"products_needed":self._prods(title),
                            "source_url":self.base_url,"source_name":self.source_name,
                            "tender_status":"open","confidence":0.65}
                        if date_el: signal["deadline_date"] = date_el.get_text(strip=True)
                        result.demand_signals.append(signal)
                        result.items_collected += 1
                except Exception as e: result.errors.append(f"{country}: {e}")
                await asyncio.sleep(self.request_delay)
        result.completed_at = datetime.utcnow()
        return result

    def _prods(self, title):
        t=title.lower()
        return [p for p in ["steel","cement","generator","medical","construction","equipment",
                "supplies","services","consulting","infrastructure","power","water","road","building"] if p in t]

    async def search(self, query, country=None):
        r = await self.collect()
        if country: return [s for s in r.demand_signals if s.get("buyer_country")==country]
        return r.demand_signals
