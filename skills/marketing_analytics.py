from skills.base import Skill

skill = Skill(
    name="marketing_analytics",
    description="Marketing analytics: campaign performance, attribution, CAC, ROAS, and channel analysis",
    keywords=[
        "marketing", "campaign", "campaigns", "campaign performance",
        "attribution", "multi-touch attribution", "first touch", "last touch",
        "cac", "customer acquisition cost", "cost per acquisition", "cpa",
        "roas", "return on ad spend", "ad spend", "ad performance",
        "impressions", "clicks", "ctr", "click-through rate",
        "conversion", "conversions", "conversion rate", "conversion funnel",
        "leads", "lead generation", "qualified leads", "mql", "sales qualified lead",
        "channel", "channels", "marketing channel", "paid search", "organic",
        "email campaign", "email open rate", "email click rate", "unsubscribe",
        "social media", "paid social", "organic social",
        "seo", "sem", "ppc", "cost per click", "cpc",
        "landing page", "bounce rate", "traffic source",
        "marketing roi", "marketing spend", "media mix",
        "utm", "utm source", "utm medium", "utm campaign",
        "retargeting", "remarketing", "audience", "reach", "frequency",
    ],
    prompt_hint=(
        "This is a marketing analytics analysis. "
        "Focus on campaign efficiency (ROAS, CPA, CTR) and channel contribution. "
        "Compare performance across channels, campaigns, and time periods. "
        "Highlight top-performing and underperforming campaigns — rank by ROAS or CPA. "
        "For attribution, clarify the model used (first-touch, last-touch, linear). "
        "Express CAC as total spend / new customers acquired in the period. "
        "Flag campaigns with high spend but low conversion rate as priority optimisation targets. "
        "Include percentage change vs prior period where data allows."
    ),
    sql_hint=(
        "-- Marketing analytics patterns:\n"
        "-- CTR:          clicks / NULLIF(impressions, 0) AS ctr\n"
        "-- Conversion rate: conversions / NULLIF(clicks, 0) AS conversion_rate\n"
        "-- CPA:          total_spend / NULLIF(conversions, 0) AS cost_per_acquisition\n"
        "-- ROAS:         revenue_attributed / NULLIF(ad_spend, 0) AS roas\n"
        "-- CAC:          SUM(marketing_spend) / NULLIF(COUNT(DISTINCT new_customer_id), 0)\n"
        "-- Channel mix:  SUM(spend) GROUP BY channel ORDER BY spend DESC\n"
        "-- UTM grouping: utm_source, utm_medium, utm_campaign from events/sessions table\n"
        "-- Period delta: (current - prior) / NULLIF(prior, 0) AS pct_change\n"
        "-- Filter active campaigns: WHERE campaign_status = 'active' AND end_date >= CURRENT_DATE"
    ),
)
