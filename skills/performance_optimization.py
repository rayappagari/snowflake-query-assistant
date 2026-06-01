from skills.base import Skill

skill = Skill(
    name="performance_optimization",
    description="Query performance analysis, slow query detection, and Snowflake optimization audits",
    keywords=[
        "performance", "slow query", "slow queries", "slowest", "optimize", "optimization",
        "long running", "long-running", "expensive query", "expensive queries",
        "query cost", "credits consumed", "credit usage", "credits used", "credits",
        "warehouse utilization",
        "bytes scanned", "partitions scanned", "pruning", "partition pruning",
        "spillage", "disk spill", "remote spill", "clustering", "cluster key",
        "materialized view", "query history", "execution time", "elapsed time",
        "full table scan", "missing filter", "cartesian", "query profile",
    ],
    prompt_hint=(
        "This is a query performance analysis. "
        "Identify the most expensive or slowest queries, highlight waste (full table scans, "
        "poor partition pruning, disk spillage, cartesian joins). "
        "Quantify cost in credits and bytes scanned where available. "
        "Rank findings by impact — most expensive first. "
        "Suggest concrete optimizations: add clustering keys, add WHERE filters, "
        "use result caching, right-size the warehouse, or convert to a materialized view."
    ),
    sql_hint=(
        "-- Performance analysis patterns (query SNOWFLAKE.ACCOUNT_USAGE or INFORMATION_SCHEMA):\n"
        "-- Slow queries:        SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY\n"
        "--                      ORDER BY TOTAL_ELAPSED_TIME DESC\n"
        "-- High bytes scanned:  BYTES_SCANNED, PARTITIONS_SCANNED, PARTITIONS_TOTAL\n"
        "-- Pruning ratio:       1 - (PARTITIONS_SCANNED / NULLIF(PARTITIONS_TOTAL, 0))\n"
        "-- Disk spillage:       BYTES_SPILLED_TO_LOCAL_STORAGE, BYTES_SPILLED_TO_REMOTE_STORAGE\n"
        "-- Credit cost:         CREDITS_USED_CLOUD_SERVICES\n"
        "-- Warehouse load:      SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY\n"
        "-- Filter recent:       WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP)"
    ),
)
