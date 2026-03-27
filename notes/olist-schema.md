# ERD nguồn — Olist (CSV)

**Mục lục:** [`README.md`](README.md) · **Star schema / marts:** [`dwh-olist-design.md`](dwh-olist-design.md)

File thực tế: `olist_*_dataset.csv` + `product_category_name_translation.csv`. Tên `olist_customers_dataset` (không phải `olist_order_customer_dataset`).

## Mermaid

```mermaid
erDiagram
    olist_orders_dataset {
        string order_id PK
        string customer_id FK
        string order_status
        datetime order_purchase_timestamp
        datetime order_approved_at
        datetime order_delivered_carrier_date
        datetime order_delivered_customer_date
        datetime order_estimated_delivery_date
    }

    olist_customers_dataset {
        string customer_id PK
        string customer_unique_id
        string customer_zip_code_prefix
        string customer_city
        string customer_state
    }

    olist_order_items_dataset {
        string order_id FK
        int order_item_id
        string product_id FK
        string seller_id FK
        datetime shipping_limit_date
        float price
        float freight_value
    }

    olist_order_payments_dataset {
        string order_id FK
        int payment_sequential
        string payment_type
        int payment_installments
        float payment_value
    }

    olist_order_reviews_dataset {
        string review_id PK
        string order_id FK
        int review_score
        string review_comment_title
        string review_comment_message
        date review_creation_date
        datetime review_answer_timestamp
    }

    olist_products_dataset {
        string product_id PK
        string product_category_name FK
        int product_name_lenght
        int product_description_lenght
        int product_photos_qty
        int product_weight_g
        float product_length_cm
        float product_height_cm
        float product_width_cm
    }

    olist_sellers_dataset {
        string seller_id PK
        string seller_zip_code_prefix
        string seller_city
        string seller_state
    }

    olist_geolocation_dataset {
        string geolocation_zip_code_prefix
        float geolocation_lat
        float geolocation_lng
        string geolocation_city
        string geolocation_state
    }

    product_category_name_translation {
        string product_category_name PK
        string product_category_name_english
    }

    olist_customers_dataset ||--o{ olist_orders_dataset : "customer_id"
    olist_orders_dataset ||--o{ olist_order_items_dataset : "order_id"
    olist_orders_dataset ||--o{ olist_order_payments_dataset : "order_id"
    olist_orders_dataset ||--o{ olist_order_reviews_dataset : "order_id"
    olist_products_dataset ||--o{ olist_order_items_dataset : "product_id"
    olist_sellers_dataset ||--o{ olist_order_items_dataset : "seller_id"
    olist_customers_dataset }o--o{ olist_geolocation_dataset : "customer_zip_code_prefix = geolocation_zip_code_prefix"
    olist_sellers_dataset }o--o{ olist_geolocation_dataset : "seller_zip_code_prefix = geolocation_zip_code_prefix"
    product_category_name_translation ||--o{ olist_products_dataset : "product_category_name"
```

- Trục join: **orders** → items / payments / reviews / customers.  
- **Geo:** nhiều dòng / zip prefix — join lỏng hoặc aggregate trước.  
- **Typo cột:** `product_name_lenght` (Kaggle).

## DBML (dbdiagram.io)

```dbml
Table olist_orders_dataset {
  order_id varchar [pk]
  customer_id varchar [ref: > olist_customers_dataset.customer_id]
  order_status varchar
  order_purchase_timestamp datetime
  order_approved_at datetime
  order_delivered_carrier_date datetime
  order_delivered_customer_date datetime
  order_estimated_delivery_date datetime
}

Table olist_customers_dataset {
  customer_id varchar [pk]
  customer_unique_id varchar
  customer_zip_code_prefix varchar
  customer_city varchar
  customer_state varchar
}

Table olist_order_items_dataset {
  order_id varchar [ref: > olist_orders_dataset.order_id]
  order_item_id int
  product_id varchar [ref: > olist_products_dataset.product_id]
  seller_id varchar [ref: > olist_sellers_dataset.seller_id]
  shipping_limit_date datetime
  price decimal
  freight_value decimal
}

Table olist_order_payments_dataset {
  order_id varchar [ref: > olist_orders_dataset.order_id]
  payment_sequential int
  payment_type varchar
  payment_installments int
  payment_value decimal
}

Table olist_order_reviews_dataset {
  review_id varchar [pk]
  order_id varchar [ref: > olist_orders_dataset.order_id]
  review_score int
  review_comment_title varchar
  review_comment_message varchar
  review_creation_date date
  review_answer_timestamp datetime
}

Table olist_products_dataset {
  product_id varchar [pk]
  product_category_name varchar [ref: > product_category_name_translation.product_category_name]
  product_name_lenght int
  product_description_lenght int
  product_photos_qty int
  product_weight_g int
  product_length_cm decimal
  product_height_cm decimal
  product_width_cm decimal
}

Table olist_sellers_dataset {
  seller_id varchar [pk]
  seller_zip_code_prefix varchar
  seller_city varchar
  seller_state varchar
}

Table olist_geolocation_dataset {
  geolocation_zip_code_prefix varchar
  geolocation_lat decimal
  geolocation_lng decimal
  geolocation_city varchar
  geolocation_state varchar
}

Table product_category_name_translation {
  product_category_name varchar [pk]
  product_category_name_english varchar
}
```

Join geo qua zip: FK lỏng — thể hiện bằng comment hoặc SQL, không bắt buộc trong DBML.
