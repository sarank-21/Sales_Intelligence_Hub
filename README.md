# 🏪 Sales Intelligence Hub — Sales Management System

> A multi-branch sales management and analytics platform built with Streamlit and MySQL, featuring role-based access control, real-time payment tracking, automated financial triggers, and an interactive SQL analysis dashboard.

---

## 📖 About the Project

The **Sales Intelligence Hub** is a full-stack sales management system designed to streamline customer registrations, payment collections, and financial reporting across multiple business branches. It connects a Streamlit-powered dashboard to a MySQL backend, automatically syncing payment records with sales statuses via database triggers. Branch admins manage their own sales, while Super Admins gain a unified view across all locations — making it ideal for multi-branch education or service businesses.

---

## 🛠️ Development Process

### 1. 🗄️ Database Design & Schema Setup
- Designed a normalized relational schema with four core tables: `branches`, `users`, `customer_sales`, and `payment_splits`
- Implemented `FOREIGN KEY` constraints to enforce referential integrity between branches, users, and sales records
- Automated database and table creation on first launch using SQLAlchemy's `setup_database()` function — zero manual setup required

### 2. 📥 Initial Data Loading from CSV
- Bootstrapped the system by loading CSV files for branches, users, customer records, and payment splits into MySQL using `load_initial_data()`
- Applied a one-time load guard (`SELECT COUNT(*) FROM users`) to prevent duplicate inserts across app restarts
- Hashed all user passwords using SHA-256 via `hash_password()` before inserting into the `users` table

### 3. 🔄 Data Integrity Fix for Existing Records
- Ran `fix_existing_data()` to retroactively recalculate `received_amount`, `pending_amount`, and `status` for all pre-existing sales records
- Used a `LEFT JOIN` against `payment_splits` with `IFNULL(SUM(...), 0)` to handle sales with no payments gracefully

### 4. ⚡ Automated Database Triggers
- Created three MySQL triggers (`after_insert_payment`, `after_update_payment`, `after_delete_payment`) to automatically update `received_amount`, `pending_amount`, and `status` on every payment change
- Triggers use `DECLARE` and `SELECT INTO` to compute totals directly in MySQL, keeping business logic close to the data layer
- Trigger creation is idempotent — wrapped in a session-state guard to run only once per app session

### 5. 🔐 Secure Role-Based Login System
- Implemented a two-role authentication model: **Super Admin** (cross-branch access) and **Admin** (single-branch access)
- Passwords stored and verified as SHA-256 hashes; login queries use parameterized inputs to prevent SQL injection
- Session state variables (`logged_in`, `role`, `branch`, `user`) persist authentication context across page navigations

### 6. 👤 Customer & Payment Entry System
- Built a two-step form flow: customer details → payment page, using `st.session_state.page` for navigation
- Implemented `get_open_sale()` to detect existing open sales by mobile + product + branch, enabling payment top-ups without creating duplicate records
- `insert_or_update_payment()` handles both new sale creation and payment appending in a single transactional block

### 7. 📊 Dynamic Dashboard with Filters
- Role-aware dashboard: Super Admins see all branches with a branch-filter dropdown; Admins see only their branch's data
- Real-time filter combinations (product × status × branch) using dynamic parameterized SQL queries
- Displayed key metrics via `st.metric()`: Total Branches, Customers, Products, Gross Sales, Received, and Pending

### 8. 🔍 SQL Analysis Module
- Built a four-category analysis portal with 20 pre-written SQL queries covering Basic, Aggregation, Join-Based, and Financial Tracking analyses
- Each category uses a nested selectbox navigation pattern, rendering query results as interactive `st.dataframe()` views
- Navigation managed through `st.session_state.analysis_page` for seamless back-and-forth routing

---

## 🔎 Key Features

### 🔐 Role-Based Access Control
Two distinct roles — Super Admin and Branch Admin — with scoped data visibility and branch-level isolation.

### ⚡ Auto-Triggered Payment Sync
MySQL triggers automatically recalculate `received_amount`, `pending_amount`, and `status` on every payment insert, update, or delete.

### 💳 Smart Payment Splitting
Multiple payments per sale are tracked individually in `payment_splits`, enabling full payment history and partial payment support.

### 🧩 Duplicate Sale Prevention
`get_open_sale()` checks for existing open sales by mobile + product + branch before creating new records, preventing duplicate entries.

### 📊 20-Query Analysis Dashboard
Four analysis categories with 20 pre-built SQL queries covering aggregations, joins, financial filters, and branch comparisons.

### 🔒 SHA-256 Password Security
All passwords are hashed before storage and verified at login — no plain-text credentials anywhere in the system.

### 🏢 Multi-Branch Architecture
Each sale, user, and admin is tied to a `branch_id`, supporting fully isolated multi-location operations under one platform.

### 📋 Dynamic Filtered Dashboard
Filter sales data by product, status, and branch simultaneously with real-time metric updates and tabular display.

### 🗄️ Zero-Setup Database Initialization
Database, tables, triggers, and seed data are all created automatically on first run — no manual SQL setup required.

### 📦 CSV-Based Data Bootstrapping
Initial data for branches, users, customers, and payments is loaded from CSV files with a one-time guard to prevent re-seeding.

---

## ✨ Features (Detailed)

### 🔐 Authentication & Session Management
- Secure login form with username, password (SHA-256 hashed), and role selection
- Session state tracks: `logged_in`, `user`, `role`, `branch`, `page`, `customer_data`, `analysis_page`
- Automatic redirect to the dashboard on successful login; logout clears all session state

### 📊 Dashboard (Customer Page)
- **Super Admin view**: 6 metrics — Total Branches, Customers, Products, Gross Sales, Received, Pending
- **Admin view**: 4 metrics — Total Customers, Gross Sales, Received, Pending
- Three-column filter bar: Product (8 options), Status (Open/Close), and Branch (Super Admin only)
- Full sales table with `st.dataframe()` rendered from dynamic parameterized SQL

### 👤 Customer Entry & Payment Flow
- Product pricing is pre-defined (`BI: ₹28,000`, `DA: ₹48,000`, `AI: ₹35,000`, etc.) and auto-populated
- Two-step navigation: Customer form → Payment page → Dashboard
- Payment methods supported: Cash, UPI, Card
- Payment amount validated: must be numeric, > 0, and ≤ gross sales value

### 🔍 SQL Analysis Module
| Category | Queries |
|---|---|
| 📊 Basic Queries | All records from customer_sales, branches, payment_splits; Open sales; Chennai branch sales |
| 📈 Aggregation Queries | Total gross sales, received, pending; count per branch; average gross |
| 🔗 Join-Based Queries | Sales + branch name; sales + payment totals; branch-wise totals; payment method; admin name |
| 💰 Financial Tracking | Pending > ₹5,000; Top 3 gross sales; highest branch; monthly summary; payment method totals |

### ⚡ Database Triggers
- `after_insert_payment`: Updates parent sale after a new payment is added
- `after_update_payment`: Recomputes totals when a payment record is edited
- `after_delete_payment`: Recalculates using `OLD.sale_id` when a payment is removed
- All triggers are idempotent — safely dropped and recreated on startup

---

## 🧰 Tech Stack

### 🖥️ Frontend / UI
| Library | Purpose |
|---|---|
| `streamlit` | Web app framework — pages, forms, metrics, session state |

### 📊 Data Processing & Analysis
| Library | Purpose |
|---|---|
| `pandas` | DataFrames, CSV loading, SQL result processing |

### 📈 Data Visualization
| Library | Purpose |
|---|---|
| `plotly.express` | Interactive charts — pie, bar (prepared, ready to enable) |

### 🗄️ Database
| Library | Purpose |
|---|---|
| `sqlalchemy` | ORM engine, connection pooling, `text()` parameterized queries |
| `mysql-connector-python` | MySQL driver (`mysql+mysqlconnector://`) |
| MySQL | Relational database — 4 tables, 3 triggers, FK constraints |

### ⚙️ Backend / Core Logic
| Library | Purpose |
|---|---|
| `hashlib` | SHA-256 password hashing |

---

## 🚀 Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/Sales_Intelligence_Hub.git
cd Sales_Intelligence_Hub
```

### 2. Create a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
Key libraries: `streamlit`, `pandas`, `sqlalchemy`, `mysql-connector-python`, `plotly`

### 4. Setup MySQL Database
- Ensure MySQL is running locally
- Update the connection string in `get_connection()` if your credentials differ:
```python
create_engine("mysql+mysqlconnector://root:0007@localhost")
```
- The app will auto-create the `Sales_Management_System` database and all tables on first launch

### 5. Prepare the CSV Files
Place the following files in `CSV/` (relative to the project root):
```
CSV/
├── branches.csv
├── users.csv
├── customer_sales.csv
└── payment_splits.csv
```
> Update the absolute paths in `load_initial_data()` if needed.

### 6. Run the Application
```bash
streamlit run app.py
```
Navigate to `http://localhost:8501` in your browser.

### 7. First-Time Initialization
On first launch, the app will automatically:
- Create the database and all 4 tables
- Load CSV seed data
- Fix any historical payment inconsistencies
- Create all 3 MySQL triggers

---

## 💼 Use Cases

1. **🏫 Multi-Branch Education Centers** — Track student enrollments, course fees (BI, DA, AI, FSD, ML, etc.), and payment collections across multiple city branches from a single Super Admin dashboard.

2. **💰 Partial Payment Management** — Record split payments for a single sale over time; the system automatically tracks how much has been received and how much is pending without manual recalculation.

3. **📍 Branch Admin Operations** — Allow branch-level admins to register new customers, accept payments, and monitor their branch's sales without access to other branches' data.

4. **📊 SQL-Driven Financial Reporting** — Use the built-in 20-query analysis dashboard to generate real-time reports on gross sales, pending dues, top performers, and payment method breakdowns.

5. **🔍 Audit & Reconciliation** — Identify open sales with high pending amounts, view payment method distributions, and generate monthly revenue summaries — all without writing a single query.

6. **📈 Branch Performance Benchmarking** — Super Admins can compare branch-wise total gross sales and identify the highest-performing location using the Financial Tracking analysis module.

---

## 🔮 Future Enhancements

1. **📤 Export Reports to PDF/Excel** — Add one-click download for filtered dashboard data and analysis query results
2. **📱 SMS/WhatsApp Payment Reminders** — Auto-notify customers with pending balances using Twilio or WhatsApp Business API
3. **📊 Live Plotly Charts on Dashboard** — Activate the commented-out pie and bar charts for branch-wise and product-wise sales visualization
4. **🔑 Password Reset via Email OTP** — Allow admins to securely reset forgotten passwords via email verification
5. **🧾 Invoice Generator** — Auto-generate and email PDF invoices to customers on payment submission
6. **📅 Date-Range Filters on Dashboard** — Add start/end date pickers to the dashboard filter bar for period-specific reporting
7. **👥 Admin Management by Super Admin** — Allow Super Admins to create, edit, and deactivate branch admin accounts from within the UI
8. **☁️ Cloud Deployment** — Deploy to Streamlit Cloud or AWS EC2 with a managed RDS MySQL instance for remote access

---

## 🏗️ How It Works

```
┌──────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT UI (Browser)                        │
│         Login Page │ Dashboard │ Payment Page │ Analysis Page        │
└───────────────────────────────┬──────────────────────────────────────┘
                                │  st.session_state
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LOGIC LAYER                         │
│  login()  │  Customer_register()  │  insert_or_update_payment()      │
│  get_open_sale()  │  analysis()   │  hash_password()                 │
└──────┬──────────────────────┬──────────────────────────┬─────────────┘
       │                      │                          │
       ▼                      ▼                          ▼
┌─────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│  Auth Layer │   │   Data Entry Layer   │   │   Analysis Layer     │
│  SHA-256    │   │  customer_sales      │   │  20 SQL Queries      │
│  hash check │   │  payment_splits      │   │  Basic / Aggregation │
│  role check │   │  INSERT / SELECT     │   │  Join / Financial    │
└─────────────┘   └──────────┬───────────┘   └──────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         MYSQL TRIGGER LAYER                          │
│  after_insert_payment → recalculate received_amount + status         │
│  after_update_payment → recalculate received_amount + status         │
│  after_delete_payment → recalculate received_amount + status         │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│               MySQL: Sales_Management_System Database                │
│  branches │ users │ customer_sales │ payment_splits                  │
│  FK constraints │ ENUM status │ AUTO_INCREMENT PKs                   │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     INITIALIZATION PIPELINE                          │
│  setup_database() → load_initial_data() → fix_existing_data()        │
│  create_triggers() → session_state guards (init, triggers_created)   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 📝 Project Overview

The **Sales Intelligence Hub** is a multi-branch sales management platform that combines a Streamlit frontend with a MySQL backend to handle the full lifecycle of a customer sale — from initial registration to final payment clearance. The system enforces strict role-based access: Super Admins view and analyze data across all branches with cross-branch filters, while Branch Admins operate within their own scoped data. At the data layer, three MySQL triggers (`after_insert_payment`, `after_update_payment`, `after_delete_payment`) automatically maintain financial consistency by recalculating `received_amount`, `pending_amount`, and `status` on every payment event — eliminating manual reconciliation entirely. The application bootstraps itself on first run by creating the database schema, loading CSV seed data, and initializing triggers, making deployment a single-command process. An embedded SQL analysis module provides 20 categorized queries — spanning basic lookups, aggregations, join-based reports, and financial filters — giving both technical and non-technical users direct insight into sales performance without writing a line of SQL.

---

⭐ **If you find this project useful, give it a star on GitHub and share your feedback!**
