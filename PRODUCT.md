# Snowflake Query Assistant — Product Overview

**Ask questions about your data in plain English. Get answers in seconds.**

> Live app: https://laudable-clarity-production.up.railway.app

---

## What is it?

Snowflake Query Assistant is an AI-powered data query tool that lets anyone on your team explore your Snowflake data warehouse — without knowing SQL or needing a data analyst.

You type a question like *"What were our top 10 customers by revenue last quarter?"* and the assistant writes the database query, runs it, and explains the results back to you in plain language — alongside a table of the actual data.

---

## Who is it for?

| Role | How they use it |
|---|---|
| **Business analysts** | Self-serve data lookups without waiting for engineering |
| **Sales & account managers** | Instant access to customer and pipeline data |
| **Finance teams** | Revenue, cost, and margin queries on demand |
| **Executives** | Quick answers to ad-hoc data questions |
| **Operations** | Monitor KPIs and surface anomalies in real time |

---

## Core capabilities

### Natural language queries
Type questions the same way you would ask a colleague. No SQL required.

**Examples:**
- *"Show me total orders by region for the last 6 months"*
- *"Which products have the highest return rate?"*
- *"What is the average order value for enterprise customers?"*
- *"List all customers who haven't placed an order in 90 days"*

---

### Conversational follow-ups
The assistant remembers the context of your conversation, so you can refine results naturally — just like talking to a person.

**Example conversation:**
> You: *"Top 10 customers by revenue this year"*
> Assistant: *Shows results…*
> You: *"Now filter that to just the US"*
> Assistant: *Narrows the results automatically — no need to repeat yourself*

---

### Results you can act on

Every answer includes:

- **Plain-language summary** — what the data means, not just numbers
- **Data table** — the actual rows returned, with sticky column headers and scrolling for large datasets
- **SQL inspector** — click to see exactly what query was run (collapsible, syntax-highlighted)
- **CSV export** — download any result set with one click
- **Anomaly flagging** — the AI highlights unexpected values, nulls, or outliers automatically

---

### Query history & session memory
- Every question you ask is saved in the **History sidebar** for the current session
- Click any past question to re-run or refine it
- Start a **New chat** at any time to clear context and begin fresh

---

### Five visual themes
Choose the look that suits your preference or environment — Dark, Midnight, Ocean, Sunset, or Light. Your choice is remembered across sessions.

---

## Security & access control

### Individual user accounts
Each team member has their own username and password. There are no shared credentials — access can be granted or revoked per person at any time.

### Role-based access
Two roles are supported:
- **Admin** — full access including user management
- **User** — query access only

### Read-only by design
The assistant can only run `SELECT` queries — it is **technically impossible** for it to modify, delete, or write any data in your Snowflake warehouse. Every write command is blocked at the application level before it reaches the database.

### PII detection
Results are automatically scanned for common personally identifiable information (emails, phone numbers, social security numbers, credit card numbers). When detected, a warning is displayed so users are aware they are viewing sensitive data.

### Password-protected access
The application requires login before any data can be accessed. All session tokens expire after 8 hours and must be renewed.

### Encrypted connections
All traffic between the browser and the application is encrypted via HTTPS. Credentials and tokens are never stored in plain text.

---

## Governance & audit

### Full audit trail
Every query is logged automatically with:
- Who asked (username)
- What they asked (the question)
- What SQL was generated and run
- How many rows were returned
- How long it took
- Whether any PII was detected
- Success or failure status

Logs are viewable in the **Audit tab** in the sidebar and are stored persistently in the database.

### Rate limiting
Each user is limited to 20 requests per minute to prevent accidental or intentional overuse of the system.

### Circuit protection
If the Snowflake database becomes temporarily unavailable, the system automatically stops sending requests (rather than flooding it) and retries gracefully once it recovers.

---

## Performance

### Intelligent model selection
Simple questions (e.g. *"list all tables"*) are answered using a faster, cheaper AI model. Complex analytical questions (e.g. *"year-over-year revenue trend by product category"*) automatically use the most capable model. This happens transparently with no action needed from the user.

### Result caching
If the same question is asked twice within 5 minutes, the result is served instantly from cache — with a ⚡ badge shown to indicate a cached response. This saves time and reduces database costs.

### Connection pooling
The application maintains a pool of persistent database connections rather than opening a new one for each query, significantly reducing response latency.

---

## Administration

### User management panel
Admins have access to a built-in user management interface (no need to touch code or databases). From the **Users** panel, admins can:

| Action | Description |
|---|---|
| **Add users** | Create accounts with username, email, password, and role |
| **Change roles** | Promote a user to admin or demote to standard user |
| **Activate / deactivate** | Suspend access without deleting the account |
| **Reset passwords** | Set a new password for any user |
| **Delete accounts** | Permanently remove a user |

---

## Infrastructure

| Component | Detail |
|---|---|
| **Hosting** | Railway — cloud platform with automatic scaling |
| **Database** | PostgreSQL for user accounts and audit logs |
| **Cache** | Redis for shared result caching across servers |
| **AI models** | Anthropic Claude (Haiku and Opus 4.8) |
| **Data warehouse** | Snowflake (your existing warehouse — no migration needed) |
| **Availability** | Two parallel server processes with automatic restarts |

---

## What it connects to

The assistant connects to your **existing Snowflake warehouse** — there is no need to move, copy, or export your data. It queries the same data your team already uses, using a dedicated read-only connection.

---

## What it does not do

| Limitation | Detail |
|---|---|
| **Cannot modify data** | Write operations are blocked by design |
| **Cannot access external data** | Only queries what is in your Snowflake warehouse |
| **Not a BI tool** | Does not produce charts or dashboards (text + table output only) |
| **Session memory only** | Conversation context resets when the page is reloaded |
| **No scheduled reports** | Does not send automated emails or alerts (yet) |

---

## Getting access

Contact your administrator to be set up with a username and password. Once your account is created:

1. Go to the app URL
2. Enter your username and password
3. Start asking questions

No installation, no downloads, no training required.

---

## Frequently asked questions

**Can it access all tables in my Snowflake warehouse?**
It can access all tables the configured Snowflake user has permission to read. Your database administrator controls which tables are visible by managing Snowflake user roles as usual.

**How accurate are the answers?**
The AI generates SQL that is validated against your actual schema before execution. Results come directly from your Snowflake data — the AI does not invent or estimate numbers. Complex queries may occasionally require a follow-up rephrasing if the first attempt doesn't capture the intent precisely.

**Is my data sent to a third party?**
The schema structure (table and column names) and query results are sent to Anthropic's Claude API to generate SQL and summaries. Raw row data is sent only for the interpretation step. Anthropic does not use API inputs to train models. Review Anthropic's data processing terms for your compliance requirements.

**How do I know what query was run?**
Click **▸ SQL** on any response to see the exact SQL query that was executed. Every query is also recorded in the Audit log.

**What happens if I ask something the AI can't answer?**
The system retries up to 3 times with error feedback before returning a clear failure message. You can rephrase the question and try again.

**Can multiple people use it at the same time?**
Yes. The system handles concurrent users and maintains separate conversation contexts per session.
