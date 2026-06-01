from skills.base import Skill

skill = Skill(
    name="customer_segmentation",
    description="Customer analysis, segmentation, and lifetime value",
    keywords=[
        "customer", "user", "client", "segment", "ltv", "lifetime value",
        "churn", "retention", "acquisition", "top customers", "active customers",
        "high value", "at-risk", "new customers", "repeat", "purchase frequency",
    ],
    prompt_hint=(
        "This is a customer analysis. "
        "Identify meaningful segments (high-value, at-risk, new, churned). "
        "Surface LTV, purchase frequency, and recency where relevant. "
        "Flag customers with unusual patterns (sudden drop-off, spike in spend). "
        "Rank customers clearly if a top-N question is asked."
    ),
    sql_hint=(
        "-- Customer segmentation patterns:\n"
        "-- Recency:   DATEDIFF('day', last_order_date, CURRENT_DATE) AS days_since_last_order\n"
        "-- Frequency: COUNT(DISTINCT order_id) AS order_count\n"
        "-- Monetary:  SUM(order_value) AS total_spend\n"
        "-- Quartile:  NTILE(4) OVER (ORDER BY total_spend DESC) AS spend_quartile\n"
        "-- Include zero-order customers: LEFT JOIN orders ON customers.id = orders.customer_id"
    ),
)
