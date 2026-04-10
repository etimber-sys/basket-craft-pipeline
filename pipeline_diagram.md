# BasketCraft ELT Pipeline Diagram

```mermaid
flowchart TD
    subgraph SRC["☁️  SOURCE  —  MySQL (db.isba.co / basket_craft)"]
        O[(orders)]
        OI[(order_items)]
        P[(products)]
    end

    subgraph EX["⚙️  EXTRACT  —  extract.py"]
        direction TB
        E1["🔌 get_mysql_conn()\nDictCursor"]
        E2["fetchall() → memory\nbatch size = 1,000 rows"]
        E3["TRUNCATE stg_* then\nexecutemany() INSERT"]
        E1 --> E2 --> E3
    end

    subgraph STG["🗄️  STAGING LAYER  —  PostgreSQL (localhost / basket_craft)"]
        SO[(stg_orders)]
        SOI[(stg_order_items)]
        SP[(stg_products)]
    end

    subgraph TR["⚙️  TRANSFORM  —  transform.py"]
        direction TB
        T1["JOIN stg_order_items\n+ stg_products"]
        T2["DATE_TRUNC('month')\nGROUP BY month, product"]
        T3["Aggregate:\norder_count · revenue_usd · avg_order_value"]
        T4["TRUNCATE monthly_sales\nthen INSERT"]
        T1 --> T2 --> T3 --> T4
    end

    subgraph ANA["📊  ANALYTICS LAYER  —  PostgreSQL"]
        MS[(monthly_sales\nPK: sale_month + product_id)]
    end

    subgraph ORCH["🎛️  ORCHESTRATOR  —  pipeline.py"]
        PH1["1. extract()"]
        PH2["2. transform()"]
        PH1 --> PH2
    end

    O  --> EX
    OI --> EX
    P  --> EX
    EX --> SO
    EX --> SOI
    EX --> SP

    SO  -.->|"not used\nin transform"| TR
    SOI --> TR
    SP  --> TR
    TR  --> MS

    ORCH -.->|"calls"| EX
    ORCH -.->|"calls"| TR
```

## Data Flow Summary

| Step | Phase | From | To | Key Mechanic |
|------|-------|------|----|--------------|
| 1 | Extract | MySQL `orders` | `stg_orders` | TRUNCATE + batch INSERT |
| 2 | Extract | MySQL `order_items` | `stg_order_items` | TRUNCATE + batch INSERT |
| 3 | Extract | MySQL `products` | `stg_products` | TRUNCATE + batch INSERT |
| 4 | Transform | `stg_order_items` + `stg_products` | `monthly_sales` | DATE_TRUNC GROUP BY aggregation |

## monthly_sales Schema (Output)

| Column | Type | Description |
|--------|------|-------------|
| `sale_month` | DATE (PK) | First day of each month |
| `product_id` | INT (PK) | Product identifier |
| `product_name` | VARCHAR(50) | Denormalized for query convenience |
| `order_count` | INT | Distinct orders per product-month |
| `revenue_usd` | NUMERIC(12,2) | Sum of `price_usd` from order_items |
| `avg_order_value` | NUMERIC(10,2) | `revenue_usd / order_count` |

## Design Properties

- **Idempotent** — both phases TRUNCATE before insert; safe to re-run
- **Atomic** — each phase rolls back on error; no partial state
- **Injection-safe** — table names whitelisted; values parameterized
