# Kết quả EDA — Olist

**Lộ trình:** [`README.md`](README.md) · **Thực hành:** `notebooks/01_explore.ipynb`, `scripts/EDA.ipynb`

## Quy mô

| Bảng | Dòng | Cột |
|------|-----:|----:|
| orders | 99.441 | 8 |
| customers | 99.441 | 5 |
| items | 112.650 | 7 |
| payments | 103.886 | 5 |
| reviews | 99.224 | 7 |
| products | 32.951 | 9 |
| sellers | 3.095 | 4 |
| geo | 1.000.163 | 5 |
| translation | 71 | 2 |

## Ý chính theo bảng

- **orders:** ~97k `delivered`; null nhiều ở `order_delivered_customer_date` (~3%), carrier (~1,8%); timestamp trong CSV là **chuỗi** → parse datetime khi pipeline.  
- **items:** 1 `order_id` có thể **nhiều dòng** (max ~21); **giá:** `price`, **ship:** `freight_value`.  
- **payments:** `boleto`, `credit_card`, `debit_card`, `voucher`, `not_defined`; **~3k** đơn có **>1** payment.  
- **reviews:** score **1–5**; **~59%** null `review_comment_message`.  
- **geo:** ~**1M** dòng, ~**19k** zip prefix → nhiều tọa độ / prefix.  
- **products:** ~**1,85%** null category → policy trước khi join `translation`.  

## Rủi ro modeling

- Zip số trong CSV → có thể **mất số 0 đầu** → chuẩn hóa **5 ký tự** khi join.  
- Grain khác nhau (đơn / item / payment / review) → chọn **đúng fact** (xem [`dwh-olist-design.md`](dwh-olist-design.md)).

## Clean local (tùy)

Parquet sau clean: cell cuối `scripts/EDA.ipynb` → thư mục `data/clean/`.
