from skills.base import Skill

skill = Skill(
    name="financial_reporting",
    description="Financial reporting: P&L, balance sheet, cash flow, budget vs actuals, and period-end close",
    keywords=[
        "financial report", "financial reporting", "financial statement", "financial statements",
        "profit and loss", "p&l", "income statement", "balance sheet",
        "cash flow", "cash flow statement", "operating expenses", "opex",
        "capital expenditure", "capex", "gross profit", "gross margin",
        "net income", "net profit", "ebitda", "ebit",
        "budget", "budget vs actual", "budget variance", "forecast vs actual",
        "variance analysis", "actuals", "headcount cost",
        "accounts receivable", "accounts payable", "ar", "ap",
        "accruals", "amortization", "amortisation", "depreciation",
        "period close", "month end", "quarter end", "year end",
        "general ledger", "cost center", "cost centre", "department spend",
        "tax", "effective tax rate", "working capital",
    ],
    prompt_hint=(
        "This is a financial reporting analysis. "
        "Present numbers with the correct sign convention (expenses as negative, revenue as positive). "
        "Always include period labels (e.g. Q1 FY2024) and prior-period comparisons where data allows. "
        "Compute variance as both absolute (£/$) and percentage. "
        "Flag items that are materially over or under budget (>5% variance is typically significant). "
        "Distinguish between recurring and one-off items where identifiable. "
        "Use standard financial terminology (gross profit, EBITDA, operating leverage) consistently."
    ),
    sql_hint=(
        "-- Financial reporting patterns:\n"
        "-- Period label:      TO_CHAR(date_col, 'YYYY-MM') AS period or DATE_TRUNC('quarter', date_col)\n"
        "-- Budget variance:   actual - budget AS abs_variance,\n"
        "--                    ROUND((actual - budget) / NULLIF(budget, 0) * 100, 2) AS pct_variance\n"
        "-- Gross profit:      SUM(revenue) - SUM(cogs) AS gross_profit\n"
        "-- Gross margin:      ROUND(gross_profit / NULLIF(SUM(revenue), 0) * 100, 2) AS gross_margin_pct\n"
        "-- EBITDA:            net_income + interest + tax + depreciation + amortisation\n"
        "-- Rolling YTD:       SUM(amount) OVER (PARTITION BY YEAR(date_col) ORDER BY date_col)\n"
        "-- Prior period join: JOIN financials prior ON prior.period = DATEADD('month', -1, current.period)"
    ),
)
