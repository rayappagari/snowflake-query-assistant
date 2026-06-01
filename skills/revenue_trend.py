from skills.base import Skill

skill = Skill(
    name="revenue_trend",
    description="Revenue and financial performance trend analysis",
    keywords=[
        "revenue", "sales", "income", "earnings", "profit", "margin",
        "yoy", "mom", "qoq", "year-over-year", "month-over-month",
        "quarter-over-quarter", "trend", "growth", "decline",
        "quarterly", "monthly", "annual", "fiscal",
    ],
    prompt_hint=(
        "This is a revenue/financial trend analysis. "
        "Focus on period-over-period comparisons (MoM, QoQ, YoY). "
        "Highlight significant changes, outliers, and trend direction. "
        "Format monetary values clearly (e.g. $1.2M). "
        "If comparing periods, compute the percentage change explicitly."
    ),
    sql_hint=(
        "-- Revenue trend patterns:\n"
        "-- Monthly bucketing:  DATE_TRUNC('month', date_col)\n"
        "-- Quarterly bucketing: DATE_TRUNC('quarter', date_col)\n"
        "-- Period-over-period: LAG(revenue, 1) OVER (ORDER BY period) AS prev_revenue\n"
        "-- Growth rate: ROUND(revenue / NULLIF(prev_revenue, 0) - 1, 4) AS growth_rate\n"
        "-- Rolling window: DATEADD('day', -30, CURRENT_DATE)"
    ),
)
