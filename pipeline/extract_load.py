# ===== PHẦN 1: IMPORTS & CONFIG =====
"""
ETL: GCS (CSV) → Transform → BigQuery dataset `staging`.

Chạy từ repo (đã ADC):
  cd D:\\H\\Projects\\data-platform
  python pipeline/extract_load.py

Cần: google-cloud-bigquery, google-cloud-storage, pandas, pyarrow.
"""
from __future__ import annotations

import io
from collections.abc import Callable

import pandas as pd
from google.cloud import bigquery, storage

PROJECT_ID = "project-6fe3973c-4db8-4b72-83b"
BUCKET = "personal-data-platform-raw"
BQ_DATASET = "staging"
GCS_PREFIX = "raw/olist"

# Tại sao dùng bigquery.Client?
# → Official Python SDK của GCP; dùng Application Default Credentials (gcloud auth application-default login)
# → Không hardcode key trong code.
bq_client = bigquery.Client(project=PROJECT_ID)
_storage_client: storage.Client | None = None


def _get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


# ===== PHẦN 2: EXTRACT =====
def read_from_gcs(filename: str) -> pd.DataFrame:
    """
    Đọc CSV từ GCS về pandas (tải blob qua google-cloud-storage, không cần gcsfs).
    """
    path = f"gs://{BUCKET}/{GCS_PREFIX}/{filename}"
    print(f"Reading: {path}")
    blob = _get_storage_client().bucket(BUCKET).blob(f"{GCS_PREFIX}/{filename}")
    raw = blob.download_as_bytes()
    df = pd.read_csv(io.BytesIO(raw))
    print(f"  -> {len(df):,} rows, {len(df.columns)} cols")
    return df


# ===== PHẦN 3: TRANSFORM =====
def _zip5(series: pd.Series) -> pd.Series:
    """CEP prefix → string 5 ký tự (CSV đọc int mất số 0 đầu). Khớp join với stg_geo.zip_code."""
    s = pd.to_numeric(series, errors="coerce")
    out = pd.Series(pd.NA, index=series.index, dtype="string")
    m = s.notna()
    out.loc[m] = s.loc[m].round().astype(int).astype(str).str.zfill(5)
    return out


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    """
    Timestamp trong CSV là string → datetime để BQ/schema và tính toán đúng.
    errors='coerce': parse lỗi → NaT, không crash pipeline.
    """
    out = df.copy()
    date_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in date_cols:
        out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def clean_geolocation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hóa zip → groupby 1 dòng / prefix (mean lat/lng). Cột output: zip_code (string 5).
    """
    x = df.copy()
    x["geolocation_zip_code_prefix"] = _zip5(x["geolocation_zip_code_prefix"])
    return (
        x.groupby("geolocation_zip_code_prefix", as_index=False)
        .agg(
            lat=("geolocation_lat", "mean"),
            lng=("geolocation_lng", "mean"),
            city=("geolocation_city", "first"),
            state=("geolocation_state", "first"),
        )
        .rename(columns={"geolocation_zip_code_prefix": "zip_code"})
    )


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    """
    Điền null kích thước/cân bằng median; thêm volume_cm3.
    """
    out = df.copy()
    num_cols = [
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]
    for col in num_cols:
        if col in out.columns:
            med = out[col].median()
            out[col] = out[col].fillna(med)
    out["volume_cm3"] = (
        out["product_length_cm"] * out["product_height_cm"] * out["product_width_cm"]
    )
    if "product_category_name" in out.columns:
        out["product_category_name"] = out["product_category_name"].fillna("unknown")
    return out


def clean_items(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["shipping_limit_date"] = pd.to_datetime(out["shipping_limit_date"], errors="coerce")
    return out


def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["customer_zip_code_prefix"] = _zip5(out["customer_zip_code_prefix"])
    return out


def clean_sellers(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["seller_zip_code_prefix"] = _zip5(out["seller_zip_code_prefix"])
    return out


def clean_payments(df: pd.DataFrame) -> pd.DataFrame:
    """Giữ grain (order_id, payment_sequential); ép kiểu số rõ ràng."""
    out = df.copy()
    out["payment_sequential"] = pd.to_numeric(out["payment_sequential"], errors="coerce").astype("Int64")
    out["payment_installments"] = pd.to_numeric(out["payment_installments"], errors="coerce").astype("Int64")
    out["payment_value"] = pd.to_numeric(out["payment_value"], errors="coerce")
    return out


def clean_reviews(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["review_creation_date"] = pd.to_datetime(out["review_creation_date"], errors="coerce")
    out["review_answer_timestamp"] = pd.to_datetime(out["review_answer_timestamp"], errors="coerce")
    out["review_score"] = pd.to_numeric(out["review_score"], errors="coerce").astype("Int64")
    return out


def clean_translation(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == object or pd.api.types.is_string_dtype(out[c]):
            out[c] = out[c].astype("string").str.strip()
    return out


# ===== PHẦN 4: LOAD =====
def load_to_bq(df: pd.DataFrame, table_name: str) -> None:
    """
    WRITE_TRUNCATE: full refresh mỗi lần chạy.
    autodetect=True: tiện prototype; production nên khai báo schema explicit.
    """
    destination = f"{PROJECT_ID}.{BQ_DATASET}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    job = bq_client.load_table_from_dataframe(df, destination, job_config=job_config)
    job.result()
    print(f"  OK Loaded {len(df):,} rows -> {destination}")


# ===== PHẦN 5: ORCHESTRATE =====
def run() -> None:
    tables: dict[str, tuple[str, Callable[[pd.DataFrame], pd.DataFrame] | None]] = {
        "stg_orders": ("olist_orders_dataset.csv", clean_orders),
        "stg_items": ("olist_order_items_dataset.csv", clean_items),
        "stg_customers": ("olist_customers_dataset.csv", clean_customers),
        "stg_products": ("olist_products_dataset.csv", clean_products),
        "stg_sellers": ("olist_sellers_dataset.csv", clean_sellers),
        "stg_payments": ("olist_order_payments_dataset.csv", clean_payments),
        "stg_reviews": ("olist_order_reviews_dataset.csv", clean_reviews),
        "stg_geo": ("olist_geolocation_dataset.csv", clean_geolocation),
        "stg_translation": ("product_category_name_translation.csv", clean_translation),
    }

    for table_name, (filename, cleaner) in tables.items():
        print(f"\n[{table_name}]")
        frame = read_from_gcs(filename)
        if cleaner is not None:
            frame = cleaner(frame)
        load_to_bq(frame, table_name)

    print("\nPipeline hoan thanh.")


if __name__ == "__main__":
    run()
