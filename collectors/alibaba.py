"""
Alibaba Collector — B2B marketplace scraping for product/supplier discovery.
"""
import asyncio, re
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from data_collection.collectors.base import BaseCollector, CollectionResult, SourceType, Frequency

class AlibabaCollector(BaseCollector):
    source_name = "alibaba"
    source_type = SourceType.B2B_MARKETPLACE
    frequency = Frequency.EVERY_6H
    target_countries = ["IQ","SA","AE","QA","KW","OM","BH","SY"]
    target_languages = ["en"]

    SEARCH_QUERIES = [
        "steel rebar construction", "cement portland bulk", "ceramic floor tiles",
        "pvc pipes plumbing", "medical scrubs hospital", "diesel generator industrial",
        "led lighting fixtures", "electrical cable copper", "solar panel system",
        "water pump industrial", "hvac system commercial", "steel pipes oil gas",
        "safety equipment construction", "hospital bed medical",
    ]

    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.alibaba.com"
        self.search_url = "https://www.alibaba.com/trade/search"
        self.headers = {"User-Agent": "Mozilla/5.0","Accept": "text/html","Accept-Language": "en"}
        self.request_delay = 2.0

    def can_collect(self) -> bool: return True

    async def collect(self) -> CollectionResult:
        result = CollectionResult(source_name=self.source_name, source_type=self.source_type, started_at=datetime.utcnow())
        import httpx
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            for query in self.SEARCH_QUERIES:
                try:
                    products = await self._search(client, query)
                    result.products.extend(products)
                    result.items_collected += len(products)
                    for product in products:
                        if product.get("company_name"):
                            result.companies.append({
                                "name": product["company_name"],
                                "country_code": product.get("origin_country",""),
                                "company_type": "manufacturer",
                                "source_url": product.get("source_url",""),
                                "source_name": self.source_name,
                                "verified": product.get("verified",False),
                                "years_in_business": product.get("supplier_years"),
                                "certifications": product.get("certifications",[]),
                            })
                except Exception as e: result.errors.append(f"{query}: {e}")
                await asyncio.sleep(self.request_delay)
        result.completed_at = datetime.utcnow()
        return result

    async def _search(self, client, query: str) -> List[Dict]:
        try:
            params = {"SearchText": query, "page": 1, "indexArea": "product_en"}
            resp = await client.get(f"{self.search_url}?{urlencode(params)}")
            if resp.status_code != 200: return []
            return self._parse(resp.text, query)
        except Exception: return []

    def _parse(self, html: str, query: str) -> List[Dict]:
        products = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            for card in soup.select('[class*="search-card"],[class*="product"]')[:20]:
                try:
                    p = self._extract_card(card, query)
                    if p: products.append(p)
                except Exception: pass
        except ImportError: pass
        return products

    def _extract_card(self, card, query: str) -> Optional[Dict]:
        product = {"source_name": self.source_name, "source_url": "", "category": self._cat(query)}
        title_el = card.select_one('[class*="title"],h2,a')
        if title_el:
            product["name"] = title_el.get_text(strip=True)[:500]
            href = title_el.get("href","")
            if href: product["source_url"] = href if href.startswith("http") else f"{self.base_url}{href}"
        if not product.get("name"): return None
        price_el = card.select_one('[class*="price"],[class*="Price"]')
        if price_el: product["unit_price_usd"] = self._price(price_el.get_text(strip=True))
        moq_el = card.select_one('[class*="moq"],[class*="min-order"]')
        if moq_el: product["moq"] = self._num(moq_el.get_text(strip=True))
        supplier_el = card.select_one('[class*="supplier"],[class*="company"]')
        if supplier_el: product["company_name"] = supplier_el.get_text(strip=True)[:300]
        text = card.get_text()
        product["origin_country"] = self._country(text)
        certs = ["ISO","CE","FDA","SGS","BV","TUV","RoHS","REACH"]
        product["certifications"] = [c for c in certs if c in text]
        product["verified"] = "verified" in text.lower() or "gold supplier" in text.lower()
        ym = re.search(r"(\d+)\s*(?:years|yrs)", text, re.I)
        if ym: product["supplier_years"] = int(ym.group(1))
        return product

    def _price(self, t): m=re.findall(r'\$?\s*([\d,]+\.?\d*)',t); return float(m[0].replace(",","")) if m else None
    def _num(self, t): m=re.search(r"(\d[\d,]*)",t); return int(m.group(1).replace(",","")) if m else None
    def _country(self, t):
        t=t.lower(); scores={}
        for c,k in {"CN":["china","guangdong","zhejiang"],"TR":["turkey","istanbul","ankara"],"AE":["uae","dubai"]}.items():
            scores[c]=sum(1 for w in k if w in t)
        return max(scores,key=scores.get) if scores and max(scores.values())>0 else "CN"
    def _cat(self, q):
        for k,v in {"steel":"construction_materials","cement":"construction_materials","generator":"power_generation","led":"electrical","medical":"medical","pvc":"construction_materials"}.items():
            if k in q.lower(): return v
        return "general"

    async def search(self, query: str, country: str = None) -> List[Dict]:
        import httpx
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            return await self._search(client, query)
