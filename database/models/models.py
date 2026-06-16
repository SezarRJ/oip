"""OIP - Database Engine. SQLAlchemy ORM + async pool + repositories."""
import os, uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from sqlalchemy import (Column, Integer, String, Float, Boolean, DateTime, Text,
    Numeric, ForeignKey, Index, create_engine, JSON, BigInteger, CheckConstraint, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID, ARRAY as PG_ARRAY
from sqlalchemy.orm import declarative_base, relationship, Session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.sql import select, update

Base = declarative_base()

class Country(Base):
    __tablename__ = "countries"
    id = Column(Integer, primary_key=True); code = Column(String(2), unique=True, nullable=False)
    name = Column(String(120)); currency = Column(String(3)); risk_base = Column(Float, default=0.30)
    is_source = Column(Boolean, default=False); is_demand = Column(Boolean, default=False)
    active = Column(Boolean, default=True); created_at = Column(DateTime(timezone=True), server_default=func.now())

class Company(Base):
    __tablename__ = "companies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(500), nullable=False); name_ar = Column(String(500)); name_zh = Column(String(500)); name_tr = Column(String(500))
    company_type = Column(String(40)); country_id = Column(Integer, ForeignKey("countries.id"))
    city = Column(String(200)); address = Column(Text); website = Column(String(500))
    email = Column(String(300)); phone = Column(String(100)); whatsapp = Column(String(100))
    employees_estimate = Column(Integer); years_in_business = Column(Integer)
    certifications = Column(PG_ARRAY(String)); reliability_score = Column(Float, default=0)
    verified = Column(Boolean, default=False); source_url = Column(Text); source_name = Column(String(200))
    last_seen = Column(DateTime(timezone=True), default=func.now()); first_seen = Column(DateTime(timezone=True), default=func.now())
    data_quality_score = Column(Float, default=5.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now()); updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    country = relationship("Country"); products = relationship("Product", back_populates="company", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_c_name_gin","name",postgresql_using="gin",postgresql_ops={"name":"gin_trgm_ops"}),)

class Product(Base):
    __tablename__ = "products"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(500), nullable=False); category = Column(String(200)); subcategory = Column(String(200))
    description = Column(Text); specifications = Column(JSON, default=dict); hs_code = Column(String(12))
    moq = Column(Integer); unit = Column(String(50)); unit_price_usd = Column(Numeric(14,2))
    min_bulk_price = Column(Numeric(14,2)); bulk_quantity = Column(Integer)
    lead_time_days = Column(Integer); weight_kg = Column(Numeric(12,3))
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    origin_country_id = Column(Integer, ForeignKey("countries.id")); source_url = Column(Text)
    active = Column(Boolean, default=True); last_price_check = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now()); updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    company = relationship("Company", back_populates="products"); origin_country = relationship("Country")
    __table_args__ = (Index("ix_p_hs","hs_code"),Index("ix_p_cat","category"),Index("ix_p_price","unit_price_usd"))

class ProductPriceHistory(Base):
    __tablename__ = "product_price_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    price_usd = Column(Numeric(14,2), nullable=False); source_url = Column(Text); recorded_at = Column(DateTime(timezone=True), server_default=func.now())

class DemandSignal(Base):
    __tablename__ = "demand_signals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_type = Column(String(40)); title = Column(String(800), nullable=False); description = Column(Text)
    buyer_company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id")); buyer_country_id = Column(Integer, ForeignKey("countries.id"))
    buyer_name = Column(String(500)); products_needed = Column(PG_ARRAY(String)); hs_codes_needed = Column(PG_ARRAY(String))
    estimated_volume = Column(Numeric(14,2)); estimated_budget_usd = Column(Numeric(16,2))
    published_date = Column(DateTime); deadline_date = Column(DateTime); tender_ref = Column(String(200))
    tender_status = Column(String(40)); source_url = Column(Text); source_name = Column(String(200))
    confidence = Column(Float, default=5.0); status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now()); updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    buyer_country = relationship("Country")

class MarketIntel(Base):
    __tablename__ = "market_intel"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intel_type = Column(String(30)); title = Column(String(800), nullable=False); summary = Column(Text)
    url = Column(Text); source_name = Column(String(200)); countries_affected = Column(PG_ARRAY(Integer))
    products_affected = Column(PG_ARRAY(String)); sentiment = Column(String(10)); impact_score = Column(Integer)
    confidence = Column(Float, default=5.0); published_at = Column(DateTime(timezone=True)); collected_at = Column(DateTime(timezone=True), server_default=func.now())

class Opportunity(Base):
    __tablename__ = "opportunities"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_type = Column(String(40), nullable=False); title = Column(String(600), nullable=False); description = Column(Text)
    status = Column(String(20), default="discovered"); source_country_id = Column(Integer, ForeignKey("countries.id"))
    target_country_id = Column(Integer, ForeignKey("countries.id")); product_category = Column(String(200))
    hs_codes_involved = Column(PG_ARRAY(String)); product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    supplier_company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id")); buyer_company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    supplier_name = Column(String(500)); buyer_name = Column(String(500))
    capital_required_usd = Column(Numeric(16,2)); purchase_cost_usd = Column(Numeric(16,2)); shipping_cost_usd = Column(Numeric(14,2))
    insurance_cost_usd = Column(Numeric(12,2)); customs_duty_usd = Column(Numeric(14,2)); taxes_usd = Column(Numeric(14,2))
    handling_cost_usd = Column(Numeric(12,2)); warehousing_cost_usd = Column(Numeric(12,2)); financing_cost_usd = Column(Numeric(12,2))
    brokerage_fee_usd = Column(Numeric(12,2)); total_cost_usd = Column(Numeric(16,2)); expected_revenue_usd = Column(Numeric(16,2))
    expected_commission_usd = Column(Numeric(14,2)); expected_gross_profit = Column(Numeric(14,2)); expected_net_profit = Column(Numeric(14,2))
    expected_roi_pct = Column(Numeric(8,2)); cash_conversion_days = Column(Integer); probability_of_success = Column(Numeric(4,3))
    risk_score = Column(Float); risk_components = Column(JSON, default=dict)
    profit_score = Column(Float); capital_efficiency_score = Column(Float); execution_ease_score = Column(Float)
    speed_score = Column(Float); repeatability_score = Column(Float); scalability_score = Column(Float)
    market_demand_score = Column(Float); supply_constraint_score = Column(Float); competitive_intensity = Column(Float)
    opportunity_score = Column(Float); why_exists = Column(Text); competitor_analysis = Column(Text)
    window_estimate = Column(String(50)); is_repeatable = Column(Boolean, default=False); execution_plan = Column(Text)
    recommended_actions = Column(PG_ARRAY(String)); key_contacts = Column(JSON, default=list)
    supporting_evidence = Column(JSON, default=list); capital_tier = Column(String(20))
    discovered_at = Column(DateTime(timezone=True), server_default=func.now()); last_evaluated = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True)); executed_at = Column(DateTime(timezone=True)); archived_at = Column(DateTime(timezone=True))
    data_sources = Column(PG_ARRAY(String)); confidence = Column(Float, default=5.0)
    rank_position = Column(Integer); rank_category = Column(String(60))
    created_at = Column(DateTime(timezone=True), server_default=func.now()); updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    source_country = relationship("Country", foreign_keys=[source_country_id]); target_country = relationship("Country", foreign_keys=[target_country_id])
    __table_args__ = (Index("ix_opp_score","opportunity_score"),Index("ix_opp_roi","expected_roi_pct"),
        Index("ix_opp_capital","capital_required_usd"),Index("ix_opp_risk","risk_score"),
        Index("ix_opp_tier","capital_tier"),Index("ix_opp_discovered","discovered_at"),
        CheckConstraint("opportunity_score >= 0 AND opportunity_score <= 100"),
        CheckConstraint("risk_score >= 0 AND risk_score <= 100"))

class DailyBriefing(Base):
    __tablename__ = "daily_briefings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4); briefing_date = Column(DateTime, nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    top_zero_capital = Column(PG_ARRAY(UUID(as_uuid=True))); top_under_10k = Column(PG_ARRAY(UUID(as_uuid=True)))
    top_under_50k = Column(PG_ARRAY(UUID(as_uuid=True))); top_under_100k = Column(PG_ARRAY(UUID(as_uuid=True)))
    top_under_500k = Column(PG_ARRAY(UUID(as_uuid=True))); top_under_1m = Column(PG_ARRAY(UUID(as_uuid=True)))
    top_brokerage = Column(PG_ARRAY(UUID(as_uuid=True))); top_trading = Column(PG_ARRAY(UUID(as_uuid=True)))
    top_low_risk = Column(PG_ARRAY(UUID(as_uuid=True))); top_high_margin = Column(PG_ARRAY(UUID(as_uuid=True)))
    top_repeatable = Column(PG_ARRAY(UUID(as_uuid=True))); top_long_term = Column(PG_ARRAY(UUID(as_uuid=True)))
    emerging_3mo = Column(PG_ARRAY(UUID(as_uuid=True))); emerging_6mo = Column(PG_ARRAY(UUID(as_uuid=True)))
    emerging_12mo = Column(PG_ARRAY(UUID(as_uuid=True))); emerging_24mo = Column(PG_ARRAY(UUID(as_uuid=True)))
    total_opportunities = Column(Integer); new_opportunities = Column(Integer); briefing_text = Column(Text); briefing_json = Column(JSON)
    __table_args__ = (UniqueConstraint("briefing_date"),)

class CurrencyRate(Base):
    __tablename__ = "currency_rates"
    id = Column(Integer, primary_key=True); base_currency = Column(String(3), default="USD"); target_currency = Column(String(3), nullable=False)
    rate = Column(Numeric(18,8), nullable=False); source = Column(String(100)); recorded_at = Column(DateTime(timezone=True), server_default=func.now())

# ── DATABASE MANAGER ──
class Database:
    _instance = None
    def __new__(cls): 
        if cls._instance is None: cls._instance = super().__new__(cls)
        return cls._instance

    def init(self, database_url: str = None):
        url = database_url or os.environ.get("DATABASE_URL","postgresql+asyncpg://oip:oip@localhost:5432/oip")
        sync_url = url.replace("+asyncpg","+psycopg2")
        self._engine = create_engine(sync_url, echo=False, pool_size=5)
        self._async_engine = create_async_engine(url, echo=False, pool_size=5)
        self._session_factory = sessionmaker(bind=self._engine)
        self._async_session_factory = async_sessionmaker(self._async_engine, class_=AsyncSession, expire_on_commit=False)
        return self

    def create_all(self): Base.metadata.create_all(self._engine)
    @property
    def session(self) -> Session: return self._session_factory()

    @asynccontextmanager
    async def async_session(self):
        async with self._async_session_factory() as s: yield s

# ── REPOSITORIES ──
class BaseRepository:
    def __init__(self, model, db=None): self.model = model; self.db = db or Database()
    async def get(self, id):
        async with self.db.async_session() as s: return await s.get(self.model, id)
    async def get_by(self, **kwargs):
        async with self.db.async_session() as s:
            r = await s.execute(select(self.model).filter_by(**kwargs)); return r.scalar_one_or_none()
    async def upsert(self, lookup: dict, data: dict):
        existing = await self.get_by(**lookup)
        async with self.db.async_session() as s:
            if existing:
                for k,v in data.items(): setattr(existing,k,v)
                s.add(existing); await s.commit(); await s.refresh(existing); return existing
            obj = self.model(**{**lookup,**data}); s.add(obj); await s.commit(); await s.refresh(obj); return obj
    async def bulk_upsert(self, records: List[Dict], lookup_key: str = "name") -> int:
        new = 0
        for rec in records:
            lv = rec.get(lookup_key)
            if not lv: continue
            async with self.db.async_session() as s:
                r = await s.execute(select(self.model).filter_by(**{lookup_key:lv}))
                existing = r.scalar_one_or_none()
                if existing:
                    for k,v in rec.items(): setattr(existing,k,v)
                    s.add(existing)
                else: s.add(self.model(**rec)); new += 1
                await s.commit()
        return new

class OpportunityRepository(BaseRepository):
    def __init__(self, db=None): super().__init__(Opportunity, db)
    async def find_active(self, limit=100):
        async with self.db.async_session() as s:
            r = await s.execute(select(Opportunity).where(Opportunity.status.in_(("discovered","evaluating","active")))
                .where((Opportunity.expires_at.is_(None))|(Opportunity.expires_at > func.now()))
                .order_by(Opportunity.opportunity_score.desc()).limit(limit))
            return list(r.scalars().all())
    async def find_new_since(self, since):
        async with self.db.async_session() as s:
            r = await s.execute(select(Opportunity).where(Opportunity.discovered_at >= since)
                .order_by(Opportunity.opportunity_score.desc()))
            return list(r.scalars().all())

db = Database()
