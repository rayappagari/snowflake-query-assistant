from skills.base import Skill

skill = Skill(
    name="user_behavior",
    description="User behavior analytics: engagement, session analysis, feature adoption, and activity patterns",
    keywords=[
        "user behavior", "user activity", "user engagement", "engagement",
        "session", "sessions", "session length", "session duration",
        "page views", "pageviews", "clicks", "click rate", "click-through",
        "feature adoption", "feature usage", "feature engagement", "adoption", "adoption rate",
        "active users", "dau", "mau", "wau", "daily active", "monthly active",
        "weekly active", "power users", "casual users",
        "drop off", "drop-off", "bounce", "bounce rate",
        "time on site", "time spent", "visit frequency", "visit duration",
        "event tracking", "events", "user journey", "user path",
        "heatmap", "scroll depth", "interaction", "interactions",
        "login frequency", "last login", "inactive users", "inactive",
    ],
    prompt_hint=(
        "This is a user behavior analysis. "
        "Identify engagement patterns: DAU/MAU/WAU trends, session frequency and duration, "
        "feature adoption rates, and drop-off points in user journeys. "
        "Segment users by activity level (power, regular, casual, dormant). "
        "Highlight where users disengage or stop progressing. "
        "Express metrics as rates and averages alongside raw counts for context. "
        "Flag unusual spikes or drops in activity."
    ),
    sql_hint=(
        "-- User behavior patterns:\n"
        "-- DAU/MAU ratio (stickiness): COUNT(DISTINCT CASE WHEN date = CURRENT_DATE THEN user_id END)\n"
        "--                              / NULLIF(COUNT(DISTINCT user_id), 0)\n"
        "-- Session duration:           DATEDIFF('second', session_start, session_end) AS duration_seconds\n"
        "-- Event funnel:               COUNT(DISTINCT CASE WHEN event = 'step_1' THEN user_id END) AS step1_users\n"
        "-- Activity segmentation:      CASE WHEN event_count >= 20 THEN 'power'\n"
        "--                                  WHEN event_count >= 5  THEN 'regular'\n"
        "--                                  ELSE 'casual' END\n"
        "-- Inactive users:             DATEDIFF('day', MAX(event_time), CURRENT_DATE) > 30\n"
        "-- Rolling 7-day active:       COUNT(DISTINCT user_id) WHERE event_time >= DATEADD('day', -7, CURRENT_DATE)"
    ),
)
