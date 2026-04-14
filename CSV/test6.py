import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# -----------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------
st.set_page_config(
    page_title="Client Query Management System",
    page_icon="💼",
    layout="wide"
)

# -----------------------------------------------------------
# LOAD DATA
# -----------------------------------------------------------
branch_data = pd.read_csv(r"D:\PROJECTS\Anna_Project_1\Sales_Intelligence_Hub\CSV\branches.csv")
user_data = pd.read_csv(r"D:\PROJECTS\Anna_Project_1\Sales_Intelligence_Hub\CSV\users.csv")
payment_data = pd.read_csv(r"D:\PROJECTS\Anna_Project_1\Sales_Intelligence_Hub\CSV\payment_splits.csv")
customer_data = pd.read_csv(r"D:\PROJECTS\Anna_Project_1\Sales_Intelligence_Hub\CSV\customer_sales.csv")

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
def Dataset_SetUp():
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
            role ENUM('Super Admin', 'Admin'),
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
            pending_amount DECIMAL(12,2) DEFAULT 0,
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

# -----------------------------------------------------------
# CREATE TRIGGERS
# -----------------------------------------------------------
def create_triggers():
    with db_engine.begin() as conn:

        conn.execute(text("DROP TRIGGER IF EXISTS after_insert_payment_splits"))
        conn.execute(text("DROP TRIGGER IF EXISTS after_update_payment_splits"))
        conn.execute(text("DROP TRIGGER IF EXISTS after_delete_payment_splits"))

        # INSERT
        conn.execute(text("""
        CREATE TRIGGER after_insert_payment_splits
        AFTER INSERT ON payment_splits
        FOR EACH ROW
        BEGIN
            DECLARE total_paid DECIMAL(10,2);

            SELECT IFNULL(SUM(amount_paid), 0)
            INTO total_paid
            FROM payment_splits
            WHERE sale_id = NEW.sale_id;

            UPDATE customer_sales
            SET 
                received_amount = total_paid,
                pending_amount  = gross_sales - total_paid,
                status = CASE 
                            WHEN gross_sales - total_paid = 0 THEN 'Close'
                            ELSE 'Open'
                         END
            WHERE sale_id = NEW.sale_id;
        END
        """))

        # UPDATE
        conn.execute(text("""
        CREATE TRIGGER after_update_payment_splits
        AFTER UPDATE ON payment_splits
        FOR EACH ROW
        BEGIN
            DECLARE total_paid DECIMAL(10,2);

            SELECT IFNULL(SUM(amount_paid), 0)
            INTO total_paid
            FROM payment_splits
            WHERE sale_id = NEW.sale_id;

            UPDATE customer_sales
            SET 
                received_amount = total_paid,
                pending_amount  = gross_sales - total_paid,
                status = CASE 
                            WHEN gross_sales - total_paid = 0 THEN 'Close'
                            ELSE 'Open'
                         END
            WHERE sale_id = NEW.sale_id;
        END
        """))

        # DELETE
        conn.execute(text("""
        CREATE TRIGGER after_delete_payment_splits
        AFTER DELETE ON payment_splits
        FOR EACH ROW
        BEGIN
            DECLARE total_paid DECIMAL(10,2);

            SELECT IFNULL(SUM(amount_paid), 0)
            INTO total_paid
            FROM payment_splits
            WHERE sale_id = OLD.sale_id;

            UPDATE customer_sales
            SET 
                received_amount = total_paid,
                pending_amount  = gross_sales - total_paid,
                status = CASE 
                            WHEN gross_sales - total_paid = 0 THEN 'Close'
                            ELSE 'Open'
                         END
            WHERE sale_id = OLD.sale_id;
        END
        """))

# -----------------------------------------------------------
# INSERT DATA (SAFE)
# -----------------------------------------------------------
def insert_data():
    branch_data.to_sql("branches", db_engine, if_exists="append", index=False)
    user_data.to_sql("users", db_engine, if_exists="append", index=False)
    customer_data.to_sql("customer_sales", db_engine, if_exists="append", index=False)
    payment_data.to_sql("payment_splits", db_engine, if_exists="append", index=False)

# -----------------------------------------------------------
# FIX EXISTING DATA
# -----------------------------------------------------------
def update_existing_data():
    with db_engine.begin() as conn:
        conn.execute(text("""
        UPDATE customer_sales cs
        LEFT JOIN (
            SELECT sale_id, SUM(amount_paid) AS total_paid
            FROM payment_splits
            GROUP BY sale_id
        ) p ON cs.sale_id = p.sale_id
        SET 
            cs.received_amount = IFNULL(p.total_paid, 0),
            cs.pending_amount  = cs.gross_sales - IFNULL(p.total_paid, 0),
            cs.status = CASE 
                            WHEN cs.gross_sales - IFNULL(p.total_paid,0) = 0 THEN 'Close'
                            ELSE 'Open'
                        END;
        """))

# -----------------------------------------------------------
# RUN ONCE (IMPORTANT)
# -----------------------------------------------------------
if not st.session_state.get("db_initialized"):

    Dataset_SetUp()
    create_triggers()
    insert_data()
    update_existing_data()

    st.session_state["db_initialized"] = True

# -----------------------------------------------------------
# UI
# -----------------------------------------------------------
st.title("💼 Client Query Management System")
st.success("✅ Database Ready with Triggers & Auto Calculation")



def analysis():
    if "analysis_page" not in st.session_state:
        st.session_state.analysis_page = "home"

    topic = st.selectbox("Analysis",
                         ["Select Analysis","Basic Queries",
                          "Aggregation Queries",
                          "Join-Based Queries",
                          "Financial Tracking Queries"])
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


# --------------------------------------------------------------------  Basic Queries ----------------------------------------------------------------------------------
    elif st.session_state.analysis_page == "Basic Queries":
        st.header("📊 Basic Queries")
        topic1 = st.selectbox("Analysis",
                             ["Select Query",
                              "Retrieve all records from the customer_sales table",
                              "Retrieve all records from the branches table",
                              "Retrieve all records from the payment_splits table",
                              "Display all sales with status = 'Open'",
                              "Retrieve all sales belonging to the Chennai branch"])
        
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
        else:
                query = """select c.gross_sales,c.received_amount,c.pending_amount,b.branch_name  from customer_sales as c
                   inner join branches as b on c.branch_id = b.branch_id where branch_name = 'Chennai';"""
                df = pd.read_sql(query,db_engine)
                st.dataframe(df)
        if st.button("⬅ Back"):
            st.session_state.analysis_page = "home"
            st.rerun()     

# -----------------------------------------------------------------------  Aggregation Queries ---------------------------------------------------------------------
    elif st.session_state.analysis_page == "Aggregation Queries":
        st.subheader("📈 Aggregation Queries")

        topic2 = st.selectbox("Aggregation Queries",                           
                             ["Select Query",
                              "Calculate the total gross sales across all branches",
                              "Calculate the total received amount across all sales",
                              "Calculate the total pending amount across all sales",
                              "Count the total number of sales per branch" ,
                              "Find the average gross sales amount"])
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
        else:
            query = """select avg(gross_sales) as Total_Sales from customer_sales;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)
        
        if st.button("⬅ Back"):
            st.session_state.analysis_page = "home"
            st.rerun()
    
# ------------------------------------------------------------------------ Join-Based Queries ------------------------------------------------------------------------
    elif st.session_state.analysis_page == "Join-Based Queries":
        st.subheader("🔗 Join-Based Queries")

        topic3 = st.selectbox("Join-Based Queries",
                             ["Select Query",
                              "Retrieve sales details along with the branch name",
                              "Retrieve sales details along with total payment received (using payment_splits)",
                              "Show branch-wise total gross sales (using JOIN & GROUP BY)",
                              "Display sales along with payment method used",
                              "Retrieve sales along with branch admin name"])
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
        else:   
            query = """select c.product_name,c.gross_sales,c.received_amount,c.pending_amount,b.branch_name ,b.branch_admin_name 
            from customer_sales as c
            inner join branches as b on c.branch_id = b.branch_id;"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)

        if st.button("⬅ Back"):
            st.session_state.analysis_page = "home"
            st.rerun()
# --------------------------------------------------- Financial Tracking Queries -------------------------------------------------------------------------------------
    elif st.session_state.analysis_page == "Financial Tracking Queries":
        st.subheader("💰 Financial Queries")

        topic4 = st.selectbox("Financial Tracking Queries",
                             ["Select Query",
                              "Find sales where the pending amount is greater than 5000",
                              "Retrieve top 3 highest gross sales",
                              "Find the branch with highest total gross sales",
                              "Retrieve monthly sales summary (group by month & year)",
                              "Calculate payment method-wise total collection (Cash / UPI / Card)"])
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
        else: 
            query = """select sum(c.gross_sales),p.payment_method
            from customer_sales as c
            inner join payment_splits as p on c.sale_id = p.sale_id  group by payment_method"""
            df = pd.read_sql(query,db_engine)
            st.dataframe(df)
        
        if st.button("⬅ Back"):
            st.session_state.analysis_page = "home"
            st.rerun()

