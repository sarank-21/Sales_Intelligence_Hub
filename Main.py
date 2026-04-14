import streamlit as st
import pandas as pd
import hashlib
from sqlalchemy import create_engine, text
import plotly.express as px


# -----------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------
st.set_page_config(page_title="Sales Management System", layout="wide")

# -----------------------------------------------------------
# DB CONNECTION
# -----------------------------------------------------------
def get_connection():
    engine = create_engine("mysql+mysqlconnector://root:0007@localhost")

    with engine.connect() as conn:
        conn.execute(text("CREATE DATABASE IF NOT EXISTS Sales_Management_System"))
        conn.commit()

    return create_engine("mysql+mysqlconnector://root:0007@localhost/Sales_Management_System")

db_engine = get_connection()

# -----------------------------------------------------------
# CREATE TABLES
# -----------------------------------------------------------
def setup_database():
    with db_engine.begin() as conn:

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS branches (
            branch_id INT AUTO_INCREMENT PRIMARY KEY,
            branch_name VARCHAR(50),
            branch_admin_name VARCHAR(50)
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100),
            password VARCHAR(255),
            email VARCHAR(255) UNIQUE,
            branch_id INT,
            role ENUM('Super Admin','Admin'),
            FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS customer_sales (
            sale_id INT AUTO_INCREMENT PRIMARY KEY,
            branch_id INT,
            date DATE DEFAULT (CURRENT_DATE),
            name VARCHAR(50),
            mobile_number VARCHAR(15),
            product_name VARCHAR(30),
            gross_sales DECIMAL(12,2),
            received_amount DECIMAL(12,2) DEFAULT 0,
            pending_amount DECIMAL(12,2),
            status ENUM('Open','Close') DEFAULT 'Open',
            FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS payment_splits (
            payment_id INT AUTO_INCREMENT PRIMARY KEY,
            sale_id INT,
            payment_date DATE DEFAULT (CURRENT_DATE),
            amount_paid DECIMAL(12,2),
            payment_method VARCHAR(50),
            FOREIGN KEY (sale_id) REFERENCES customer_sales(sale_id)
        )
        """))
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -----------------------------------------------------------
# LOAD CSV DATA
# -----------------------------------------------------------
def load_initial_data():
    with db_engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()

    if count > 0:
        return

    # Load CSV
    branch_data = pd.read_csv(r"D:\PROJECTS\Anna_Project_1\Sales_Intelligence_Hub\CSV\branches.csv")
    user_data = pd.read_csv(r"D:\PROJECTS\Anna_Project_1\Sales_Intelligence_Hub\CSV\users.csv")
    customer_data = pd.read_csv(r"D:\PROJECTS\Anna_Project_1\Sales_Intelligence_Hub\CSV\customer_sales.csv")
    payment_data = pd.read_csv(r"D:\PROJECTS\Anna_Project_1\Sales_Intelligence_Hub\CSV\payment_splits.csv")

    # ❌ No hashing
    user_data["password"] = user_data["password"].apply(hash_password)

    branch_data.to_sql("branches", db_engine, if_exists="append", index=False)
    user_data.to_sql("users", db_engine, if_exists="append", index=False)
    customer_data.to_sql("customer_sales", db_engine, if_exists="append", index=False)
    payment_data.to_sql("payment_splits", db_engine, if_exists="append", index=False)

# -----------------------------------------------------------
# FIX OLD DATA
# -----------------------------------------------------------
def fix_existing_data():
    with db_engine.begin() as conn:

        conn.execute(text("""
            UPDATE customer_sales cs
            LEFT JOIN (
                SELECT sale_id, IFNULL(SUM(amount_paid),0) AS total_paid
                FROM payment_splits
                GROUP BY sale_id
            ) ps ON cs.sale_id = ps.sale_id
            SET 
                cs.received_amount = IFNULL(ps.total_paid, 0),
                cs.pending_amount = cs.gross_sales - IFNULL(ps.total_paid, 0),
                cs.status = CASE 
                    WHEN cs.gross_sales - IFNULL(ps.total_paid, 0) = 0 THEN 'Close'
                    ELSE 'Open'
                END
        """))
# -----------------------------------------------------------
# TRIGGERS (ONLY UPDATE RECEIVED + STATUS)
# -----------------------------------------------------------
def create_triggers():
    with db_engine.begin() as conn:

        # ✅ Use database name explicitly
        conn.execute(text("DROP TRIGGER IF EXISTS Sales_Management_System.after_insert_payment"))
        conn.execute(text("DROP TRIGGER IF EXISTS Sales_Management_System.after_update_payment"))
        conn.execute(text("DROP TRIGGER IF EXISTS Sales_Management_System.after_delete_payment"))

        trigger_logic = """
            DECLARE total_paid DECIMAL(10,2);

            SELECT IFNULL(SUM(amount_paid),0)
            INTO total_paid
            FROM payment_splits
            WHERE sale_id = NEW.sale_id;

            UPDATE customer_sales
            SET 
                received_amount = total_paid,
                pending_amount = gross_sales - total_paid,
                status = CASE 
                    WHEN gross_sales - total_paid = 0 THEN 'Close'
                    ELSE 'Open'
                END
            WHERE sale_id = NEW.sale_id;
        """

        conn.execute(text(f"""
        CREATE TRIGGER Sales_Management_System.after_insert_payment
        AFTER INSERT ON payment_splits
        FOR EACH ROW
        BEGIN
            {trigger_logic}
        END
        """))

        conn.execute(text(f"""
        CREATE TRIGGER Sales_Management_System.after_update_payment
        AFTER UPDATE ON payment_splits
        FOR EACH ROW
        BEGIN
            {trigger_logic}
        END
        """))

        conn.execute(text("""
        CREATE TRIGGER Sales_Management_System.after_delete_payment
        AFTER DELETE ON payment_splits
        FOR EACH ROW
        BEGIN
            DECLARE total_paid DECIMAL(10,2);

            SELECT IFNULL(SUM(amount_paid),0)
            INTO total_paid
            FROM payment_splits
            WHERE sale_id = OLD.sale_id;

            UPDATE customer_sales
            SET 
                received_amount = total_paid,
                pending_amount = gross_sales - total_paid,
                status = CASE 
                    WHEN gross_sales - total_paid = 0 THEN 'Close'
                    ELSE 'Open'
                END
            WHERE sale_id = OLD.sale_id;
        END
        """))
# -----------------------------------------------------------
# LOGIN SYSTEM (SECURE)
# -----------------------------------------------------------
def login(username, password, role):

    query = text("""
        SELECT * FROM users
        WHERE username = :username 
        AND password = :password 
        AND role = :role
    """)

    df = pd.read_sql(query, db_engine, params={
        "username": username,
        "password": password,
        "role": role
    })

    return df

# -----------------------------------------------------------
# INIT DB
# -----------------------------------------------------------
if "init" not in st.session_state:
    setup_database()
    load_initial_data() 
    fix_existing_data()
    st.session_state.init = True

# ✅ Handle triggers separately (important)
if "triggers_created" not in st.session_state:
    try:
        create_triggers()
    except Exception as e:
        # Ignore if already exists (safe fallback)
        pass
    st.session_state.triggers_created = True
def get_open_sale(mobile, product, branch_id):
    query = text("""
        SELECT sale_id FROM customer_sales
        WHERE mobile_number = :mobile
        AND product_name = :product
        AND branch_id = :branch
        AND status = 'Open'
        LIMIT 1
    """)

    df = pd.read_sql(query, db_engine, params={
        "mobile": mobile,
        "product": product,
        "branch": branch_id
    })

    return None if df.empty else int(df.iloc[0]["sale_id"])
# -----------------------------------------------------------
# CUSTOMER INSERT
# -----------------------------------------------------------
def insert_or_update_payment(name, mobile, product, gross, amount, method):

    # ✅ Get branch from customer data (works for both roles)
    branch = st.session_state.customer_data.get("branch")

    if branch is None:
        st.error("⚠️ Branch not selected")
        st.stop()

    branch_id = int(branch)

    with db_engine.begin() as conn:

        # 🔍 Check existing open sale
        sale_id = get_open_sale(mobile, product, branch_id)

        if sale_id is None:
            # 🆕 NEW SALE
            result = conn.execute(
                text("""
                    INSERT INTO customer_sales
                    (branch_id, name, mobile_number, product_name, gross_sales, received_amount, status)
                    VALUES (:branch, :name, :mobile, :product, :gross, 0, 'Open')
                """),
                {
                    "branch": branch_id,
                    "name": name,
                    "mobile": mobile,
                    "product": product,
                    "gross": gross
                }
            )
            sale_id = int(result.lastrowid)

        # 💳 ALWAYS insert payment
        conn.execute(
            text("""
                INSERT INTO payment_splits (sale_id, amount_paid, payment_method)
                VALUES (:sale_id, :amount, :method)
            """),
            {
                "sale_id": sale_id,
                "amount": float(amount),
                "method": method
            }
        )
# -----------------------------------------------------------
# CUSTOMER FORM
# -----------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "customer"
def Customer_register():

    st.subheader("👤 Customer Entry")

    # ✅ STEP 0: Branch Selection (ADD HERE)
    if st.session_state.role == "Super Admin":

        branch_df = pd.read_sql("SELECT branch_id, branch_name FROM branches", db_engine)
        branch_map = dict(zip(branch_df["branch_name"], branch_df["branch_id"]))

        selected_branch_name = st.selectbox("Select Branch", list(branch_map.keys()))
        branch_id = branch_map[selected_branch_name]

    else:
        branch_id = st.session_state.branch

    # ✅ Store selected branch
    st.session_state.selected_branch = branch_id


    # -------------------------------
    # 👇 YOUR EXISTING CODE (UNCHANGED)
    # -------------------------------
    col1,col2 = st.columns(2)
    with col1 :
        name = st.text_input("Customer Name")
    with col2:
        mobile = st.text_input("Mobile Number")

    col1,col2 = st.columns(2)
    with col1:
        product_dict = {
        "BI":28000,"DA":48000,"AI":35000,
        "FSD":45000,"ML":42000,"SQL":25000,
        "DS":40000,"BA":30000
        }
        product_name = st.selectbox("Product", ["Select"] + list(product_dict.keys()))
    with col2:
        gross = product_dict.get(product_name, 0)
        st.text_input("Gross Sales", value=str(gross), disabled=True)

    # 👉 STEP 1: Proceed to payment
    if st.button("Proceed to Payment"):
        
        if not name or not mobile or product_name == "Select":
            st.error("⚠️ Fill all fields")
            
        elif not mobile.isdigit() or len(mobile) != 10:
            st.error("⚠️ Invalid mobile number")

        elif st.session_state.selected_branch is None:
            st.error("⚠️ Branch not selected")
            
        else:
            st.session_state.customer_data = {
                "name": name,
                "mobile": mobile,
                "product": product_name,
                "gross": gross,
                "branch": st.session_state.selected_branch   # ✅ ADD THIS
            }
            
            st.session_state.page = "payment"
            st.rerun()
# -----------------------------------------------------------
# ANALYSIS PART
# -----------------------------------------------------------
if "analysis_page" not in st.session_state:
    st.session_state.analysis_page = "home"
def analysis():

    # ✅ Initialize state
    if "analysis_page" not in st.session_state:
        st.session_state.analysis_page = "home"

    # -------------------------------
    # 🏠 HOME PAGE
    # -------------------------------
    if st.session_state.analysis_page == "home":

        topic = st.selectbox(
            "Analysis",
            ["Select Analysis",
             "Basic Queries",
             "Aggregation Queries",
             "Join-Based Queries",
             "Financial Tracking Queries"]
        )

        if topic != "Select Analysis":
            st.session_state.analysis_page = topic
            st.rerun()
        if st.button("⬅ Back to Dashboard"):
            st.session_state.page = "customer"
            st.rerun()

    # -------------------------------
    # 📊 BASIC QUERIES
    # -------------------------------
    elif st.session_state.analysis_page == "Basic Queries":

        st.subheader("📊 Basic Queries")
        

        topic1 = st.selectbox("Analysis",
                             ["Select Query",
                              "Retrieve all records from the customer_sales table",
                              "Retrieve all records from the branches table",
                              "Retrieve all records from the payment_splits table",
                              "Display all sales with status = 'Open'",
                              "Retrieve all sales belonging to the Chennai branch"])
        if topic1 == "Select Query":
            st.info("Please select a query") 
        
# -- Retrieve all records from the customer_sales table.
        if topic1 == "Retrieve all records from the customer_sales table":  
                query = """select * from customer_sales;"""
                df = pd.read_sql(query,db_engine)
                st.dataframe(df)

# -- Retrieve all records from the branches table.
        elif topic1 == "Retrieve all records from the branches table":  
                query = """select * from branches;"""
                df = pd.read_sql(query,db_engine)
                st.dataframe(df)

# -- Retrieve all records from the payment_splits table.
        elif topic1 == "Retrieve all records from the payment_splits table":  
                query = """select * from payment_splits;"""
                df = pd.read_sql(query,db_engine)
                st.dataframe(df)

# -- Display all sales with status = 'Open'.
        elif topic1 == "Display all sales with status = 'Open'":
                query = """select gross_sales,received_amount,pending_amount,status from customer_sales 
                   where status = 'Open';"""
                df = pd.read_sql(query,db_engine)
                st.dataframe(df)

# -- Retrieve all sales belonging to the Chennai branch.-- 
        elif topic1 == "Retrieve all sales belonging to the Chennai branch":
                query = """select c.gross_sales,c.received_amount,c.pending_amount,b.branch_name  from customer_sales as c
                   inner join branches as b on c.branch_id = b.branch_id where branch_name = 'Chennai';"""
                df = pd.read_sql(query,db_engine)
                st.dataframe(df)
        if st.button("⬅ Back"):
            st.session_state.analysis_page = "home"
            st.rerun()

    # -------------------------------
    # 📈 AGGREGATION QUERIES
    # -------------------------------
    elif st.session_state.analysis_page == "Aggregation Queries":

        st.subheader("📈 Aggregation Queries")
        

        topic2 = st.selectbox("Aggregation Queries",                           
                             ["Select Query",
                              "Calculate the total gross sales across all branches",
                              "Calculate the total received amount across all sales",
                              "Calculate the total pending amount across all sales",
                              "Count the total number of sales per branch" ,
                              "Find the average gross sales amount"])
        
        if topic2 == "Select Query":
            st.info("Please select a query") 

# -- Calculate the total gross sales across all branches.
        if topic2 == "Calculate the total gross sales across all branches":
            query = """select sum(gross_sales) as Total_Sales from customer_sales;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

# -- Calculate the total received amount across all sales. 
        elif topic2 == "Calculate the total received amount across all sales":
            query = """select sum(received_amount) as Total_Recevied from customer_sales;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

# -- Calculate the total pending amount across all sales.
        elif topic2 == "Calculate the total pending amount across all sales":
            query = """select sum(pending_amount) as Total_Recevied from customer_sales;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

# -- Count the total number of sales per branch.
        elif topic2 == "Count the total number of sales per branch":
            query = """select sum(c.gross_sales),b.branch_name  from customer_sales as c
            inner join branches as b on c.branch_id = b.branch_id group by branch_name;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

# -- Find the average gross sales amount.
        elif topic2 == "Find the average gross sales amount":
            query = """select avg(gross_sales) as Total_Sales from customer_sales;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)
        
        if st.button("⬅ Back"):
            st.session_state.analysis_page = "home"
            st.rerun()
    # -------------------------------
    # 🔗 JOIN QUERIES
    # -------------------------------
    elif st.session_state.analysis_page == "Join-Based Queries":

        st.subheader("🔗 Join-Based Queries")
        

        topic3 = st.selectbox("Join-Based Queries",
                             ["Select Query",
                              "Retrieve sales details along with the branch name",
                              "Retrieve sales details along with total payment received (using payment_splits)",
                              "Show branch-wise total gross sales (using JOIN & GROUP BY)",
                              "Display sales along with payment method used",
                              "Retrieve sales along with branch admin name"])
        
        if topic3 == "Select Query":
            st.info("Please select a query") 

# -- Retrieve sales details along with the branch name.
        if topic3 == "Retrieve sales details along with the branch name":    
            query = """select c.product_name,c.gross_sales,c.received_amount,c.pending_amount,b.branch_name  from customer_sales as c
            inner join branches as b on c.branch_id = b.branch_id;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

# -- Retrieve sales details along with total payment received (using payment_splits).
        elif topic3 == "Retrieve sales details along with total payment received (using payment_splits)":    
            query = """select c.product_name,c.gross_sales,c.received_amount,p.amount_paid from customer_sales as c
            inner join payment_splits as p on c.sale_id = p.sale_id;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

# -- Show branch-wise total gross sales (using JOIN & GROUP BY).
        elif topic3 == "Show branch-wise total gross sales (using JOIN & GROUP BY)":
            query = """select sum(c.gross_sales),b.branch_name  from customer_sales as c
            inner join branches as b on c.branch_id = b.branch_id group by branch_name;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

# -- Display sales along with payment method used.
        elif topic3 == "Display sales along with payment method used":
            query = """select c.product_name,c.gross_sales,c.received_amount,c.pending_amount,p.payment_method  
            from customer_sales as c
            inner join payment_splits as p on c.sale_id = p.sale_id;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

# -- Retrieve sales along with branch admin name.
        elif topic3 == "Retrieve sales along with branch admin name": 
            query = """select c.product_name,c.gross_sales,c.received_amount,c.pending_amount,b.branch_name ,b.branch_admin_name 
            from customer_sales as c
            inner join branches as b on c.branch_id = b.branch_id;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

        if st.button("⬅ Back"):
            st.session_state.analysis_page = "home"
            st.rerun()
    # -------------------------------
    # 💰 FINANCIAL QUERIES
    # -------------------------------
    elif st.session_state.analysis_page == "Financial Tracking Queries":

        st.subheader("💰 Financial Queries")

        topic4 = st.selectbox("Financial Tracking Queries",
                             ["Select Query",
                              "Find sales where the pending amount is greater than 5000",
                              "Retrieve top 3 highest gross sales",
                              "Find the branch with highest total gross sales",
                              "Retrieve monthly sales summary (group by month & year)",
                              "Calculate payment method-wise total collection (Cash / UPI / Card)"])
        
        if topic4 == "Select Query":
            st.info("Please select a query") 
            
# -- Find sales where the pending amount is greater than 5000.
        if topic4 == "Find sales where the pending amount is greater than 5000":   
            query = """select * from customer_sales
            where pending_amount > 5000;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

# -- Retrieve top 3 highest gross sales.
        elif topic4 == "Retrieve top 3 highest gross sales":   
            query = """select distinct(gross_sales) from customer_sales 
            order by gross_sales desc limit 3;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

# -- Find the branch with highest total gross sales.
        elif topic4 == "Find the branch with highest total gross sales":   
            query = """select sum(c.gross_sales) as Total_sales,b.branch_name  from customer_sales as c
            inner join branches as b on c.branch_id = b.branch_id group by branch_name order by Total_sales desc limit 1;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

# -- Retrieve monthly sales summary (group by month & year).
        elif topic4 == "Retrieve monthly sales summary (group by month & year)":   
            query = """select MONTH(date) as month,sum(gross_sales) from customer_sales
            group by month;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

# -- Calculate payment method-wise total collection (Cash / UPI / Card).
        elif topic4 == "Calculate payment method-wise total collection (Cash / UPI / Card)":
            query = """select sum(c.gross_sales),p.payment_method
            from customer_sales as c
            inner join payment_splits as p on c.sale_id = p.sale_id  group by payment_method"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)
        
        if st.button("⬅ Back"):
            st.session_state.analysis_page = "home"
            st.rerun()


# -----------------------------------------------------------
# LOGIN UI
# -----------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    st.title("🔐 Login")

    # ✅ FORM START
    with st.form("login_form"):

        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["Select","Super Admin","Admin"])

        submit = st.form_submit_button("Login")   # ✅ IMPORTANT

    # ✅ HANDLE LOGIN OUTSIDE FORM
    if submit:

        if not user or not pwd or role == "Select":
            st.warning("⚠️ Please fill all fields")

        else:
            hashed_pwd = hash_password(pwd)
            df = login(user, hashed_pwd, role)

            if not df.empty:
                st.session_state.logged_in = True
                st.session_state.user = df.iloc[0]["username"]
                st.session_state.role = df.iloc[0]["role"]
                st.session_state.branch = df.iloc[0]["branch_id"]

                # ✅ RESET PAGE
                st.session_state.page = "customer"

                st.success("✅ Login Successful")
                st.rerun()
            else:
                st.error("❌ Invalid Credentials")

# -----------------------------------------------------------
# MAIN APP AFTER LOGIN
# -----------------------------------------------------------
else:

    # ✅ SESSION VARIABLES
    role = st.session_state.role
    branch = st.session_state.get("branch")
    user = st.session_state.user

    # -------------------------------
    # 📄 CUSTOMER PAGE (Dashboard)
    # -------------------------------
    if st.session_state.page == "customer":

        st.title("📊 Dashboard")
        st.subheader(f"👤 Welcome, {user}")

        # -------------------------------
        # 🔹 FILTERS
        # -------------------------------
        colA, colB, colC = st.columns(3)

        with colA:
            product = st.selectbox(
                "Product",
                ["All","BI","DA","AI","FSD","ML","SQL","DS","BA"],
                key="product_filter"
            )

        with colB:
            status = st.selectbox(
                "Status",
                ["All","Open","Close"],
                key="status_filter"
            )
        # ✅ Branch filter only for Super Admin
        selected_branch_id = None
        if role == "Super Admin":
            with colC:
                branch_df = pd.read_sql("SELECT branch_id, branch_name FROM branches", db_engine)
                
                branch_map = dict(zip(branch_df["branch_name"], branch_df["branch_id"]))
                
                # ✅ Add "All"
                branch_options = ["All"] + list(branch_map.keys())
                
                selected_branch_name = st.selectbox("Branch", branch_options)
                
                if selected_branch_name != "All":
                    selected_branch_id = branch_map[selected_branch_name]
                

        # -------------------------------
        # 🔹 BASE QUERY
        # -------------------------------
        if role == "Super Admin":
            query = "SELECT * FROM customer_sales WHERE 1=1"
            params = {}
        else:
            query = "SELECT * FROM customer_sales WHERE branch_id = :branch"
            params = {"branch": int(branch)}

        # -------------------------------
        # 🔹 APPLY FILTERS
        # -------------------------------
        if product != "All":
            query += " AND product_name = :product"
            params["product"] = str(product)

        if status != "All":
            query += " AND status = :status"
            params["status"] = str(status)
        
        # ✅ Branch filter (ONLY for Super Admin)
        if role == "Super Admin" and selected_branch_id is not None:
            query += " AND branch_id = :branch_id"
            params["branch_id"] = int(selected_branch_id)


        # -------------------------------
        # 🔹 EXECUTE
        # -------------------------------
        sales = pd.read_sql(text(query), db_engine, params=params)

        # -------------------------------
        # 🔹 METRICS
        # -------------------------------
        if role == "Super Admin":
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                st.metric("Total Branches", sales['branch_id'].nunique())
            with col2:
                st.metric("Total Customers", sales['name'].count())
            with col3:
                st.metric("Total Products", sales['product_name'].nunique())
            with col4:
                st.metric("Total Sales", f"₹ {sales['gross_sales'].sum():,.0f}")
            with col5:
                st.metric("Received", f"₹ {sales['received_amount'].sum():,.0f}")
            with col6:
                st.metric("Pending", f"₹ {sales['pending_amount'].sum():,.0f}")

            
        else:  # Admin
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("TotalCustomers", sales['name'].count())
            with col2:
                st.metric("Total Sales", f"₹ {sales['gross_sales'].sum():,.0f}")
            with col3:
                st.metric("Received", f"₹ {sales['received_amount'].sum():,.0f}")
            with col4:
                st.metric("Pending", f"₹ {sales['pending_amount'].sum():,.0f}")

        # -------------------------------
        # 🔹 TABLE
        # -------------------------------
        st.dataframe(sales)

        # -------------------------------
        # ➕ CUSTOMER FORM
        # -------------------------------
        
        with st.expander("➕ Add Customer or Update Payment"):
            Customer_register()
        if role == "Admin" or role == "Super Admin":
            if st.button("📊 Go to Analysis"):
                st.session_state.page = "analysis"
                st.rerun()
        # -------------------------------
        # 🚪 LOGOUT
        # -------------------------------
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.page = "customer"
            st.session_state.customer_data = {}
            st.rerun()

    # -------------------------------
    # 💳 PAYMENT PAGE
    # -------------------------------
    elif st.session_state.page == "payment":

        st.title("💳 Payment Page")

        amount = st.text_input("Amount Paid", key="pay_amount")
        payment_method = st.selectbox(
            "Payment Method", ["Select","Cash","UPI","Card"], key="pay_method"
        )

        data = st.session_state.customer_data
        gross = float(data["gross"])   # ✅ get correct value
        
        if st.button("Submit Payment"):
            
            if not amount or payment_method == "Select":
                st.error("⚠️ Fill all fields")
                
            elif not amount.replace('.', '', 1).isdigit():
                st.error("⚠️ Enter valid number")
                
            elif float(amount) <= 0:
                st.error("Amount must be greater than 0")
                
            elif float(amount) > gross:
                st.error(f"⚠️ Amount cannot exceed product price (₹ {gross})")
                
            else:
                insert_or_update_payment(
                    data["name"],
                    data["mobile"],
                    data["product"],
                    gross,
                    amount,
                    payment_method)
                
                st.success("✅ Customer + Payment Saved")
                
                st.session_state.page = "customer"
                st.session_state.customer_data = {}
                st.rerun()

        # 🔙 BACK BUTTON
        if st.button("⬅ Back To Dashboard"):
            st.session_state.page = "customer"
            st.rerun()
        
    elif st.session_state.page == "analysis":
        
        st.title("📊 Analysis Dashboard")
        analysis()   # ✅ CALL YOUR FUNCTION HERE
        
        