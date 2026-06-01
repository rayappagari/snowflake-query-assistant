# Snowflake Query Assistant — Product Overview

**Ask questions about your data in plain English. Get answers in seconds.**

> **Live app:** https://laudable-clarity-production.up.railway.app

---

## What is it?

Snowflake Query Assistant is an AI-powered data query tool that lets anyone on your team explore your Snowflake data warehouse — without knowing SQL or needing a data analyst.

Type a question like *"What were our top 10 customers by revenue last quarter?"* and the assistant writes the database query, runs it, and explains the results in plain language — alongside a table of the actual data, ready to download.

---

## Who is it for?

| Role | How they use it |
|---|---|
| **Business analysts** | Self-serve data lookups without waiting for engineering |
| **Sales & account managers** | Instant access to customer and pipeline data |
| **Finance teams** | Revenue, cost, and margin queries on demand |
| **Executives** | Quick answers to ad-hoc data questions |
| **Operations** | Monitor KPIs and surface anomalies in real time |
| **Data administrators** | Manage user access and review the full query audit trail |

---

## Core capabilities

### Ask questions in plain English
Type questions the way you would ask a colleague. No SQL, no training required.

**Examples:**
- *"Show me total orders by region for the last 6 months"*
- *"Which products have the highest return rate?"*
- *"What is the average order value for enterprise customers?"*
- *"List all customers who haven't placed an order in 90 days"*
- *"Compare revenue this quarter versus the same quarter last year"*

---

### Domain-aware analysis
The assistant recognises the type of question being asked and applies specialist knowledge automatically — no extra configuration required.

| Domain | Activates when you ask about… | What it adds |
|---|---|---|
| **Revenue & trends** | Sales, profit, YoY/MoM/QoQ growth, quarterly performance | Period-over-period comparisons, growth rate calculations, outlier flags |
| **Customer analysis** | Top customers, churn, lifetime value, segmentation | RFM scoring, spend quartiles, recency and frequency metrics |
| **Inventory** | Stock levels, turnover, reorder alerts, supply chain | Days-of-supply calculations, stockout risk, slow-moving SKU identification |
| **Cohort & funnel** | Retention rates, funnel drop-off, conversion, onboarding | Cohort bucketing, per-stage conversion rates, largest drop-off identification |
| **Coding standards** | Naming conventions, schema quality, anti-patterns | Flags non-snake_case names, missing primary keys, overly wide tables, generic column names |
| **Performance optimization** | Slow queries, credit cost, warehouse load, partition pruning | Ranks queries by cost/time, surfaces spillage and poor pruning, suggests clustering keys and filters |
| **Data quality** | Nulls, duplicates, stale data, referential integrity, outliers | Reports defect rates as percentages, flags orphaned foreign keys and out-of-range values, prioritises by severity |
| **User behavior** | DAU/MAU/WAU, sessions, feature adoption, drop-off, activity patterns | Segments users by activity level, calculates stickiness ratios, highlights disengagement points in user journeys |
| **Financial reporting** | P&L, EBITDA, cash flow, budget vs actuals, cost centre spend | Applies correct sign conventions, computes absolute and percentage variance, flags material over/under-budget items |

This happens invisibly. You ask a normal question; the assistant silently selects the right domain lens and returns a richer, more targeted answer.

---

### Conversational follow-ups
The assistant remembers the context of your conversation, so you can refine results naturally without starting over.

**Example conversation:**
> **You:** *"Top 10 customers by revenue this year"*
> **Assistant:** *Shows a ranked table…*
> **You:** *"Now filter that to just the US"*
> **Assistant:** *Narrows the results automatically — no need to repeat yourself*
> **You:** *"Show me only the top 3"*
> **Assistant:** *Refines again instantly*

---

### Results you can act on

Every answer includes:

| | |
|---|---|
| **Plain-language summary** | What the data means, not just raw numbers — with anomaly flags for nulls, outliers, or unexpected values |
| **Data table** | Actual rows returned, with sticky column headers and scrolling for large result sets |
| **SQL inspector** | Click ▸ SQL to see exactly what query was run — collapsible, syntax-highlighted |
| **CSV export** | Download any result table with one click |
| **Cache indicator** | ⚡ badge shown when results are served instantly from cache |

---

### Query history
Every question is saved in the **History sidebar** during your session. Click any past question to re-run or use it as a starting point. Start a **New chat** at any time to clear context and begin fresh.

---

### Five visual themes
Choose the look that suits your preference — **Dark**, **Midnight**, **Ocean**, **Sunset**, or **Light**. Your choice is saved and remembered across sessions.

---

## Security & access control

### Individual user accounts
Each team member has their own username and password. There are no shared credentials. Access can be granted or revoked per person at any time through the built-in admin panel.

### Role-based access
Two roles are supported:

| Role | Capabilities |
|---|---|
| **Admin** | Query data + manage all users (add, edit, deactivate, delete) |
| **User** | Query data only |

### Read-only by design
The assistant can only run `SELECT` queries against your Snowflake warehouse. It is **architecturally impossible** for it to insert, update, delete, or modify any data. Write commands are blocked at the application level before they ever reach the database.

### Automatic PII detection
Before results are shown to the user, they are automatically scanned for common personally identifiable information — email addresses, phone numbers, Social Security Numbers, and credit card numbers. When detected, a visible warning is displayed so users are aware they are handling sensitive data.

### Session security
- Login required before any data is accessible
- Session tokens expire automatically after 8 hours
- Tokens are signed and encrypted — cannot be tampered with
- All traffic is encrypted via HTTPS

---

## Governance & audit

### Full audit trail
Every query is logged automatically and stored in a persistent database. Each log entry records:

- **Who** — the username of the person who asked
- **What** — the exact question asked in plain English
- **Query** — the SQL that was generated and executed
- **Result** — how many rows were returned
- **Time** — how long the query took (in milliseconds)
- **Cache** — whether the result was served from cache
- **PII** — whether personally identifiable information was detected
- **Status** — success or failure, with error detail if applicable

Audit logs are viewable in real time from the **Audit tab** in the application sidebar.

### Rate limiting
Each user is limited to 20 requests per minute to prevent accidental or intentional overuse of the system. Users who exceed the limit receive a clear message with a countdown until they can query again.

### Circuit protection
If the Snowflake database becomes temporarily unavailable, the system automatically stops sending requests rather than flooding it with retries. It probes for recovery after 60 seconds and resumes normal operation automatically — no manual intervention needed.

---

## Performance

### Intelligent model selection
The assistant automatically selects the most appropriate AI model for each question:
- **Simple lookups** (e.g. *"list all tables"*, *"count rows"*) → faster, lower-cost model
- **Complex analytics** (e.g. *"year-over-year trend by product category"*) → most capable model

Simultaneously, it detects the domain of the question and activates a matching specialist skill — injecting the right SQL patterns and analysis focus without any user input. Both choices happen invisibly; users always get the most accurate answer at the lowest cost.

### Result caching
If the same question generates the same database query within a 5-minute window, the result is served instantly from cache rather than running against Snowflake again. This reduces query costs and response time. A ⚡ badge is shown on cached responses.

### Connection pooling
The application maintains a pool of persistent Snowflake connections rather than opening a new connection for every query, significantly reducing response latency.

---

## Administration

### User management panel
Administrators have access to a built-in user management interface directly within the application — no need to access databases or run commands. Click **👥 Users** in the top navigation bar (visible to admins only).

From the Users panel, admins can:

| Action | Description |
|---|---|
| **View all users** | See username, email, role, active status, and account creation date |
| **Add a user** | Create a new account with username, email, password, and role |
| **Change role** | Promote a user to admin or demote to standard user |
| **Activate / deactivate** | Suspend a user's access without permanently deleting their account |
| **Reset password** | Set a new password for any user account |
| **Delete a user** | Permanently remove a user from the system |

> Administrators cannot deactivate or delete their own account, preventing accidental lockout.

---

## Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| **Hosting** | Railway | Cloud platform, automatic restarts, HTTPS |
| **Application** | Python / FastAPI | Backend API server (2 parallel processes) |
| **Frontend** | React / Vite | Browser-based chat interface |
| **User database** | PostgreSQL | Stores user accounts and persistent audit logs |
| **Cache** | Redis | Shared result cache and rate limiting across server processes |
| **AI models** | Anthropic Claude | SQL generation, result interpretation, error recovery |
| **Data warehouse** | Snowflake | Your existing warehouse — no migration required |
| **Monitoring** | Prometheus | Real-time metrics (query volume, latency, errors, cache hit rate) |

---

## What it connects to

The assistant connects to your **existing Snowflake warehouse** — there is no need to move, copy, or export your data. It reads from the same data your team already uses, through a dedicated connection that cannot write anything.

---

## What it does not do

| | |
|---|---|
| **Cannot modify data** | Write operations (insert, update, delete) are blocked at the system level |
| **Cannot access external data** | Only reads from your configured Snowflake warehouse |
| **Not a BI or charting tool** | Returns text summaries and data tables — not charts or dashboards |
| **No persistent conversation** | Conversation context clears when the browser tab is closed or refreshed |
| **No scheduled reports** | Does not send automated emails, alerts, or reports on a schedule |

---

## Getting access

Your administrator creates your account through the built-in user management panel. Once created:

1. Go to the app URL
2. Enter your username and password
3. Start asking questions

No installation, no downloads, no configuration, no training required.

---

## Frequently asked questions

**Can it access all tables in our Snowflake warehouse?**
It can access all tables the configured Snowflake service account has permission to read. Your database administrator controls which schemas and tables are visible by managing Snowflake roles — the assistant respects those permissions exactly.

**How accurate are the answers?**
The AI generates SQL that is validated against your actual schema before execution. Results come directly from your live Snowflake data — the AI does not estimate or invent numbers. For complex queries, the system retries up to 3 times before reporting an error. You can always rephrase a question if the first attempt doesn't return what you expected.

**Is our data sent to a third party?**
Table and column names (schema metadata) are sent to Anthropic's Claude API so it can understand your data structure and write accurate queries. Result data (the actual rows) is sent only during the interpretation step so Claude can summarise the findings. Anthropic does not use API request data to train their models. Please review [Anthropic's data processing terms](https://www.anthropic.com/privacy) for your compliance requirements.

**How do I know what query was run?**
Click **▸ SQL** on any response to expand the query that was executed — shown with full syntax highlighting. Every query is also permanently recorded in the Audit log, viewable from the sidebar.

**What happens if the AI can't answer my question?**
The system retries up to 3 times using error feedback from previous attempts. If all attempts fail, it returns a clear error message. Rephrasing the question usually resolves it — for example, breaking a complex multi-part question into simpler steps.

**Can multiple people use it at the same time?**
Yes. The system runs two server processes and handles concurrent users with separate session contexts. Each user's conversation is completely isolated from others.

**What happens if Snowflake is temporarily unavailable?**
The circuit breaker automatically stops sending queries when Snowflake is unresponsive, and retries after 60 seconds. Users receive a clear error message during the outage rather than waiting indefinitely.

**How do I add new team members?**
Log in as an admin and click **👥 Users** in the top navigation. Fill in the new user's username, email, password, and role. They can log in immediately.

**Can I revoke someone's access instantly?**
Yes. In the Users panel, click the **Active** toggle next to any user to deactivate their account immediately. They will not be able to log in until reactivated. Their account and history are preserved.
