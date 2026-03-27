**Lộ trình học + file notes đã chỉnh theo repo:** [notes/README.md](README.md)

---

PHASE 0 – SETUP (Tuần 1, ngày 1-3)
Ngày 1 – GCP + Dataset
text
GCP:
□ Tạo project mới: personal-data-platform
□ Enable APIs: BigQuery, Cloud Storage, Compute Engine
□ Tạo GCS bucket: gs://personal-data-platform-raw
□ gcloud auth application-default set-quota-project YOUR_PROJECT_ID

Download & Upload:
□ Kaggle → download Olist (9 CSV files)
□ Upload lên GCS:
  gsutil cp *.csv gs://personal-data-platform-raw/raw/olist/
□ Verify trên GCP Console → Storage → thấy 9 files
Ngày 2 – Local Environment
text
□ Python 3.11 + venv
  python -m venv .venv
  .venv\Scripts\Activate.ps1

□ Install packages:
  pip install pandas google-cloud-bigquery \
              google-cloud-storage db-dtypes \
              sqlalchemy pyarrow

□ VS Code extensions:
  - Python
  - SQLTools + SQLTools BigQuery Driver
  - dbt Power User

□ Test connection:
  from google.cloud import bigquery
  client = bigquery.Client(project="YOUR_PROJECT_ID")
  print(client.list_datasets())  # không lỗi là OK
Ngày 3 – GitHub Setup
text
□ Tạo repo: personal-data-platform
□ Cấu trúc thư mục:
  personal-data-platform/
  ├── README.md
  ├── .gitignore          ← thêm: *.json, .env, __pycache__
  ├── pipeline/
  ├── dbt/
  ├── ml/
  │   ├── notebooks/
  │   └── src/
  ├── streaming/
  └── dashboard/
      └── screenshots/

□ .gitignore quan trọng — KHÔNG commit credentials:
  application_default_credentials.json
  *.json
  .env
PHASE 1 – DATA MODELING & BI (Tuần 1-4)
Tuần 1 – Hiểu Data + ERD
Ngày 1-2: Đọc hiểu 9 bảng

Mở Jupyter notebook, đọc từng bảng:

python
# notebooks/01_explore.ipynb
import pandas as pd
from google.cloud import storage

# Đọc thẳng từ GCS
def read_gcs(filename):
    return pd.read_csv(
        f"gs://personal-data-platform-raw/raw/olist/{filename}"
    )

orders      = read_gcs("olist_orders_dataset.csv")
items       = read_gcs("olist_order_items_dataset.csv")
customers   = read_gcs("olist_customers_dataset.csv")
products    = read_gcs("olist_products_dataset.csv")
sellers     = read_gcs("olist_sellers_dataset.csv")
payments    = read_gcs("olist_order_payments_dataset.csv")
reviews     = read_gcs("olist_order_reviews_dataset.csv")
geo         = read_gcs("olist_geolocation_dataset.csv")
translation = read_gcs("product_category_name_translation.csv")

# Với mỗi bảng, chạy:
print(orders.shape)
print(orders.dtypes)
print(orders.isnull().sum())
print(orders.head(3))
Câu hỏi cần trả lời sau khi đọc xong:

text
□ orders join items qua cột gì?
□ 1 order có thể có bao nhiêu items?
□ 1 order có thể có bao nhiêu payments?
□ Null ở đâu nhiều nhất?
□ Date columns có format gì?
□ geolocation bảng có bao nhiêu dòng? (hint: ~1M)
Ngày 3: Vẽ ERD

Vẽ tay hoặc dùng dbdiagram.io (free):

text
orders (order_id PK, customer_id FK, status, 
        purchase_ts, approved_ts, 
        delivered_carrier_ts, delivered_customer_ts,
        estimated_delivery_ts)

order_items (order_id FK, order_item_id, product_id FK,
             seller_id FK, price, freight_value)

order_payments (order_id FK, payment_sequential,
                payment_type, installments, value)

order_reviews (review_id PK, order_id FK, score,
               comment_title, comment_message,
               creation_date, answer_ts)

customers (customer_id PK, unique_id, zip_code,
           city, state)

products (product_id PK, category_name, name_length,
          description_length, photos_qty,
          weight_g, length_cm, height_cm, width_cm)

sellers (seller_id PK, zip_code, city, state)

geolocation (zip_code, lat, lng, city, state)

translation (category_name, category_name_english)
Relationship cần note:

text
orders → order_items    : 1 to many
orders → order_payments : 1 to many  
orders → order_reviews  : 1 to 1 (gần như)
orders → customers      : many to 1
order_items → products  : many to 1
order_items → sellers   : many to 1
customers/sellers → geolocation : qua zip_code
products → translation  : many to 1
Ngày 4-5: Thiết kế Star Schema

sql
-- FACT TABLE
fact_orders (
  order_id          STRING,    -- PK
  customer_id       STRING,    -- FK → dim_customers
  seller_id         STRING,    -- FK → dim_sellers  
  product_id        STRING,    -- FK → dim_products
  order_date_id     INT64,     -- FK → dim_date (YYYYMMDD)
  
  -- Measures
  price             FLOAT64,
  freight_value     FLOAT64,
  payment_value     FLOAT64,
  review_score      INT64,
  
  -- Delivery metrics
  order_status                  STRING,
  days_to_deliver               INT64,   -- actual
  days_estimated                INT64,
  is_late                       BOOL,
  days_late                     INT64    -- negative = early
)

dim_customers (
  customer_id   STRING,
  city          STRING,
  state         STRING,
  zip_code      STRING
)

dim_products (
  product_id        STRING,
  category_en       STRING,   -- sau khi join translation
  weight_g          FLOAT64,
  volume_cm3        FLOAT64   -- length*height*width
)

dim_sellers (
  seller_id   STRING,
  city        STRING,
  state       STRING
)

dim_date (
  date_id     INT64,    -- YYYYMMDD
  date        DATE,
  year        INT64,
  quarter     INT64,
  month       INT64,
  month_name  STRING,
  week        INT64,
  weekday     INT64,    -- 1=Mon, 7=Sun
  weekday_name STRING,
  is_weekend  BOOL
)
Ngày 6-7: Tạo Dataset + Staging tables trên BigQuery

python
# pipeline/create_schema.py
from google.cloud import bigquery

client = bigquery.Client(project="YOUR_PROJECT_ID")

# Tạo datasets
datasets = ["raw", "staging", "marts"]
for ds in datasets:
    dataset = bigquery.Dataset(f"YOUR_PROJECT_ID.{ds}")
    dataset.location = "US"
    client.create_dataset(dataset, exists_ok=True)
    print(f"Created dataset: {ds}")
Tuần 2 – ETL Pipeline
Ngày 1-3: Viết extract_load.py

python
# pipeline/extract_load.py
import pandas as pd
from google.cloud import bigquery, storage
from datetime import datetime

PROJECT_ID = "YOUR_PROJECT_ID"
BUCKET     = "personal-data-platform-raw"
BQ_CLIENT  = bigquery.Client(project=PROJECT_ID)

def read_from_gcs(filename: str) -> pd.DataFrame:
    path = f"gs://{BUCKET}/raw/olist/{filename}"
    return pd.read_csv(path)

def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    date_cols = [
        "order_purchase_timestamp",
        "order_approved_at", 
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date"
    ]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def clean_geolocation(df: pd.DataFrame) -> pd.DataFrame:
    # Aggregate: 1M rows → ~20K zip codes
    return df.groupby("geolocation_zip_code_prefix").agg(
        lat  = ("geolocation_lat", "mean"),
        lng  = ("geolocation_lng", "mean"),
        city = ("geolocation_city", "first"),
        state= ("geolocation_state", "first")
    ).reset_index()

def load_to_bq(df: pd.DataFrame, table: str, 
               write_mode: str = "WRITE_TRUNCATE"):
    job_config = bigquery.LoadJobConfig(
        write_disposition=write_mode,
        autodetect=True
    )
    job = BQ_CLIENT.load_table_from_dataframe(
        df, f"{PROJECT_ID}.staging.{table}", 
        job_config=job_config
    )
    job.result()
    print(f"Loaded {len(df)} rows → staging.{table}")

def run():
    tables = {
        "stg_orders":    ("olist_orders_dataset.csv",     clean_orders),
        "stg_items":     ("olist_order_items_dataset.csv",None),
        "stg_customers": ("olist_customers_dataset.csv",  None),
        "stg_products":  ("olist_products_dataset.csv",   None),
        "stg_sellers":   ("olist_sellers_dataset.csv",    None),
        "stg_payments":  ("olist_order_payments_dataset.csv", None),
        "stg_reviews":   ("olist_order_reviews_dataset.csv",  None),
        "stg_geo":       ("olist_geolocation_dataset.csv",clean_geolocation),
        "stg_translation":("product_category_name_translation.csv", None),
    }
    for table_name, (filename, cleaner) in tables.items():
        df = read_from_gcs(filename)
        if cleaner:
            df = cleaner(df)
        load_to_bq(df, table_name)

if __name__ == "__main__":
    run()
Ngày 4-5: SQL Transform → build fact/dim

sql
-- pipeline/sql/build_dim_date.sql
CREATE OR REPLACE TABLE marts.dim_date AS
WITH date_spine AS (
  SELECT DATE_ADD('2016-01-01', INTERVAL n DAY) AS date
  FROM UNNEST(GENERATE_ARRAY(0, 1460)) AS n  -- 4 years
)
SELECT
  CAST(FORMAT_DATE('%Y%m%d', date) AS INT64) AS date_id,
  date,
  EXTRACT(YEAR    FROM date) AS year,
  EXTRACT(QUARTER FROM date) AS quarter,
  EXTRACT(MONTH   FROM date) AS month,
  FORMAT_DATE('%B', date)    AS month_name,
  EXTRACT(WEEK    FROM date) AS week,
  EXTRACT(DAYOFWEEK FROM date) AS weekday,
  FORMAT_DATE('%A', date)    AS weekday_name,
  EXTRACT(DAYOFWEEK FROM date) IN (1, 7) AS is_weekend
FROM date_spine;

-- pipeline/sql/build_fact_orders.sql
CREATE OR REPLACE TABLE marts.fact_orders AS
SELECT
  o.order_id,
  o.customer_id,
  i.seller_id,
  i.product_id,
  CAST(FORMAT_DATE('%Y%m%d', 
    DATE(o.order_purchase_timestamp)) AS INT64) AS order_date_id,
  
  i.price,
  i.freight_value,
  p.payment_value,
  r.review_score,
  
  o.order_status,
  DATE_DIFF(
    DATE(o.order_delivered_customer_date),
    DATE(o.order_purchase_timestamp), DAY
  ) AS days_to_deliver,
  DATE_DIFF(
    DATE(o.order_estimated_delivery_date),
    DATE(o.order_purchase_timestamp), DAY
  ) AS days_estimated,
  o.order_delivered_customer_date > 
    o.order_estimated_delivery_date AS is_late,
  DATE_DIFF(
    DATE(o.order_delivered_customer_date),
    DATE(o.order_estimated_delivery_date), DAY
  ) AS days_late

FROM staging.stg_orders o
LEFT JOIN staging.stg_items    i USING (order_id)
LEFT JOIN staging.stg_payments p USING (order_id)
LEFT JOIN staging.stg_reviews  r USING (order_id)
WHERE o.order_status = 'delivered';
Ngày 6-7: Analytical Queries có Business Insight

sql
-- Q1: Revenue theo tháng — trend analysis
SELECT
  FORMAT_DATE('%Y-%m', DATE(o.order_purchase_timestamp)) AS month,
  COUNT(DISTINCT o.order_id)   AS total_orders,
  ROUND(SUM(i.price), 0)       AS revenue,
  ROUND(AVG(i.price), 2)       AS aov
FROM staging.stg_orders o
JOIN staging.stg_items i USING (order_id)
WHERE o.order_status = 'delivered'
GROUP BY 1 ORDER BY 1;

-- Q2: Late delivery vs Review score — key insight
SELECT
  CASE
    WHEN DATE_DIFF(
      DATE(order_delivered_customer_date),
      DATE(order_estimated_delivery_date), DAY) <= 0
      THEN '✓ On Time'
    WHEN DATE_DIFF(...) <= 7 THEN '⚠ Late < 1w'
    ELSE '✗ Late > 1w'
  END AS delivery_status,
  ROUND(AVG(r.review_score), 2) AS avg_review,
  COUNT(*)                       AS orders,
  ROUND