from skills.base import Skill

skill = Skill(
    name="cohort_analysis",
    description="Cohort retention, funnel analysis, and conversion tracking",
    keywords=[
        "cohort", "retention", "funnel", "conversion", "drop-off", "drop off",
        "stage", "onboarding", "activation", "churn rate", "week 1", "week 4",
        "day 7", "day 30", "signup", "reactivation",
    ],
    prompt_hint=(
        "This is a cohort or funnel analysis. "
        "Define cohorts by acquisition/signup period. "
        "Compute retention rates at each period (week 1, week 4, week 12). "
        "For funnels, show count and conversion rate at each stage. "
        "Highlight where the largest drop-off occurs."
    ),
    sql_hint=(
        "-- Cohort analysis patterns:\n"
        "-- Cohort bucket: DATE_TRUNC('month', signup_date) AS cohort_month\n"
        "-- Period offset: DATEDIFF('month', signup_date, activity_date) AS period_number\n"
        "-- Retention rate: COUNT(DISTINCT user_id) / FIRST_VALUE(COUNT(DISTINCT user_id))\n"
        "--                  OVER (PARTITION BY cohort_month ORDER BY period_number)\n"
        "-- Funnel step conversion: step_n_users / NULLIF(step_1_users, 0)"
    ),
)
