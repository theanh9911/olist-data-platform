# Ghi chú học Data Platform (Olist)

Đọc **theo thứ tự** — mỗi bước có file ngắn + thực hành trong repo.

## Lộ trình (bảng chính)

| Bước | Nội dung | Đọc | Thực hành |
| ---: | -------- | --- | --------- |
| 0 | GCP: PATH, login, project, bucket | [d1.md](d1.md) | Login + upload 9 CSV lên `raw/olist/` |
| 1 | Tư duy DE + BQ: tầng dữ liệu, grain | [bq-etl-de-workflow.md](bq-etl-de-workflow.md) | Trả lời 4 câu tự kiểm trong file |
| 2 | EDA — 9 bảng | [eda-summary.md](eda-summary.md) | [01_explore.ipynb](../notebooks/01_explore.ipynb), [EDA.ipynb](../scripts/EDA.ipynb) |
| 3 | ERD nguồn | [olist-schema.md](olist-schema.md) | Export ảnh → [erd.png](../dashboard/screenshots/) |
| 4 | Star schema + grain | [dwh-olist-design.md](dwh-olist-design.md) | Viết 1 đoạn: vì sao 2 fact khác grain |
| 5 | Staging — transform từng bảng | [staging-after-eda.md](staging-after-eda.md) | Bổ sung `clean_*` trong [extract_load.py](../pipeline/extract_load.py) |
| 6 | ETL GCS → BQ `staging` | Bước 1 + [d1.md](d1.md) | Chạy script (lệnh dưới) + verify BQ |
| 7 | Marts — SQL/dbt | [dwh-olist-design.md](dwh-olist-design.md) §5 mapping | SQL trong Console hoặc init `dbt/` (gợi ý dưới) |

Kế hoạch checklist dài: [plan.md](plan.md).

**Capstone end-to-end** (DE → DA → DS → ML → AI/Agent, làm dần): [pipeline-e2e-capstone-roadmap.md](pipeline-e2e-capstone-roadmap.md).

---

## Điều kiện trước khi chạy pipeline (bước 6)

- Python 3.13+ và env có: `pandas`, `pyarrow`, `google-cloud-bigquery`, `google-cloud-storage`.
- Đã `gcloud auth application-default login` (ADC cho client Python).
- Project GCP và dataset `staging` đã tạo ([d1.md](d1.md)).
- Bucket có đủ 9 file CSV dưới `gs://…/raw/olist/`.

---

## Lệnh tham chiếu nhanh

```powershell
# ETL (từ thư mục data-platform hoặc chỉnh PYTHONPATH tới project có dependency)
cd D:\H\Projects\data-platform
python pipeline\extract_load.py
```

```powershell
# Kiểm tra BQ
bq ls --project_id=project-6fe3973c-4db8-4b72-83b staging
bq query --use_legacy_sql=false "SELECT COUNT(*) AS n FROM `project-6fe3973c-4db8-4b72-83b.staging.stg_orders`"
```

```powershell
# Kiểm tra GCS
gcloud storage ls gs://personal-data-platform-raw/raw/olist/
```

---

## Thư mục repo (chỗ hay đụng)

| Đường dẫn | Việc |
|-----------|------|
| `data-platform/data/` | CSV local (EDA) |
| `data-platform/data/clean/` | Parquet sau cell clean trong `EDA.ipynb` |
| `data-platform/notebooks/` | Explore bước 2 |
| `data-platform/scripts/EDA.ipynb` | EDA + clean nâng cao |
| `data-platform/pipeline/extract_load.py` | ETL → BQ staging |
| `data-platform/dashboard/screenshots/` | Ảnh ERD export |

---

## Bước 7 — gợi ý khép vòng demo (chưa có code trong repo)

Làm **một trong hai** (đủ để nói “đã đi hết pipeline”):

1. **BigQuery Console — Saved query**  
   Viết SQL đọc `staging.stg_*`: join orders + items + products + translation → `SELECT` doanh thu theo tháng / bang (materialize bằng `CREATE TABLE marts.fact_order_items_demo AS …` nếu muốn lưu bảng).

2. **dbt** (chuẩn nghề DE)  
   Trong `data-platform/`: `dbt init` (profile trỏ BQ), khai báo `sources.yml` cho `staging`, tạo model `marts/dim_product.sql`, `marts/fact_order_items.sql` theo [dwh-olist-design.md](dwh-olist-design.md).

Thứ tự hợp lý trong dbt: **staging (sources)** → **intermediate** (join, rename) → **marts** (fact/dim).

---

## Cạm bẫy hay gặp

1. **Tên file:** `olist_*_dataset.csv`, không chỉ `orders` / `customers`.
2. **Grain:** `price` / `freight` ở **order_items** → fact chi tiết là **fact_order_items**; **fact_orders** = cấp đơn (SLA, tổng thanh toán, …).
3. **Geo ~1M dòng:** nhiều lat/lng / zip prefix — aggregate hoặc rule trước khi dim.
4. **Zip:** số trong CSV có thể mất số 0 đầu → chuẩn **string 5 ký tự** khi join geo.
5. **Review vs order:** không giả định 1:1 nếu chưa kiểm tra `COUNT(DISTINCT order_id)` trên reviews.
