-- Phase 3 — ví dụ marts tối thiểu (chạy trong BigQuery Console)
-- Thay project_id nếu khác
CREATE OR REPLACE TABLE `project-6fe3973c-4db8-4b72-83b.marts.demo_revenue_by_state` AS
SELECT
  c.customer_state AS state,
  SUM(i.price) AS revenue_items
FROM `project-6fe3973c-4db8-4b72-83b.staging.stg_items` AS i
JOIN `project-6fe3973c-4db8-4b72-83b.staging.stg_orders` AS o
  ON i.order_id = o.order_id
JOIN `project-6fe3973c-4db8-4b72-83b.staging.stg_customers` AS c
  ON o.customer_id = c.customer_id
GROUP BY 1;

-- SELECT * FROM `project-6fe3973c-4db8-4b72-83b.marts.demo_revenue_by_state` LIMIT 20;
