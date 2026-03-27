# Sườn dự án end-to-end: DE → DA → DS → ML → AI/Agent (Olist / e-commerce)

Tài liệu này là **khung làm dần** — bạn có thể chỉnh stack (BQ-only vs Postgres local, Airflow vs Dagster, v.v.) nhưng **thứ tự nghiệp vụ** nên giữ để pipeline “có thật”: dữ liệu chảy trước, insight sau, model trên mart, agent cuối cùng đọc đã kiểm soát.

**Tiền đề:** đã nắm khái niệm staging/mart trong [dwh-olist-design.md](dwh-olist-design.md) và luồng DE trong [bq-etl-de-workflow.md](bq-etl-de-workflow.md).

---

## 1. Mục tiêu tổng thể

| Mục tiêu | Tiêu chí “xong” |
|----------|------------------|
| **DE** | Ingest → raw/staging → mart có grain rõ; job lặp lại được; có kiểm tra tối thiểu (row count, freshness). |
| **DA** | Dashboard hoặc báo cáo SQL cố định trả lời 5–8 câu hỏi kinh doanh. |
| **DS** | Một phân tích có giả thuyết + kết luận đo lường được (cohort, RFM, hoặc drivers). |
| **ML** | Một model tabular + batch scoring ghi vào bảng `analytics.*`; có baseline đơn giản để so. |
| **AI/Agent** | RAG hoặc agent có **tool read-only** (SQL/metric) + trích dẫn nguồn; không tự ghi warehouse lúc đầu. |

**Một câu chuyện người dùng xuyên suốt:** *“Pipeline cập nhật mart mỗi ngày → DA xem KPI → DS làm báo cáo sâu → ML cập nhật dự báo/score → stakeholder hỏi chatbot và nhận câu trả lời có căn cứ query/bảng.”*

---

## 2. Phạm vi dữ liệu (gợi ý bám Olist)

- **Nguồn:** các bảng Olist đã dùng trong project (orders, items, payments, customers, geolocation, reviews, products, sellers, leads).
- **Grain mart tối thiểu:**  
  - `fct_orders_daily` (ngày × trạng thái vùng nếu có)  
  - `fct_order_items` (đơn–dòng hàng)  
  - `dim_customer`, `dim_seller`, `dim_product` (tùy mức hoàn thiện staging).

Giảm phạm vi nếu thiếu thời gian: chỉ **đơn + item + payment + customer**.

---

## 3. Kiến trúc tham chiếu (logical)

```text
Nguồn (CSV/GCS/API giả lập)
    → Landing / Raw
    → Staging (chuẩn hóa kiểu, PK, dedup nhẹ)
    → Mart (star / wide theo use case)
    → Consumption: BI + Notebook + Feature view + Batch predictions
    → LLM layer: RAG (docs/mart dictionary) + Tool SQL read-only
```

**Nguyên tắc:** ML và agent **không** đọc trực tiếp staging “bẩn”; chỉ đọc mart hoặc bảng `analytics` đã kiểm duyệt.

---

## 4. Cấu trúc thư mục gợi ý (trong `data-platform/`)

```text
data-platform/
  pipeline/              # ingest, staging jobs (đã có — mở rộng)
  dbt/                   # (tùy chọn) mart SQL có test
  orchestration/         # Airflow/Dagster DAG hoặc cron manifest
  analytics/             # SQL cho DA, export cho BI
  ml/
    features/            # định nghĩa feature SQL / Python
    train/               # script train, config
    batch_score/         # job ghi predictions
  ai/
    rag/                 # chunk, embed, index (local hoặc managed)
    agent/               # tool definitions, prompt, guardrail
  notebooks/             # EDA, DS (đã có — gắn mục lục)
  notes/
    pipeline-e2e-capstone-roadmap.md   # file này
```

Không cần tạo hết ngày một — **mở folder theo phase**.

---

## 5. Phase chi tiết

### Phase 0 — Chuẩn bị (0,5–1 tuần)

| # | Việc | Đầu ra |
|---|------|--------|
| 0.1 | Chốt môi trường: BQ + GCS (theo repo hiện tại) hoặc thêm Postgres local cho dev | Doc 1 trang: “chạy trên máy tôi thế này” |
| 0.2 | Danh sách bảng + owner + tầng (raw/staging/mart) | Bảng trong README hoặc `notes/data-contract.md` |
| 0.3 | Secrets: ADC / SA — không commit key | `.env.example` hoặc hướng dẫn GCP |

**Cổng thoát phase:** một lệnh (hoặc một DAG) chạy được ingest tới staging như hiện trạng + verify query.

---

### Phase 1 — DE: Staging chắc + Mart v1 (2–4 tuần)

| # | Việc | Đầu ra |
|---|------|--------|
| 1.1 | Hoàn thiện `clean_*` / typing / null theo [staging-after-eda.md](staging-after-eda.md) | Staging ổn định, có test SQL hoặc assert trong Python |
| 1.2 | Thiết kế 2 fact + dim tối thiểu theo [dwh-olist-design.md](dwh-olist-design.md) | DDL hoặc dbt model |
| 1.3 | Mart v1: doanh thu, số đơn, AOV theo thời gian / bang (nếu join được) | View hoặc table `mart.*` |
| 1.4 | **Data quality:** kiểm tra freshness (ngày dữ liệu mới nhất), duplicate PK, tổng tiền khớp payment vs order | Bảng log QC hoặc task cuối pipeline |
| 1.5 | **Orchestration:** lịch chạy (daily) — Airflow/Dagster hoặc Cloud Scheduler + script | DAG/README có thứ tự task + retry |

**Cổng thoát phase:** mart v1 refresh tự động; bạn viết được 10 dòng SQL trả lời “doanh thu 7 ngày gần nhất”.

---

### Phase 2 — DA: Tiêu thụ mart (1–2 tuần)

| # | Việc | Đầu ra |
|---|------|--------|
| 2.1 | Định nghĩa 5–8 câu hỏi KPI (doanh thu, đơn, hủy, lead time, top category…) | `analytics/kpi_questions.md` |
| 2.2 | SQL saved (hoặc dbt exposure) cho từng KPI | File `.sql` trong `analytics/` |
| 2.3 | Dashboard: Metabase / Looker Studio / Lightdash / BQ Studio — chọn một | Link hoặc export PDF snapshot |
| 2.4 | Tài liệu “grain + caveats” cho từng chart | 1 trang để DS/ML không hiểu sai |

**Cổng thoát phase:** người không code đọc dashboard hiểu được xu hướng tuần.

---

### Phase 3 — DS: Phân tích có giả thuyết (1–2 tuần)

| # | Việc | Đầu ra |
|---|------|--------|
| 3.1 | Chọn một câu hỏi: ví dụ *“Khách mới vs cũ — giá trị đơn khác nhau thế nào?”* hoặc cohort theo tháng mua đầu | Notebook có EDA + plot |
| 3.2 | Định nghĩa metric, segment, bias (missing geo, seller tập trung) | Section “Limitation” trong notebook |
| 3.3 | Kết luận 3 bullet + đề xuất hành động (dù chỉ là “cần thu thập thêm X”) | Slide hoặc markdown báo cáo |

**Cổng thoát phase:** một file báo cáo DS có thể trình được trong 10 phút.

---

### Phase 4 — ML: Tabular + batch (2–3 tuần)

| # | Việc | Đầu ra |
|---|------|--------|
| 4.1 | Chọn bài toán gọn: **dự báo số đơn/ngày** (aggregate) hoặc **phân loại trễ giao** (nếu có label) hoặc **LTV bucket** | `ml/README.md` mô tả label + horizon |
| 4.2 | Feature từ mart (SQL hoặc Python), snapshot theo ngày (tránh leakage) | `ml/features/*.sql` |
| 4.3 | Train: baseline (moving average / logistic) + model chính (LightGBM / sklearn) | Artifact + metrics (MAE/AUC) lưu file |
| 4.4 | Batch score: job ghi `analytics.predictions_*` partition theo `run_date` | Task trong orchestration |
| 4.5 | (Tùy chọn) Theo dõi đơn giản: so sánh distribution feature tuần này vs tuần trước | Bảng hoặc notebook |

**Cổng thoát phase:** bảng predictions join lại mart được; DA có thể vẽ thêm một chart “thực tế vs dự báo”.

---

### Phase 5 — AI / Agent: RAG + tool an toàn (2–4 tuần)

| # | Việc | Đầu ra |
|---|------|--------|
| 5.1 | **Data dictionary / glossary** cho mart (markdown) — nguồn RAG | `ai/rag/docs/*.md` |
| 5.2 | RAG: embed glossary + vài đoạn hướng dẫn KPI; Q&A “Ý nghĩa cột X là gì?” | Script hoặc app nhỏ |
| 5.3 | **Tool SQL read-only:** chỉ cho phép `SELECT` trên dataset mart (whitelist view), giới hạn timeout/rows | Module `ai/agent/tools.py` |
| 5.4 | Agent (hoặc single LLM + tool loop): user hỏi KPI → gọi tool → trả lời kèm SQL/metric | Demo CLI hoặc FastAPI |
| 5.5 | Guardrail: không cho DROP/INSERT; log prompt + query (PII policy) | Checklist bảo mật 1 trang |

**Cổng thoát phase:** demo 3 câu hỏi: định nghĩa metric, số liệu từ SQL, giải thích driver (kết hợp text + số).

---

## 6. Ma trận kỹ năng (DE / DA / DS / ML / AI)

| Phase | DE | DA | DS | ML | AI |
|-------|----|----|----|----|-----|
| 0–1 | ●●● | ○ | ○ | ○ | ○ |
| 2 | ● | ●●● | ○ | ○ | ○ |
| 3 | ○ | ● | ●●● | ○ | ○ |
| 4 | ● | ● | ● | ●●● | ○ |
| 5 | ○ | ● | ○ | ○ | ●●● |

---

## 7. Ước lượng thời gian tổng

- **Lộ trình vừa phải:** ~8–12 tuần làm bán thời gian (một phase có overlap).  
- **Tối giản (bỏ ML hoặc bỏ Agent):** trừ ~2–4 tuần tương ứng.

---

## 8. Rủi ro & thứ tự “đừng làm sớm”

1. **Đừng** làm Agent trước khi mart và KPI SQL ổn — sẽ “bịa” hoặc SQL lung tung.  
2. **Đừng** train ML trước khi grain mart và label rõ — leakage rất dễ.  
3. **Đừng** nhét quá nhiều nguồn mới khi Phase 1 chưa cổng thoát — nợ kỹ thuật DE ăn cả sau.

---

## 9. Liên kết repo hiện có

| Phần | File / thư mục |
|------|----------------|
| ETL | [pipeline/extract_load.py](../pipeline/extract_load.py) |
| DWH thiết kế | [dwh-olist-design.md](dwh-olist-design.md) |
| Staging | [staging-after-eda.md](staging-after-eda.md) |
| Lộ trình gốc | [README.md](README.md), [plan.md](plan.md) |
| Docker/K8s học song song | `Projects/docker-lab`, `Projects/k8s-lab` |

---

## 10. Checklist nhanh (copy khi làm)

```
Phase 0: [ ] env [ ] data contract [ ] secrets
Phase 1: [ ] staging [ ] mart v1 [ ] QC [ ] orchestration
Phase 2: [ ] KPI SQL [ ] dashboard [ ] caveats doc
Phase 3: [ ] notebook DS [ ] báo cáo
Phase 4: [ ] features [ ] train [ ] batch score [ ] join DA
Phase 5: [ ] glossary [ ] RAG [ ] SQL tool read-only [ ] demo agent
```

---

*Bản cập nhật: có thể chỉnh phase thời gian theo việc bạn dùng BQ-only hay thêm Postgres + Compose cho orchestrator local.*
