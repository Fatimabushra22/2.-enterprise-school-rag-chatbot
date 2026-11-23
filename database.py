import sqlite3
import pandas as pd

DB_PATH = "school_enterprise.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS directors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, designation TEXT, department TEXT, email TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            employee_id TEXT PRIMARY KEY,
            name TEXT, subject TEXT, wing TEXT, qualification TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS classrooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grade INTEGER, section TEXT, class_teacher TEXT,
            boys_count INTEGER, girls_count INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS school_finance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fiscal_year TEXT, category TEXT, title TEXT,
            amount_inr REAL, department TEXT, notes TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_role TEXT, question TEXT, tool_used TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("SELECT COUNT(*) FROM directors")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO directors (name, designation, department, email) VALUES (?, ?, ?, ?)", [
            ("Dr. Rajesh Sharma", "Chairman & Managing Director", "Board of Governors", "chairman@greenwoodschool.edu.in"),
            ("Mrs. Sunita Verma", "Principal & Academic Director", "Academics", "principal@greenwoodschool.edu.in"),
            ("Mr. Vikramaditya Rao", "Director of Finance & Infrastructure", "Finance & Operations", "finance@greenwoodschool.edu.in"),
        ])

        cur.executemany("INSERT INTO teachers VALUES (?, ?, ?, ?, ?)", [
            ("TCH-101", "Anjali Deshmukh", "Physics", "Senior Secondary", "M.Sc., B.Ed."),
            ("TCH-102", "Rohan Kulkarni", "Mathematics", "Senior Secondary", "M.Sc. Math, B.Ed."),
            ("TCH-103", "Priya Nair", "English", "Secondary", "M.A. English, B.Ed."),
            ("TCH-104", "Amitabh Tiwari", "Computer Science & AI", "Senior Secondary", "M.Tech, B.Ed."),
            ("TCH-105", "Neha Joshi", "Science & EVS", "Middle", "B.Sc., B.Ed."),
            ("TCH-106", "Kavita Menon", "Primary All-Subjects", "Primary", "B.A., D.El.Ed."),
        ])

        cur.executemany("INSERT INTO classrooms (grade, section, class_teacher, boys_count, girls_count) VALUES (?, ?, ?, ?, ?)", [
            (1, "A", "Kavita Menon", 18, 17),
            (5, "A", "Kavita Menon", 20, 19),
            (8, "A", "Neha Joshi", 22, 20),
            (10, "A", "Priya Nair", 24, 21),
            (10, "B", "Rohan Kulkarni", 21, 22),
            (12, "Science", "Anjali Deshmukh", 25, 20),
            (12, "Commerce", "Amitabh Tiwari", 19, 23),
        ])

        cur.executemany("INSERT INTO school_finance (fiscal_year, category, title, amount_inr, department, notes) VALUES (?, ?, ?, ?, ?, ?)", [
            ("2026-27", "Revenue", "Annual Tuition & Composite Fee Collection", 24500000, "Accounts", "Collected across 312 enrolled students"),
            ("2026-27", "Revenue", "Transport & Smart Lab Fee Collection", 4200000, "Transport & IT", "GPS bus fleet & ERP portal fees"),
            ("2026-27", "Expense", "Faculty & Administrative Staff Salaries", 14800000, "HR & Payroll", "Annual payroll for 38 staff members"),
            ("2026-27", "Expense", "Campus Utilities, Maintenance & Bus Fuel", 3600000, "Operations", "Electricity, fuel, and campus upkeep"),
            ("2026-27", "Investment", "AI, Robotics & Computer Lab Upgrade", 2200000, "Academics & IT", "35 new workstations & robotics kits"),
            ("2026-27", "Investment", "100 kW Rooftop Solar Power Plant", 1850000, "Infrastructure", "Cuts electricity bill by 65%"),
            ("2026-27", "Investment", "2 New GPS Electric School Buses", 2800000, "Transport", "Expanded Zone B & Zone C routes"),
            ("2026-27", "Investment", "Interactive Smart Boards (15 Classrooms)", 1250000, "Academics", "Digital classroom upgrade"),
        ])

    conn.commit()
    conn.close()

def log_chat_query(user_role: str, question: str, tool_used: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO chat_audit_logs (user_role, question, tool_used) VALUES (?, ?, ?)",
        (user_role, question, tool_used)
    )
    conn.commit()
    conn.close()

def get_dashboard_data():
    conn = sqlite3.connect(DB_PATH)
    data = {
        "directors": pd.read_sql_query("SELECT name AS Name, designation AS Designation, department AS Department, email AS Email FROM directors", conn),
        "teachers": pd.read_sql_query("SELECT employee_id AS ID, name AS Name, subject AS Subject, wing AS Wing, qualification AS Qualification FROM teachers", conn),
        "classes": pd.read_sql_query("SELECT grade AS Grade, section AS Section, class_teacher AS 'Class Teacher', boys_count AS Boys, girls_count AS Girls, (boys_count + girls_count) AS 'Total Students' FROM classrooms ORDER BY grade, section", conn),
        "finance": pd.read_sql_query("SELECT fiscal_year AS Year, category AS Category, title AS Item, amount_inr AS 'Amount (₹)', department AS Department, notes AS Notes FROM school_finance", conn),
        "logs": pd.read_sql_query("SELECT user_role AS Role, question AS Question, tool_used AS 'Tool Used', created_at AS Timestamp FROM chat_audit_logs ORDER BY id DESC LIMIT 15", conn),
    }
    conn.close()
    return data

def query_enterprise_db(query_topic: str, user_role: str) -> str:
    """Enforces Role-Based Access Control (RBAC) for AI Agent queries."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    topic = query_topic.lower()

    if any(word in topic for word in ["finance", "profit", "invest", "revenue"]):
        if user_role != "Director":
            conn.close()
            return f"ACCESS DENIED (RBAC Policy): Financial profit and capital investment records are restricted ONLY to the 'Director' role. Current role: '{user_role}'."
        cur.execute("SELECT category, title, amount_inr, department FROM school_finance")
        rows = cur.fetchall()
        conn.close()
        rev = sum(r[2] for r in rows if r[0] == "Revenue")
        exp = sum(r[2] for r in rows if r[0] == "Expense")
        inv = sum(r[2] for r in rows if r[0] == "Investment")
        profit = rev - exp
        details = "; ".join([f"[{r[0]}] {r[1]}: ₹{r[2]:,.0f} ({r[3]})" for r in rows])
        return (
            f"School Financial Summary (FY 2026-27): Revenue = ₹{rev:,.0f}, Expenses = ₹{exp:,.0f}, "
            f"Net Operating Profit = ₹{profit:,.0f}, Capital Investments = ₹{inv:,.0f}, "
            f"Net Surplus After CapEx = ₹{profit - inv:,.0f}. Details: {details}"
        )

    if user_role == "Parent / Student":
        cur.execute("SELECT name, designation, department, email FROM directors")
        dirs = cur.fetchall()
        conn.close()
        return "School Leadership: " + "; ".join([f"{d[0]} ({d[1]}, {d[2]})" for d in dirs])

    cur.execute("SELECT grade, section, class_teacher, boys_count, girls_count FROM classrooms ORDER BY grade, section")
    classes = cur.fetchall()
    cur.execute("SELECT employee_id, name, subject, wing FROM teachers")
    teachers = cur.fetchall()
    conn.close()

    total_boys = sum(c[3] for c in classes)
    total_girls = sum(c[4] for c in classes)
    class_str = "; ".join([f"Grade {c[0]}-{c[1]}: {c[3]+c[4]} students ({c[3]} Boys, {c[4]} Girls, Teacher: {c[2]})" for c in classes])
    teacher_str = "; ".join([f"{t[1]} ({t[2]}, {t[3]})" for t in teachers])
    return f"Total Students: {total_boys + total_girls} ({total_boys} Boys, {total_girls} Girls). Classes: {class_str}. Faculty: {teacher_str}."
