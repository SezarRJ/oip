-- OPPORTUNITY INTELLIGENCE PLATFORM (OIP)
-- Complete PostgreSQL Schema (15+)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- COUNTRIES
CREATE TABLE countries (
    id          SERIAL PRIMARY KEY,
    code        CHAR(2) UNIQUE NOT NULL,
    name        VARCHAR(120) NOT NULL,
    currency    CHAR(3) NOT NULL,
    region      VARCHAR(80),
    risk_base   NUMERIC(4,3) DEFAULT 0.30,
    is_source   BOOLEAN DEFAULT false,
    is_demand   BOOLEAN DEFAULT false,
    active      BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- COMPANIES
CREATE TABLE companies (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(500) NOT NULL,
    name_ar             VARCHAR(500),
    name_zh             VARCHAR(500),
    name_tr             VARCHAR(500),
    company_type        VARCHAR(40) CHECK (company_type IN (
        'manufacturer','wholesaler','distributor','retailer',
        'trader','broker','procurement_agent','exporter',
        'importer','logistics_provider','government_entity',
        'project_owner','tender_issuer','other'
    )),
    country_id          INT REFERENCES countries(id),
    city                VARCHAR(200),
    address             TEXT,
    latitude            NUMERIC(10,7),
    longitude           NUMERIC(10,7),
    location            GEOGRAPHY(Point, 4326),
    website             VARCHAR(500),
    email               VARCHAR(300),
    phone               VARCHAR(100),
    whatsapp            VARCHAR(100),
    social_links        JSONB DEFAULT '{}',
    employees_estimate  INT,
    annual_revenue_usd  BIGINT,
    years_in_business   INT,
    certifications      TEXT[],
    reliability_score   NUMERIC(3,1) DEFAULT 0,
    verified            BOOLEAN DEFAULT false,
    source_url          TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_companies_country ON companies(country_id);
CREATE INDEX idx_companies_type ON companies(company_type);
CREATE INDEX idx_companies_name_trgm ON companies USING GIN (name gin_trgm_ops);
CREATE INDEX idx_companies_location ON companies USING GIST (location);

-- DECISION MAKERS
CREATE TABLE decision_makers (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id  UUID REFERENCES companies(id) ON DELETE CASCADE,
    name        VARCHAR(300),
    title       VARCHAR(300),
    department  VARCHAR(200),
    email       VARCHAR(300),
    phone       VARCHAR(100),
    linkedin    VARCHAR(500),
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- PRODUCTS
CREATE TABLE products (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(500) NOT NULL,
    name_ar         VARCHAR(500),
    name_zh         VARCHAR(500),
    name_tr         VARCHAR(500),
    category        VARCHAR(200),
    subcategory     VARCHAR(200),
    description     TEXT,
    specifications  JSONB DEFAULT '{}',
    hs_code         VARCHAR(12),
    moq             INT,
    unit            VARCHAR(50),
    unit_price_usd  NUMERIC(14,2),
    min_bulk_price  NUMERIC(14,2),
    lead_time_days  INT,
    weight_kg       NUMERIC(12,3),
    company_id      UUID REFERENCES companies(id),
    origin_country_id INT REFERENCES countries(id),
    source_url      TEXT,
    active          BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_products_hs ON products(hs_code);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_price ON products(unit_price_usd);

-- PRODUCT PRICE HISTORY
CREATE TABLE product_price_history (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id  UUID REFERENCES products(id) ON DELETE CASCADE,
    price_usd   NUMERIC(14,2) NOT NULL,
    source_url  TEXT,
    recorded_at TIMESTAMPTZ DEFAULT now()
);

-- DEMAND SIGNALS
CREATE TABLE demand_signals (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_type         VARCHAR(40) CHECK (signal_type IN (
        'rfq','tender','procurement_notice','project_requirement',
        'buyer_inquiry','market_demand','reconstruction_need',
        'infrastructure_project','industrial_project','energy_project',
        'healthcare_project','education_project','tourism_project',
        'real_estate_project','hotel_project','port_project',
        'special_economic_zone','industrial_park'
    )),
    title               VARCHAR(800) NOT NULL,
    description         TEXT,
    buyer_company_id    UUID REFERENCES companies(id),
    buyer_country_id    INT REFERENCES countries(id),
    buyer_name          VARCHAR(500),
    products_needed     TEXT[],
    hs_codes_needed     VARCHAR(12)[],
    estimated_volume    NUMERIC(14,2),
    estimated_budget_usd NUMERIC(16,2),
    published_date      DATE,
    deadline_date       DATE,
    tender_ref          VARCHAR(200),
    tender_status       VARCHAR(40) CHECK (tender_status IN (
        'announced','open','closing_soon','closed','awarded','cancelled'
    )),
    source_url          TEXT,
    confidence          NUMERIC(3,1) DEFAULT 5.0,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_demand_type ON demand_signals(signal_type);
CREATE INDEX idx_demand_country ON demand_signals(buyer_country_id);
CREATE INDEX idx_demand_deadline ON demand_signals(deadline_date);

-- MARKET INTELLIGENCE
CREATE TABLE market_intel (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    intel_type      VARCHAR(30) CHECK (intel_type IN (
        'news','report','regulation_change','economic_indicator',
        'industry_trend','trade_policy','tariff_change',
        'infrastructure_announcement','market_shortage',
        'price_surge','sanctions_update','currency_event'
    )),
    title           VARCHAR(800) NOT NULL,
    summary         TEXT,
    url             TEXT,
    source_name     VARCHAR(200),
    countries_affected INT[],
    hs_codes_affected  VARCHAR(12)[],
    products_affected  TEXT[],
    sentiment       VARCHAR(10) CHECK (sentiment IN ('positive','negative','neutral','opportunity','threat')),
    impact_score    INT CHECK (impact_score >= 0 AND impact_score <= 100),
    published_at    TIMESTAMPTZ,
    collected_at    TIMESTAMPTZ DEFAULT now()
);

-- SHIPPING ROUTES
CREATE TABLE shipping_routes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    origin_country_id   INT REFERENCES countries(id),
    dest_country_id     INT REFERENCES countries(id),
    mode                VARCHAR(20) CHECK (mode IN ('sea','air','land','multimodal')),
    transit_time_days   INT,
    cost_per_container  NUMERIC(12,2),
    cost_per_kg         NUMERIC(10,4),
    container_type      VARCHAR(20) DEFAULT '20GP',
    reliability_score   NUMERIC(3,1),
    last_updated        TIMESTAMPTZ DEFAULT now()
);

-- CUSTOMS RATES
CREATE TABLE customs_rates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    origin_country  INT REFERENCES countries(id),
    dest_country    INT REFERENCES countries(id),
    hs_code         VARCHAR(12),
    duty_rate_pct   NUMERIC(6,3),
    vat_rate_pct    NUMERIC(6,3),
    additional_taxes JSONB DEFAULT '{}',
    trade_agreement  VARCHAR(200),
    last_verified    TIMESTAMPTZ DEFAULT now()
);

-- OPPORTUNITIES (Core Table)
CREATE TABLE opportunities (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    opportunity_type        VARCHAR(40) NOT NULL,
    title                   VARCHAR(600) NOT NULL,
    description             TEXT,
    status                  VARCHAR(20) DEFAULT 'discovered',
    source_country_id       INT REFERENCES countries(id),
    target_country_id       INT REFERENCES countries(id),
    product_category        VARCHAR(200),
    hs_codes_involved       VARCHAR(12)[],
    product_id              UUID REFERENCES products(id),
    supplier_company_id     UUID REFERENCES companies(id),
    buyer_company_id        UUID REFERENCES companies(id),
    capital_required_usd    NUMERIC(16,2),
    purchase_cost_usd       NUMERIC(16,2),
    shipping_cost_usd       NUMERIC(14,2),
    insurance_cost_usd      NUMERIC(12,2),
    customs_duty_usd        NUMERIC(14,2),
    taxes_usd               NUMERIC(14,2),
    handling_cost_usd       NUMERIC(12,2),
    warehousing_cost_usd    NUMERIC(12,2),
    financing_cost_usd      NUMERIC(12,2),
    total_cost_usd          NUMERIC(16,2),
    expected_revenue_usd    NUMERIC(16,2),
    expected_commission_usd NUMERIC(14,2),
    expected_net_profit     NUMERIC(14,2),
    expected_roi_pct        NUMERIC(8,2),
    cash_conversion_days    INT,
    probability_of_success  NUMERIC(4,3),
    risk_score              NUMERIC(4,1) CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_components         JSONB DEFAULT '{}',
    opportunity_score       NUMERIC(4,1) CHECK (opportunity_score >= 0 AND opportunity_score <= 100),
    why_exists              TEXT,
    competitor_analysis     TEXT,
    window_estimate         VARCHAR(50),
    is_repeatable           BOOLEAN DEFAULT false,
    execution_plan          TEXT,
    recommended_actions     TEXT[],
    key_contacts            JSONB DEFAULT '[]',
    supporting_evidence     JSONB DEFAULT '[]',
    capital_tier            VARCHAR(20),
    discovered_at           TIMESTAMPTZ DEFAULT now(),
    expires_at              TIMESTAMPTZ,
    rank_position           INT,
    created_at              TIMESTAMPTZ DEFAULT now(),
    updated_at              TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_opp_type ON opportunities(opportunity_type);
CREATE INDEX idx_opp_score ON opportunities(opportunity_score DESC);
CREATE INDEX idx_opp_roi ON opportunities(expected_roi_pct DESC);
CREATE INDEX idx_opp_capital ON opportunities(capital_required_usd);
CREATE INDEX idx_opp_tier ON opportunities(capital_tier);
CREATE INDEX idx_opp_risk ON opportunities(risk_score);
CREATE INDEX idx_opp_repeatable ON opportunities(is_repeatable) WHERE is_repeatable = true;

-- DAILY BRIEFINGS
CREATE TABLE daily_briefings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    briefing_date   DATE NOT NULL,
    generated_at    TIMESTAMPTZ DEFAULT now(),
    top_zero_capital       UUID[],
    top_under_10k          UUID[],
    top_under_50k          UUID[],
    top_under_100k         UUID[],
    top_under_500k         UUID[],
    top_under_1m           UUID[],
    top_brokerage          UUID[],
    top_trading            UUID[],
    top_low_risk           UUID[],
    top_high_margin        UUID[],
    top_repeatable         UUID[],
    top_long_term          UUID[],
    emerging_3mo           UUID[],
    emerging_6mo           UUID[],
    emerging_12mo          UUID[],
    emerging_24mo          UUID[],
    total_opportunities    INT,
    new_opportunities      INT,
    briefing_text          TEXT,
    briefing_json          JSONB
);

CREATE UNIQUE INDEX idx_briefing_date ON daily_briefings(briefing_date);

-- CURRENCY RATES
CREATE TABLE currency_rates (
    id              SERIAL PRIMARY KEY,
    base_currency   CHAR(3) NOT NULL DEFAULT 'USD',
    target_currency CHAR(3) NOT NULL,
    rate            NUMERIC(18,8) NOT NULL,
    recorded_at     TIMESTAMPTZ DEFAULT now()
);

-- MATERIALIZED VIEW
CREATE MATERIALIZED VIEW mv_ranked_opportunities AS
SELECT
    id, opportunity_type, title, source_country_id, target_country_id,
    capital_required_usd, expected_net_profit, expected_roi_pct,
    probability_of_success, risk_score, opportunity_score,
    capital_tier, is_repeatable, discovered_at,
    ROW_NUMBER() OVER (ORDER BY opportunity_score DESC) as global_rank,
    ROW_NUMBER() OVER (PARTITION BY capital_tier ORDER BY opportunity_score DESC) as tier_rank
FROM opportunities
WHERE status IN ('discovered', 'evaluating', 'active')
  AND (expires_at IS NULL OR expires_at > now());

-- FUNCTIONS
CREATE OR REPLACE FUNCTION get_capital_tier(amount NUMERIC)
RETURNS VARCHAR(20) AS $$
BEGIN
    RETURN CASE
        WHEN amount = 0 THEN 'Zero Capital'
        WHEN amount <= 10000 THEN 'Micro'
        WHEN amount <= 50000 THEN 'Small'
        WHEN amount <= 100000 THEN 'Medium'
        WHEN amount <= 500000 THEN 'Large'
        WHEN amount <= 1000000 THEN 'Major'
        ELSE 'Mega'
    END;
END;
$$ LANGUAGE plpgsql;

-- UPDATED_AT TRIGGER
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_companies_updated BEFORE UPDATE ON companies FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_products_updated BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_opportunities_updated BEFORE UPDATE ON opportunities FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_demand_signals_updated BEFORE UPDATE ON demand_signals FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE FUNCTION set_capital_tier_trigger()
RETURNS TRIGGER AS $$
BEGIN
    NEW.capital_tier := get_capital_tier(COALESCE(NEW.capital_required_usd, 0));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_opp_capital_tier BEFORE INSERT OR UPDATE OF capital_required_usd ON opportunities
    FOR EACH ROW EXECUTE FUNCTION set_capital_tier_trigger();
