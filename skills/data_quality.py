from skills.base import Skill

skill = Skill(
    name="data_quality",
    description="Data quality checks: nulls, duplicates, freshness, referential integrity, and outliers",
    keywords=[
        "data quality", "data issues", "null values", "nulls", "missing values",
        "missing data", "duplicates", "duplicate rows", "duplicate records", "duplicate",
        "data freshness", "stale data", "last updated", "not updated", "fresh", "freshness",
        "referential integrity", "orphaned records", "orphaned rows",
        "foreign key", "broken references", "inconsistent", "inconsistency",
        "outliers", "anomalies", "invalid values", "out of range",
        "empty strings", "blank values", "data drift", "schema drift",
        "row count drop", "unexpected zeros", "negative values",
    ],
    prompt_hint=(
        "This is a data quality analysis. "
        "Check for nulls (count and percentage per column), duplicate rows, "
        "stale or unrefreshed data (compare MAX(updated_at) to CURRENT_DATE), "
        "orphaned foreign keys, out-of-range or negative values, and empty strings. "
        "Express findings as percentages alongside raw counts so severity is clear. "
        "Prioritise columns or tables with the highest defect rates. "
        "Distinguish between structural issues (schema/type problems) and "
        "content issues (bad values, stale rows)."
    ),
    sql_hint=(
        "-- Data quality patterns:\n"
        "-- Null rate:        SUM(CASE WHEN col IS NULL THEN 1 ELSE 0 END) / COUNT(*) AS null_rate\n"
        "-- Duplicate rows:   COUNT(*) - COUNT(DISTINCT primary_key_col) AS duplicate_count\n"
        "-- Freshness:        DATEDIFF('hour', MAX(updated_at), CURRENT_TIMESTAMP) AS hours_since_refresh\n"
        "-- Orphaned FKs:     LEFT JOIN parent ON child.fk = parent.id WHERE parent.id IS NULL\n"
        "-- Out-of-range:     COUNT(CASE WHEN value < 0 OR value > expected_max THEN 1 END)\n"
        "-- Empty strings:    SUM(CASE WHEN TRIM(col) = '' THEN 1 ELSE 0 END)\n"
        "-- Metadata source:  INFORMATION_SCHEMA.TABLES for row counts and last-altered timestamps"
    ),
)
