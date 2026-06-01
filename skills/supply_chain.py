from skills.base import Skill

skill = Skill(
    name="supply_chain",
    description="Supply chain analytics: lead times, supplier performance, logistics, demand forecasting, and fulfilment",
    keywords=[
        "supply chain", "supplier", "suppliers", "vendor", "vendors",
        "lead time", "lead times", "procurement", "purchase order", "purchase orders",
        "fulfillment", "fulfilment", "order fulfillment", "on-time delivery",
        "on time delivery", "delivery performance", "late deliveries", "late orders",
        "logistics", "shipping", "shipment", "shipments", "freight",
        "demand forecast", "demand forecasting", "forecast accuracy",
        "replenishment", "safety stock", "reorder point",
        "bill of materials", "bom", "raw materials", "components",
        "goods received", "goods receipt", "inbound", "outbound",
        "warehouse throughput", "pick rate", "fill rate", "backorder",
        "back order", "supplier scorecard", "defect rate", "return rate",
        "days payable outstanding", "dpo", "days inventory outstanding", "dio",
    ],
    prompt_hint=(
        "This is a supply chain analysis. "
        "Focus on lead time variability (average, min, max, and standard deviation), "
        "supplier on-time delivery rates, and fulfilment performance. "
        "Identify bottlenecks: suppliers with the longest or most variable lead times, "
        "products with chronic backorders, and routes with the highest late-delivery rate. "
        "Express delivery performance as a percentage of orders delivered on time. "
        "Where demand forecasting is involved, compute forecast accuracy as "
        "1 - ABS(forecast - actual) / NULLIF(actual, 0). "
        "Rank suppliers or routes by impact (volume × defect/delay rate)."
    ),
    sql_hint=(
        "-- Supply chain patterns:\n"
        "-- Lead time:          DATEDIFF('day', order_date, received_date) AS lead_time_days\n"
        "-- Lead time stats:    AVG(lead_time_days), STDDEV(lead_time_days), MIN(), MAX()\n"
        "-- On-time rate:       SUM(CASE WHEN actual_delivery <= promised_delivery THEN 1 ELSE 0 END)\n"
        "--                     / NULLIF(COUNT(*), 0) AS on_time_rate\n"
        "-- Forecast accuracy:  1 - ABS(forecast - actual) / NULLIF(actual, 0) AS accuracy\n"
        "-- Fill rate:          SUM(shipped_qty) / NULLIF(SUM(ordered_qty), 0) AS fill_rate\n"
        "-- Backorder count:    SUM(CASE WHEN shipped_qty < ordered_qty THEN 1 ELSE 0 END)\n"
        "-- Supplier ranking:   COUNT(*) * (1 - on_time_rate) AS weighted_delay_score\n"
        "-- DPO:                AVG(DATEDIFF('day', invoice_date, payment_date))"
    ),
)
