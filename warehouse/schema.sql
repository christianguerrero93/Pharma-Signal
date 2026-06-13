-- Pharma Signal Enterprise DSP Warehouse Schema
-- Target warehouses: BigQuery, Snowflake, Redshift, or Postgres analytics replica.

CREATE TABLE IF NOT EXISTS dim_organization (
  organization_id VARCHAR(64) PRIMARY KEY,
  organization_name VARCHAR(255) NOT NULL,
  region VARCHAR(64),
  vertical VARCHAR(64),
  compliance_profile TEXT,
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_brand (
  brand_id VARCHAR(64) PRIMARY KEY,
  organization_id VARCHAR(64) NOT NULL,
  brand_name VARCHAR(255) NOT NULL,
  indication VARCHAR(255),
  audience_partition VARCHAR(255),
  status VARCHAR(64),
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_campaign (
  campaign_id VARCHAR(64) PRIMARY KEY,
  organization_id VARCHAR(64) NOT NULL,
  brand_id VARCHAR(64) NOT NULL,
  campaign_name VARCHAR(255) NOT NULL,
  objective TEXT,
  audience_type VARCHAR(64),
  budget NUMERIC(18, 2),
  start_date DATE,
  end_date DATE,
  base_cpm NUMERIC(18, 4),
  target_frequency_weekly INTEGER,
  max_frequency_daily INTEGER,
  outcome_kpi VARCHAR(255),
  status VARCHAR(64),
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_line_item (
  line_item_id VARCHAR(64) PRIMARY KEY,
  campaign_id VARCHAR(64) NOT NULL,
  line_item_name VARCHAR(255),
  channel VARCHAR(64),
  budget NUMERIC(18, 2),
  bid_strategy VARCHAR(128),
  max_bid_cpm NUMERIC(18, 4),
  pacing_mode VARCHAR(64),
  status VARCHAR(64),
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_audience (
  audience_id VARCHAR(64) PRIMARY KEY,
  organization_id VARCHAR(64) NOT NULL,
  audience_name VARCHAR(255),
  audience_type VARCHAR(64),
  source VARCHAR(255),
  estimated_size BIGINT,
  match_rate NUMERIC(9, 4),
  data_cpm NUMERIC(18, 4),
  quality_score NUMERIC(9, 4),
  privacy_posture TEXT,
  activation_allowed BOOLEAN,
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_supply_path (
  supply_path_id VARCHAR(64) PRIMARY KEY,
  partner VARCHAR(255),
  channel VARCHAR(64),
  deal_id VARCHAR(255),
  seller_type VARCHAR(128),
  bid_floor_cpm NUMERIC(18, 4),
  viewability NUMERIC(9, 4),
  fraud_risk NUMERIC(9, 4),
  match_rate NUMERIC(9, 4),
  working_media_ratio NUMERIC(9, 4),
  outcome_score NUMERIC(9, 4),
  status VARCHAR(64),
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_auction_event (
  auction_event_id VARCHAR(64) PRIMARY KEY,
  request_id VARCHAR(128) NOT NULL,
  event_ts TIMESTAMP NOT NULL,
  organization_id VARCHAR(64),
  campaign_id VARCHAR(64),
  line_item_id VARCHAR(64),
  audience_id VARCHAR(64),
  supply_path_id VARCHAR(64),
  creative_id VARCHAR(64),
  channel VARCHAR(64),
  domain_or_app VARCHAR(512),
  floor_cpm NUMERIC(18, 4),
  bid_cpm NUMERIC(18, 4),
  clearing_price_cpm NUMERIC(18, 4),
  decision VARCHAR(64),
  confidence INTEGER,
  audience_match NUMERIC(9, 4),
  contextual_relevance NUMERIC(9, 4),
  outcome_signal NUMERIC(9, 4),
  frequency_seen_today INTEGER,
  blocked_reason TEXT,
  event_payload_json TEXT
);

CREATE TABLE IF NOT EXISTS fact_delivery_daily (
  delivery_date DATE NOT NULL,
  campaign_id VARCHAR(64) NOT NULL,
  line_item_id VARCHAR(64),
  supply_path_id VARCHAR(64),
  audience_id VARCHAR(64),
  impressions BIGINT,
  clicks BIGINT,
  video_completes BIGINT,
  spend NUMERIC(18, 2),
  data_fees NUMERIC(18, 2),
  platform_fees NUMERIC(18, 2),
  working_media NUMERIC(18, 2),
  viewable_impressions BIGINT,
  invalid_traffic_impressions BIGINT,
  PRIMARY KEY (delivery_date, campaign_id, line_item_id, supply_path_id, audience_id)
);

CREATE TABLE IF NOT EXISTS fact_measurement_read (
  measurement_id VARCHAR(64) PRIMARY KEY,
  campaign_id VARCHAR(64) NOT NULL,
  read_date DATE,
  exposed_sample BIGINT,
  control_sample BIGINT,
  exposed_conversions BIGINT,
  control_conversions BIGINT,
  observed_lift NUMERIC(9, 4),
  minimum_detectable_lift NUMERIC(9, 4),
  power_score INTEGER,
  recommendation TEXT,
  methodology VARCHAR(255),
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_audit_event (
  audit_event_id VARCHAR(64) PRIMARY KEY,
  event_ts TIMESTAMP NOT NULL,
  actor VARCHAR(255),
  role VARCHAR(64),
  action VARCHAR(255),
  entity_type VARCHAR(128),
  entity_id VARCHAR(64),
  risk_level VARCHAR(64),
  metadata_json TEXT
);
