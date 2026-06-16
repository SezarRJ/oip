"""OIP - Data Extraction Layer. HTML/text → structured records."""
import re, json
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

class CompanyExtractor:
    EMAIL_RE = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
    PHONE_RE = re.compile(r'\+?[\d\s\-\(\)]{7,20}')

    @classmethod
    def extract(cls, html: str, url: str = "", source_name: str = "") -> Dict[str, Any]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml"); text = soup.get_text(separator=" ", strip=True)
        company = {"name": cls._name(soup, text, url), "company_type": cls._type(text),
            "website": cls._website(soup, url), "email": cls._email(text),
            "phone": cls._phone(text), "address": cls._address(soup, text),
            "city": cls._city(text), "country_code": cls._country(text, url),
            "certifications": cls._certs(text), "employees_estimate": cls._emps(text),
            "years_in_business": cls._years(text), "source_url": url, "source_name": source_name,
            "data_quality_score": 5.0}
        filled = sum(1 for v in [company["email"],company["phone"],company["address"],company["website"]] if v)
        company["data_quality_score"] = min(10.0, 2.0 + filled * 2.0)
        return company

    @classmethod
    def _name(cls, soup, text, url):
        for meta in soup.find_all("meta"):
            if meta.get("property") in ("og:site_name","og:title"):
                n = meta.get("content",""); return n.strip() if n and len(n)<200 else ""
        for tag in soup.find_all(["h1","title"]):
            n = tag.get_text(strip=True)
            if n and 3<len(n)<200: return re.sub(r'\s*[-|]\s*.+$','',n).strip()
        if url:
            d = urlparse(url).netloc; d = re.sub(r'^www\.','',d)
            return d.split('.')[0].replace('-',' ').title()
        return ""

    @classmethod
    def _type(cls, text):
        t=text.lower(); scores={}
        for ct,kw in {"manufacturer":["manufacturer","factory","production","made in","oem"],
                       "wholesaler":["wholesale","bulk supply"],"distributor":["distributor","distribution"],
                       "trader":["trading company","import export"]}.items():
            scores[ct]=sum(1 for w in kw if w in t)
        return max(scores,key=scores.get) if scores and max(scores.values())>0 else "other"

    @classmethod
    def _email(cls, text):
        emails = cls.EMAIL_RE.findall(text)
        biz = [e for e in emails if not any(g in e.lower() for g in ["gmail","yahoo","hotmail","outlook"])]
        return (biz[0] if biz else emails[0]) if emails else ""

    @classmethod
    def _phone(cls, text):
        phones = cls.PHONE_RE.findall(text); return phones[0].strip() if phones else ""

    @classmethod
    def _website(cls, soup, fb):
        c = soup.find("link",rel="canonical")
        if c and c.get("href"): return c["href"]
        for m in soup.find_all("meta"):
            if m.get("property")=="og:url": return m.get("content","")
        return fb

    @classmethod
    def _address(cls, soup, text):
        m = re.search(r'(?:address|location|headquarters?)[:\s]+(.+?)(?:\n|$)', text, re.I)
        if m: return m.group(1).strip()[:500]
        return ""

    @classmethod
    def _city(cls, text):
        for city in ["Istanbul","Ankara","Izmir","Baghdad","Erbil","Basra","Dubai","Abu Dhabi","Riyadh","Jeddah","Doha","Kuwait City","Muscat","Manama","Guangzhou","Shenzhen","Shanghai","Tehran","Damascus"]:
            if city.lower() in text.lower(): return city
        return ""

    @classmethod
    def _country(cls, text, url):
        t=text.lower(); d=urlparse(url).netloc.lower()
        for tld,code in {".tr":"TR",".iq":"IQ",".ir":"IR",".sa":"SA",".ae":"AE",".qa":"QA",".kw":"KW",".om":"OM",".bh":"BH",".cn":"CN",".sy":"SY"}.items():
            if d.endswith(tld): return code
        scores={}
        for code,kw in {"TR":["turkey","turkish","istanbul"],"IQ":["iraq","baghdad","erbil"],
                         "CN":["china","chinese","guangdong"],"AE":["uae","dubai"],
                         "SA":["saudi","riyadh"],"QA":["qatar","doha"],"KW":["kuwait"],
                         "OM":["oman","muscat"],"BH":["bahrain"]}.items():
            scores[code]=sum(1 for w in kw if w in t)
        return max(scores,key=scores.get) if scores and max(scores.values())>0 else ""

    @classmethod
    def _certs(cls, text):
        return [c for c in ["ISO 9001","ISO 14001","CE","FDA","SGS","BV","TUV","RoHS","REACH","OEKO-TEX","GMP","HACCP","API","ASME"] if c.lower() in text.lower()]

    @classmethod
    def _emps(cls, text):
        for p in [r'(\d[\d,]*)\s*\+?\s*employees?',r'(\d[\d,]*)\s*\+?\s*workers?']:
            m=re.search(p,text,re.I)
            if m: return int(m.group(1).replace(",",""))
        return None

    @classmethod
    def _years(cls, text):
        for p in [r'(?:established|founded|since)\s*(?:in\s*)?(\d{4})',r'(\d+)\s*(?:years|yrs)\s*(?:of\s*)?(?:experience|in\s*business)']:
            m=re.search(p,text,re.I)
            if m:
                y=int(m.group(1))
                return datetime.now().year-y if y>1900 else y
        return None

from datetime import datetime

class ProductExtractor:
    PRICE_RE = re.compile(r'[\$\€\£\¥]\s*([\d,]+\.?\d*)')
    MOQ_RE = re.compile(r'(?:MOQ|min\.?\s*order|minimum\s*order)[:\s]*(\d[\d,]*)', re.I)

    @classmethod
    def extract(cls, html: str, url: str = "", source_name: str = "") -> Dict[str, Any]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml"); text = soup.get_text(separator=" ", strip=True)
        return {"name": cls._name(soup, text), "category": cls._cat(text),
            "description": cls._desc(soup, text), "unit_price_usd": cls._price(text),
            "moq": cls._moq(text), "unit": cls._unit(text),
            "lead_time_days": cls._lead(text), "weight_kg": cls._weight(text),
            "specifications": cls._specs(soup), "hs_code": cls._hs(text),
            "source_url": url, "source_name": source_name}

    @classmethod
    def _name(cls, soup, text):
        for sel in ["h1",'[class*="product-title"]','[class*="product-name"]']:
            el = soup.select_one(sel)
            if el: return el.get_text(strip=True)[:500]
        return ""

    @classmethod
    def _cat(cls, text):
        t=text.lower()
        for cat,kw in {"construction_materials":["steel","cement","concrete","rebar","tile","pipe"],
                        "medical":["medical","surgical","hospital","scrub","glove"],
                        "electrical":["cable","wire","lighting","led"],
                        "power_generation":["generator","solar","turbine"],
                        "hvac":["air condition","hvac","ventilation","chiller"],
                        "industrial_equipment":["machinery","pump","motor","compressor"]}.items():
            if any(w in t for w in kw): return cat
        return "general"

    @classmethod
    def _desc(cls, soup, text):
        for sel in ['[class*="description"]','[class*="detail"]','article']:
            el = soup.select_one(sel)
            if el: return el.get_text(strip=True)[:2000]
        return text[:2000]

    @classmethod
    def _price(cls, text):
        m=cls.PRICE_RE.findall(text); return float(m[0].replace(",","")) if m else None

    @classmethod
    def _moq(cls, text):
        m=cls.MOQ_RE.search(text); return int(m.group(1).replace(",","")) if m else None

    @classmethod
    def _unit(cls, text):
        for u in ["ton","kg","piece","set","meter","square meter","roll","carton","pallet"]:
            if u in text.lower(): return u
        return "piece"

    @classmethod
    def _lead(cls, text):
        for p in [r'lead\s*time[:\s]*(\d+)\s*(?:day|d)',r'delivery[:\s]*(\d+)\s*(?:day|d)']:
            m=re.search(p,text,re.I)
            if m: return int(m.group(1))
        return None

    @classmethod
    def _weight(cls, text):
        m=re.search(r'(\d+\.?\d*)\s*(kg|kilogram|ton|g)',text,re.I)
        if m:
            v=float(m.group(1)); u=m.group(2).lower()
            return round(v*{"ton":1000,"g":0.001,"kg":1}.get(u,1),3)
        return None

    @classmethod
    def _specs(cls, soup):
        specs={}
        for row in soup.select("tr"):
            cells=row.find_all(["td","th"])
            if len(cells)>=2: specs[cells[0].get_text(strip=True).rstrip(":")]=cells[1].get_text(strip=True)
        return specs

    @classmethod
    def _hs(cls, text):
        t=text.lower()
        for code,kw in {"72142000":["steel rebar","reinforcing bar"],"25232900":["cement","portland"],
                         "69072100":["ceramic tile","floor tile"],"39172300":["pvc pipe","plastic pipe"],
                         "85021100":["diesel generator"],"94054090":["led light","lighting fixture"],
                         "62114300":["medical scrub","surgical gown"],"85444920":["electrical cable","copper wire"],
                         "84137010":["water pump"],"94029000":["hospital bed","medical furniture"]}.items():
            if any(w in t for w in kw): return code
        return ""

class DemandSignalExtractor:
    @classmethod
    def extract(cls, html: str, url: str = "", source_name: str = "") -> Dict[str, Any]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml"); text = soup.get_text(separator=" ", strip=True)
        return {"signal_type": cls._type(text),"title": cls._title(soup, text),
            "description": cls._desc(soup, text),"buyer_name": cls._buyer(text),
            "buyer_country": CompanyExtractor._country(text, url),
            "products_needed": cls._prods(text),"estimated_budget_usd": cls._budget(text),
            "deadline_date": cls._deadline(text),"tender_ref": cls._ref(text),
            "tender_status": cls._status(text),"source_url": url,"source_name": source_name,"confidence":0.60}

    @classmethod
    def _type(cls, text):
        t=text.lower()
        for st,kw in {"tender":["tender","bid","invitation to tender"],"rfq":["rfq","request for quote"],
                       "procurement_notice":["procurement","purchase notice"],
                       "infrastructure_project":["infrastructure","road construc"],
                       "energy_project":["power plant","solar farm","oil and gas"],
                       "healthcare_project":["hospital","healthcare","medical center"]}.items():
            if any(w in t for w in kw): return st
        return "procurement_notice"

    @classmethod
    def _title(cls, soup, text):
        for sel in ["h1",'[class*="title"]','[class*="heading"]']:
            el=soup.select_one(sel)
            if el: return el.get_text(strip=True)[:800]
        return text.split("\\n")[0][:800] if text else ""

    @classmethod
    def _desc(cls, soup, text):
        for sel in ['[class*="description"]',"article","main"]:
            el=soup.select_one(sel)
            if el: return el.get_text(strip=True)[:3000]
        return text[:3000]

    @classmethod
    def _buyer(cls, text):
        m=re.search(r'(?:contracting\s*authority|buyer|purchaser|employer)[:\s]+([A-Z][\w\s&]+?)(?:\n|\.|,)',text,re.I)
        return m.group(1).strip()[:500] if m else ""

    @classmethod
    def _prods(cls, text):
        t=text.lower()
        return [p for p in ["steel","cement","concrete","rebar","pipe","cable","wire","generator","transformer",
                "pump","valve","medical equipment","hospital furniture","construction material",
                "hvac","air conditioning","safety equipment","vehicle","machinery"] if p in t]

    @classmethod
    def _budget(cls, text):
        m=re.search(r'(?:budget|estimated\s*cost|value)[:\s]*[\$\€\£]?\s*([\d,]+\.?\d*)',text,re.I)
        return float(m.group(1).replace(",","")) if m else None

    @classmethod
    def _deadline(cls, text):
        m=re.search(r'(?:deadline|closing\s*date|submission\s*date)[:\s]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',text,re.I)
        return m.group(1) if m else None

    @classmethod
    def _ref(cls, text):
        m=re.search(r'(?:reference|ref|tender\s*no)[:\s]*([\w\/-]+)',text,re.I)
        return m.group(1) if m else ""

    @classmethod
    def _status(cls, text):
        t=text.lower()
        if "closed" in t or "awarded" in t: return "closed"
        if "closing soon" in t or "deadline" in t: return "closing_soon"
        if "cancel" in t: return "cancelled"
        return "open"
