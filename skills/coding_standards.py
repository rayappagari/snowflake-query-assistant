from skills.base import Skill

skill = Skill(
    name="coding_standards",
    description="SQL and schema coding standards, naming conventions, and best-practice audits",
    keywords=[
        "coding standards", "naming convention", "naming conventions",
        "snake case", "snake_case", "camel case", "camelcase", "column naming",
        "table naming", "best practices", "standards compliance",
        "code quality", "select *", "missing primary key", "no index",
        "undocumented", "without comments", "inconsistent", "violation",
        "audit schema", "schema quality", "poorly named", "bad naming",
    ],
    prompt_hint=(
        "This is a coding standards or schema quality audit. "
        "Check for naming convention violations (e.g. non-snake_case table or column names), "
        "structural issues (missing primary keys, columns named 'id' without constraints), "
        "and anti-patterns (SELECT *, ambiguous column names, overly wide tables). "
        "Group findings by severity where possible: critical, warning, informational. "
        "Be specific — quote the offending object names in the answer."
    ),
    sql_hint=(
        "-- Coding standards audit patterns (query INFORMATION_SCHEMA):\n"
        "-- Non-snake_case names: REGEXP_LIKE(column_name, '[A-Z]') to find camelCase\n"
        "-- Tables without PKs:   LEFT JOIN table_constraints WHERE constraint_type = 'PRIMARY KEY'\n"
        "-- Very wide tables:     COUNT(column_name) > 50 GROUP BY table_name\n"
        "-- Generic column names: column_name IN ('id','data','value','info','misc')\n"
        "-- All metadata lives in INFORMATION_SCHEMA.COLUMNS and INFORMATION_SCHEMA.TABLES"
    ),
)
