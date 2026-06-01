# Snowflake Query Assistant — Client Brief

**Version:** 1.0  
**Live application:** https://laudable-clarity-production.up.railway.app

---

## Executive Summary

Snowflake Query Assistant is an AI-powered data query tool that gives every member of your team instant, self-serve access to your Snowflake data warehouse — without writing SQL, without waiting for a data analyst, and without any training.

Ask a question in plain English. Get a clear answer, a data table, and the exact SQL that was run — in seconds.

---

## The Problem It Solves

Most organisations have valuable data locked inside Snowflake that only a small number of technical users can access. Business teams must submit requests to data analysts and wait hours or days for answers. This slows decisions, creates bottlenecks, and underutilises the investment already made in data infrastructure.

Snowflake Query Assistant removes that bottleneck entirely.

---

## How It Works

A user types a question — exactly as they would ask a colleague. The assistant:

1. Identifies which tables in your warehouse are relevant
2. Selects the right AI model based on question complexity
3. Detects the business domain (revenue, marketing, supply chain, etc.) and applies specialist knowledge
4. Generates a validated, read-only SQL query
5. Executes it against your Snowflake warehouse
6. Returns a plain-language summary alongside the full data table

The entire process typically completes in under 5 seconds.

---

## Who Uses It

| Role | What they get |
|---|---|
| **Executives** | Instant answers to ad-hoc data questions without waiting for reports |
| **Sales & account managers** | Real-time customer and pipeline data on demand |
| **Finance teams** | Revenue, cost, margin, and budget variance queries in seconds |
| **Marketing teams** | Campaign performance, ROAS, CAC, and attribution analysis |
| **Operations** | Live KPI monitoring and anomaly detection |
| **Business analysts** | Self-serve lookups without engineering dependency |
| **Data administrators** | Full audit trail and user access management |

---

## Core Features

### Natural Language Queries
Ask questions in plain English — no SQL knowledge required.

**Example questions:**
- *"What were our top 10 customers by revenue last quarter?"*
- *"Show me month-over-month growth for each product category"*
- *"Which campaigns have the highest return on ad spend?"*
- *"How fresh is the data in our orders table?"*
- *"Which suppliers are causing the most delivery delays?"*
- *"Compare budget vs actuals for each department this quarter"*

---

### Domain-Aware Intelligence
The assistant automatically detects the business domain of each question and activates a specialist lens — no configuration required.

| Domain | Activates for questions about… | Added intelligence |
|---|---|---|
| **Revenue & trends** | Sales, profit, YoY/MoM/QoQ growth | Period-over-period comparisons, growth rates, outlier flags |
| **Customer analysis** | Churn, lifetime value, top customers, segmentation | RFM scoring, spend quartiles, recency and frequency |
| **Marketing analytics** | Campaigns, ROAS, CAC, CTR, attribution, UTM tracking | Ranks by ROAS and CPA, flags high-spend low-conversion campaigns |
| **Financial reporting** | P&L, EBITDA, budget vs actuals, cost centre spend | Correct sign conventions, absolute and percentage variance |
| **Supply chain** | Lead times, supplier performance, backorders, fill rate | Ranks suppliers by delay impact, lead time variability |
| **Inventory** | Stock levels, turnover, reorder alerts, stockouts | Days-of-supply, stockout risk, slow-moving SKU identification |
| **User behavior** | DAU/MAU/WAU, sessions, feature adoption, drop-off | Activity segmentation, stickiness ratios, disengagement points |
| **Cohort & funnel** | Retention, conversion, onboarding, funnel drop-off | Cohort bucketing, per-stage conversion rates |
| **Data quality** | Nulls, duplicates, stale data, referential integrity | Defect rates as percentages, findings ranked by severity |
| **Performance** | Slow queries, credit cost, partition pruning, spillage | Ranks by cost impact, suggests concrete Snowflake optimisations |
| **Coding standards** | Schema naming, anti-patterns, missing keys | Flags violations by severity: critical, warning, informational |

---

### Conversational Follow-Ups
The assistant remembers the context of your conversation. Refine results naturally:

> *"Top 10 customers by revenue this year"*  
> → *Shows a ranked table*  
> *"Now filter to just the US"*  
> → *Narrows results automatically*  
> *"Show me only the top 3"*  
> → *Refines instantly*

---

### Results You Can Act On
Every response includes:

| Component | Description |
|---|---|
| **Plain-language summary** | What the data means — with anomaly flags for outliers, nulls, and unexpected values |
| **Data table** | Full result rows with sticky headers and scrolling |
| **SQL inspector** | Click to expand the exact query that ran — syntax-highlighted |
| **CSV export** | Download any result in one click |
| **Cache indicator** | ⚡ shown when results are served instantly from cache |

---

## Security & Access Control

### Individual User Accounts
Every team member has a personal username and password. No shared credentials. Access is granted and revoked per person through the built-in admin panel.

### Role-Based Access

| Role | Permissions |
|---|---|
| **Admin** | Query data + full user management (add, edit, deactivate, delete) |
| **User** | Query data only |

### Read-Only by Design
The assistant can **only** run `SELECT` queries. It is architecturally impossible for it to insert, update, delete, or modify any data. Write commands are blocked before they ever reach Snowflake.

### Automatic PII Detection
Every result is automatically scanned for personally identifiable information — email addresses, phone numbers, Social Security Numbers, and credit card numbers — before being shown to the user. A visible warning is displayed when PII is detected.

### Session Security
- Login required before any data is accessible
- Sessions expire automatically after 8 hours
- Tokens are cryptographically signed and cannot be tampered with
- All traffic encrypted via HTTPS

---

## Governance & Audit

### Full Audit Trail
Every query is permanently logged the moment it completes — automatically, with no user action required. Logs are written to three destinations simultaneously to ensure nothing is lost:

| Destination | When active | Survives restarts? |
|---|---|---|
| **PostgreSQL** | When a PostgreSQL service is connected | Yes — primary persistent store |
| **SQLite** | Always (built-in fallback) | Within deployment; attach a volume for full persistence |
| **Stdout / log aggregator** | Always | Yes — captured by Railway logs or any log platform |

Each log entry records:

| Field | What is recorded |
|---|---|
| **Timestamp** | Exact UTC time the query completed |
| **User** | Username of the person who asked |
| **Question** | The exact plain-English question typed |
| **SQL** | The query that was generated and executed against Snowflake |
| **Rows returned** | How many rows came back |
| **Latency** | Full pipeline wall-clock time in milliseconds |
| **Cache hit** | Whether Snowflake was bypassed (result served from cache) |
| **PII detected** | Types of sensitive data found in the result (email, SSN, phone, credit card) |
| **Status** | Success or failure, with full error detail on failure |

Audit logs are viewable in real time from the **Audit tab** in the application sidebar, showing the 100 most recent entries. PostgreSQL is queried first when available; SQLite is used as fallback so the audit view always returns data.

### What This Means for Compliance
- Every data access is traceable to a named individual
- The exact SQL executed is preserved — not just the question
- PII exposure events are flagged automatically and timestamped
- Logs cannot be modified by end users — they are append-only
- All log destinations are written before the response is returned to the user

### Rate Limiting
Each user is limited to 20 requests per minute to prevent overuse. Users who exceed the limit receive a clear message with a countdown.

### Circuit Protection
If Snowflake becomes temporarily unavailable, the system automatically stops sending requests and retries after 60 seconds — protecting your warehouse and notifying users clearly instead of leaving them waiting.

---

## Performance

### Intelligent Model Selection
The assistant automatically selects the most cost-efficient AI model for each question:
- **Simple lookups** → fast, lower-cost model (Haiku)
- **Complex analytics** → most capable model (Opus)

### Result Caching
Identical queries within a 5-minute window are served instantly from cache — no Snowflake compute cost, near-zero latency.

### Connection Pooling
Persistent Snowflake connections are maintained in a pool, eliminating connection overhead on every query.

---

## Administration

Administrators manage users directly within the application — no database access or command-line tools required.

| Action | Description |
|---|---|
| **Add users** | Create accounts with username, email, password, and role |
| **Change roles** | Promote to admin or demote to standard user |
| **Activate / deactivate** | Suspend access without deleting the account |
| **Reset passwords** | Set a new password for any user |
| **Delete users** | Permanently remove a user from the system |

---

## Infrastructure & Technology

| Component | Technology |
|---|---|
| **Hosting** | Railway (cloud, automatic restarts, HTTPS) |
| **Backend** | Python / FastAPI (2 parallel workers) |
| **Frontend** | React / Vite (browser-based) |
| **AI models** | Anthropic Claude (Haiku + Opus) |
| **Data warehouse** | Your existing Snowflake — no migration |
| **User database** | PostgreSQL (accounts + persistent audit log) |
| **Cache** | Redis (cross-worker result cache + rate limiting) |
| **Monitoring** | Prometheus metrics + Grafana-ready dashboards |

---

## What You Need to Get Started

### Prerequisites
| Requirement | Details |
|---|---|
| **Snowflake account** | Existing warehouse with a service account that has read access to the schemas you want to query |
| **Anthropic API key** | For Claude AI model access |
| **Hosting** | Railway (recommended) or any cloud platform that supports Docker |

### Optional (for full feature set)
| Add-on | Enables |
|---|---|
| **PostgreSQL** | Persistent audit log + JWT user authentication |
| **Redis** | Cross-worker result cache + shared rate limiting |

### Setup Time
A standard deployment takes approximately **30–60 minutes**:
1. Deploy the Docker container to Railway (or your preferred platform)
2. Set the required environment variables (Snowflake credentials, Anthropic API key)
3. Create the first admin account
4. Add team members through the built-in user panel

No code changes required for standard deployments.

---

## What It Does Not Do

| Limitation | Detail |
|---|---|
| **Cannot modify data** | Write operations are blocked at the system level — SELECT only |
| **Cannot access external data** | Reads only from your configured Snowflake warehouse |
| **Not a BI or charting tool** | Returns text summaries and data tables — not charts or dashboards |
| **No persistent conversation** | Context clears when the browser tab is closed |
| **No scheduled reports** | Does not send automated emails or recurring reports |

---

## Frequently Asked Questions

**Can it access all tables in our Snowflake warehouse?**
It accesses all tables the configured Snowflake service account has permission to read. Your database administrator controls visibility by managing Snowflake roles — the assistant respects those permissions exactly.

**How accurate are the answers?**
The AI generates SQL validated against your actual schema before execution. Results come directly from your live Snowflake data — nothing is estimated or invented. The system retries up to 3 times on failure. You can always rephrase a question if the first attempt doesn't return what you expected.

**Is our data sent to a third party?**
Table and column names (schema metadata) are sent to Anthropic's Claude API so it can write accurate queries. Result data (actual rows) is sent only during the interpretation step so Claude can summarise the findings. Anthropic does not use API request data to train their models. Review [Anthropic's data processing terms](https://www.anthropic.com/privacy) for compliance requirements.

**Can multiple people use it at the same time?**
Yes. The system runs two server processes and handles concurrent users with fully isolated session contexts.

**What happens if Snowflake is temporarily unavailable?**
The circuit breaker stops sending queries automatically and retries after 60 seconds. Users receive a clear error message rather than waiting indefinitely.

**How do we add or remove users?**
Log in as an admin, click Users in the navigation bar, and add or deactivate accounts instantly — no engineering involvement required.

**Can we control which data users can see?**
Yes — through Snowflake's native role and permission system. The assistant respects whatever access the service account has. Restrict schemas or tables in Snowflake and those restrictions apply automatically.

---

## Contact & Access

To request a demo or get access, contact your project administrator or reach out via the live app at:

**https://laudable-clarity-production.up.railway.app**
