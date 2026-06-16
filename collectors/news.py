"""
News & Market Intelligence Collector. Business news from Reuters, Trade Arabia etc.
"""
import asyncio, re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from data_collection.collectors.base import BaseCollector, CollectionResult, SourceType, Frequency

class NewsCollector(BaseCollector):
    source_name = "news_intelligence"
    source_type = SourceType.NEWS_SOURCE
    frequency = Frequency.HOURLY
    target_countries = ["IQ","SA","AE","QA","KW","OM","BH","SY","IR","TR"]

    OPPORTUNITY_KW = [
        ("construction project","infrastructure_announcement"),("new hospital","healthcare_project"),
        ("tender announced","tender"),("procurement notice","procurement_notice"),
        ("shortage of","market_shortage"),("supply disruption","market_shortage"),
        ("price surge","price_surge"),("import ban lifted","regulation_change"),
        ("tariff reduced","tariff_change"),("sanctions eased","sanctions_update"),
        ("currency devaluation","currency_event"),("reconstruction contract","reconstruction_need"),
        ("rebuilding effort","reconstruction_need"),("supplier registration","procurement_notice"),
        ("hospital construction","healthcare_project"),("power plant","energy_project"),
        ("solar project","energy_project"),("real estate development","real_estate_project"),
        ("oil and gas project","energy_project"),("hotel development","tourism_project"),
    ]
    COUNTRY_PATTERNS = {
        "IQ":[r"iraq",r"baghdad",r"erbil",r"basra"],"SA":[r"saudi",r"riyadh",r"neom"],
        "AE":[r"uae",r"dubai",r"emirates"],"QA":[r"qatar",r"doha"],
        "KW":[r"kuwait"],"OM":[r"oman",r"muscat"],"BH":[r"bahrain"],
        "SY":[r"syria",r"damascus",r"aleppo"],"IR":[r"iran",r"tehran"],
        "TR":[r"turkey",r"turkish",r"istanbul",r"ankara"],
    }
    NEWS_SOURCES = [
        {"name":"Trade Arabia","url":"https://www.tradearabia.com","region":"mena"},
        {"name":"Reuters ME","url":"https://www.reuters.com/world/middle-east/","region":"mena"},
        {"name":"Iraq Business News","url":"https://www.iraq-businessnews.com","region":"iq"},
    ]

    def __init__(self, config=None):
        super().__init__(config)
        self.request_delay = 1.0
    def can_collect(self) -> bool: return True

    async def collect(self) -> CollectionResult:
        result = CollectionResult(source_name=self.source_name, source_type=self.source_type, started_at=datetime.utcnow())
        import httpx
        from bs4 import BeautifulSoup
        async with httpx.AsyncClient(headers={"User-Agent":"Mozilla/5.0","Accept":"text/html"}, timeout=20.0, follow_redirects=True) as client:
            for source in self.NEWS_SOURCES:
                try:
                    resp = await client.get(source["url"])
                    if resp.status_code != 200: continue
                    soup = BeautifulSoup(resp.text,"lxml")
                    for card in soup.select("article,.article,.story,.news-item,h2 a,h3 a")[:30]:
                        title_el = card.select_one("h1,h2,h3,a") if card.name in ("article","div") else card
                        link = card.select_one("a") or card
                        title = title_el.get_text(strip=True) if title_el else ""
                        href = link.get("href","") if link else ""
                        if not title or len(title) < 15: continue
                        intel = self._to_intel(title, href, source)
                        if intel:
                            result.market_intel.append(intel)
                            result.items_collected += 1
                except Exception as e: result.errors.append(f"{source['name']}: {e}")
                await asyncio.sleep(self.request_delay)
        result.completed_at = datetime.utcnow()
        return result

    def _to_intel(self, title, url, source):
        t=title.lower()
        countries=[]; scores={}
        for c,ps in self.COUNTRY_PATTERNS.items():
            scores[c]=sum(1 for p in ps if re.search(p,t))
        countries=[c for c,s in scores.items() if s>0]
        if not countries: return None
        itype="news"; sentiment="neutral"; impact=30
        for kw,it in self.OPPORTUNITY_KW:
            if kw in t:
                itype=it; sentiment="opportunity"; impact=min(100,impact+30)
                break
        prods=[p for p in ["steel","cement","generator","medical","construction","oil","power","water","food"] if p in t]
        urg_words=["urgent","emergency","immediate","critical","deadline"]
        if any(w in t for w in urg_words): impact=min(100,impact+15)
        return {"intel_type":itype,"title":title[:800],"summary":title,"url":url,
                "source_name":source["name"],"countries_affected":countries,
                "products_affected":prods,"sentiment":sentiment,
                "impact_score":impact,"confidence":0.65,"published_at":datetime.utcnow()}

    async def search(self, query, country=None):
        r = await self.collect()
        if country: return [i for i in r.market_intel if country in i.get("countries_affected",[])]
        return r.market_intel
