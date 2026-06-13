-- Pharma Signal Enterprise DSP Sample Warehouse Queries

-- 1. Working media efficiency by supply partner
SELECT
  sp.partner,
  sp.channel,
  SUM(d.spend) AS total_spend,
  SUM(d.working_media) AS working_media,
  ROUND(SUM(d.working_media) / NULLIF(SUM(d.spend), 0), 4) AS working_media_ratio,
  SUM(d.impressions) AS impressions,
  ROUND(SUM(d.spend) / NULLIF(SUM(d.impressions), 0) * 1000, 2) AS effective_cpm
FROM fact_delivery_daily d
JOIN dim_supply_path sp ON d.supply_path_id = sp.supply_path_id
GROUP BY sp.partner, sp.channel
ORDER BY working_media_ratio DESC;

-- 2. Campaign measurement readiness
SELECT
  c.campaign_name,
  c.outcome_kpi,
  m.exposed_sample,
  m.control_sample,
  m.power_score,
  m.minimum_detectable_lift,
  m.recommendation
FROM fact_measurement_read m
JOIN dim_campaign c ON m.campaign_id = c.campaign_id
ORDER BY m.power_score DESC;

-- 3. Auction no-bid and block reasons
SELECT
  decision,
  blocked_reason,
  COUNT(*) AS auction_count,
  ROUND(AVG(confidence), 1) AS avg_confidence,
  ROUND(AVG(floor_cpm), 2) AS avg_floor_cpm,
  ROUND(AVG(bid_cpm), 2) AS avg_bid_cpm
FROM fact_auction_event
GROUP BY decision, blocked_reason
ORDER BY auction_count DESC;

-- 4. Frequency pressure by campaign and audience
SELECT
  c.campaign_name,
  a.audience_name,
  AVG(e.frequency_seen_today) AS avg_frequency_seen_today,
  MAX(c.max_frequency_daily) AS campaign_daily_cap,
  COUNT(*) AS bid_requests
FROM fact_auction_event e
JOIN dim_campaign c ON e.campaign_id = c.campaign_id
JOIN dim_audience a ON e.audience_id = a.audience_id
GROUP BY c.campaign_name, a.audience_name
HAVING AVG(e.frequency_seen_today) >= MAX(c.max_frequency_daily) * 0.75
ORDER BY avg_frequency_seen_today DESC;

-- 5. CEO-level media investment scoreboard
SELECT
  b.brand_name,
  c.campaign_name,
  SUM(d.spend) AS spend,
  SUM(d.working_media) AS working_media,
  ROUND(SUM(d.working_media) / NULLIF(SUM(d.spend), 0), 4) AS working_media_ratio,
  MAX(m.power_score) AS measurement_power_score,
  MAX(m.observed_lift) AS observed_lift,
  COUNT(DISTINCT d.supply_path_id) AS supply_paths_used
FROM fact_delivery_daily d
JOIN dim_campaign c ON d.campaign_id = c.campaign_id
JOIN dim_brand b ON c.brand_id = b.brand_id
LEFT JOIN fact_measurement_read m ON c.campaign_id = m.campaign_id
GROUP BY b.brand_name, c.campaign_name
ORDER BY spend DESC;
