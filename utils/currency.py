"""OIP - Currency & Exchange Rate Integration."""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

class CurrencyConverter:
    BASE_RATES = {"USD":1.0,"EUR":0.92,"GBP":0.79,"TRY":32.50,"IQD":1310.0,"SYP":12500.0,"IRR":42000.0,
                  "CNY":7.24,"SAR":3.75,"AED":3.67,"QAR":3.64,"KWD":0.307,"OMR":0.385,"BHD":0.377}
    SYMBOLS = {"USD":"$","EUR":"€","GBP":"£","TRY":"₺","IQD":"د.ع","SYP":"ل.س","IRR":"﷼","CNY":"¥",
               "SAR":"﷼","AED":"د.إ","QAR":"﷼","KWD":"د.ك","OMR":"﷼","BHD":"د.ب"}

    def __init__(self, api_key=None, config=None):
        self.api_key = api_key; self.config = config or {}
        self.last_updated = None; self.rates = dict(self.BASE_RATES)

    async def refresh_rates(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get("https://open.er-api.com/v6/latest/USD")
                if r.status_code==200:
                    d=r.json()
                    if d.get("result")=="success":
                        self.rates=d.get("rates",{}); self.last_updated=datetime.utcnow(); return True
        except: pass
        return False

    def convert(self, amount, fc, tc):
        if fc==tc: return amount
        return (amount/self.rates.get(fc,1.0))*self.rates.get(tc,1.0)

    def to_usd(self, amount, fc):
        return amount if fc=="USD" else amount/self.rates.get(fc,1.0)

    def from_usd(self, amount, tc):
        return amount if tc=="USD" else amount*self.rates.get(tc,1.0)

    def get_volatility(self, currency):
        return {"TRY":0.25,"IQD":0.05,"SYP":0.40,"IRR":0.35,"CNY":0.05,"SAR":0.01,
                "AED":0.01,"QAR":0.01,"KWD":0.03,"OMR":0.01,"BHD":0.01,"EUR":0.05,"GBP":0.07}.get(currency,0.10)

    @property
    def is_stale(self):
        return not self.last_updated or (datetime.utcnow()-self.last_updated)>timedelta(hours=12)

currency = CurrencyConverter()
