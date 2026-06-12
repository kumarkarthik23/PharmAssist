import sqlite3
from datetime import date

DB_PATH = "pharmacy.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS drugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT,
            quantity INTEGER NOT NULL DEFAULT 0,
            expiry_date TEXT,
            price_per_unit REAL NOT NULL DEFAULT 0.0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_id INTEGER NOT NULL,
            quantity_sold INTEGER NOT NULL,
            sale_date TEXT NOT NULL,
            FOREIGN KEY (drug_id) REFERENCES drugs(id)
        )
    """)

    # Seed sample data only if table is empty
    cur.execute("SELECT COUNT(*) FROM drugs")
    if cur.fetchone()[0] == 0:
        sample_drugs = [
            ("Amoxicillin", "Amoxil",      120, "2026-12-01", 0.50),
            ("Ibuprofen",   "Advil",        85, "2027-03-15", 0.30),
            ("Metformin",   "Glucophage",   60, "2026-09-30", 0.45),
            ("Lisinopril",  "Zestril",      40, "2027-01-20", 0.75),
            ("Atorvastatin","Lipitor",      55, "2026-11-10", 1.20),
            ("Omeprazole",  "Prilosec",     90, "2027-05-01", 0.60),
            ("Azithromycin","Zithromax",    30, "2026-08-25", 1.10),
            ("Cetirizine",  "Zyrtec",      100, "2027-02-28", 0.25),
            ("Paracetamol", "Tylenol",     200, "2027-06-15", 0.20),
            ("Ciprofloxacin","Cipro",       25, "2026-10-05", 0.90),
        ]
        cur.executemany(
            "INSERT INTO drugs (name, brand, quantity, expiry_date, price_per_unit) VALUES (?,?,?,?,?)",
            sample_drugs
        )

    conn.commit()
    conn.close()

def get_all_drugs():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM drugs ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_drug_by_name(name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM drugs WHERE LOWER(name) = LOWER(?)", (name,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def check_availability(name: str, required_qty: int):
    drug = get_drug_by_name(name)
    if not drug:
        return {"found": False, "drug": None, "sufficient": False}
    return {
        "found": True,
        "drug": drug,
        "sufficient": drug["quantity"] >= required_qty
    }

def deduct_stock(drug_id: int, quantity_sold: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE drugs SET quantity = quantity - ? WHERE id = ? AND quantity >= ?",
        (quantity_sold, drug_id, quantity_sold)
    )
    updated = cur.rowcount
    if updated:
        cur.execute(
            "INSERT INTO sales (drug_id, quantity_sold, sale_date) VALUES (?, ?, ?)",
            (drug_id, quantity_sold, date.today().isoformat())
        )
    conn.commit()
    conn.close()
    return updated > 0

def get_sales_log():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id, d.name, d.brand, s.quantity_sold, s.sale_date
        FROM sales s
        JOIN drugs d ON s.drug_id = d.id
        ORDER BY s.sale_date DESC, s.id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]



def get_expiring_drugs(days_threshold: int = 90) -> list[dict]:
    """Returns drugs expiring within the next `days_threshold` days, sorted soonest first."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, brand, quantity, expiry_date, price_per_unit
        FROM drugs
        WHERE expiry_date IS NOT NULL
          AND date(expiry_date) <= date('now', ? || ' days')
          AND date(expiry_date) >= date('now')
        ORDER BY date(expiry_date) ASC
    """, (f"+{days_threshold}",))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_expired_drugs() -> list[dict]:
    """Returns drugs that have already passed their expiry date."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, brand, quantity, expiry_date, price_per_unit
        FROM drugs
        WHERE expiry_date IS NOT NULL
          AND date(expiry_date) < date('now')
        ORDER BY date(expiry_date) ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
