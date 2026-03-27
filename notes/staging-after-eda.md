# Staging — checklist sau EDA

**Mục lục:** [`README.md`](README.md) · **Script:** [`extract_load.py`](../pipeline/extract_load.py)

**Mục tiêu staging:** kiểu đúng, khóa join ổn; KPI nặng để **marts**/SQL.

## Đã implement trong `extract_load.py`

| `stg_*` | Hàm | Việc làm |
|---------|-----|----------|
| stg_orders | `clean_orders` | 5 cột → datetime |
| stg_items | `clean_items` | `shipping_limit_date` → datetime |
| stg_customers | `clean_customers` | `customer_zip_code_prefix` → string 5 (`_zip5`) |
| stg_sellers | `clean_sellers` | `seller_zip_code_prefix` → string 5 |
| stg_payments | `clean_payments` | sequential/installments/value → numeric (nullable int khi cần) |
| stg_reviews | `clean_reviews` | 2 cột datetime; `review_score` → Int64 |
| stg_products | `clean_products` | median fill kích thước, `volume_cm3`, category null → `unknown` |
| stg_geo | `clean_geolocation` | `_zip5` prefix rồi aggregate → `zip_code` + lat/lng mean |
| stg_translation | `clean_translation` | strip chuỗi key/value |

**Join zip:** `stg_customers` / `stg_sellers` prefix cùng rule với `stg_geo.zip_code` (5 ký tự).

## Tuỳ chọn sau (marts / dbt)

- Đổi mean → **median** geo cho khớp notebook local.  
- Rename typo `product_name_lenght` → `product_name_length` ở lớp SQL/dbt.  
- Test `review_score` ∈ [1,5] (flag / filter).

**Tiếp:** SQL/dbt `staging` → `marts` — [`dwh-olist-design.md`](dwh-olist-design.md).
