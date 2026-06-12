import streamlit as st
from datetime import date, datetime
from PIL import Image
from db_utils import (
    init_db, get_all_drugs, check_availability,
    deduct_stock, get_sales_log,
    get_expiring_drugs, get_expired_drugs
)
from rag_agent import extract_prescription

init_db()

st.set_page_config(page_title="PharmAssist", page_icon="💊", layout="wide")
st.title("💊 PharmAssist — Prescription & Inventory Manager")

for key in ["medicines", "checked", "sale_messages"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ══════════════════════════════════════════════════════════════════════════════
# ALERTS BANNER — Expiry warnings at the very top
# ══════════════════════════════════════════════════════════════════════════════
expired      = get_expired_drugs()
expiring_30  = get_expiring_drugs(30)
expiring_90  = get_expiring_drugs(90)

# Only show banner if there's something to warn about
if expired or expiring_30:
    st.header("🚨 Alerts")

    if expired:
        with st.expander(f"🔴 {len(expired)} drug(s) EXPIRED — click to view", expanded=True):
            rows = [{"Drug": d["name"], "Brand": d["brand"],
                     "Stock": d["quantity"], "Expired On": d["expiry_date"]} for d in expired]
            st.dataframe(rows, use_container_width=True, hide_index=True)

    if expiring_30:
        with st.expander(f"🟠 {len(expiring_30)} drug(s) expiring within 30 days", expanded=True):
            rows = [{"Drug": d["name"], "Brand": d["brand"],
                     "Stock": d["quantity"], "Expiry Date": d["expiry_date"]} for d in expiring_30]
            st.dataframe(rows, use_container_width=True, hide_index=True)

    st.divider()

# Subtle 90-day notice in sidebar
with st.sidebar:
    st.markdown("### 📅 Expiry Watch")
    if expired:
        st.error(f"🔴 {len(expired)} expired")
    if expiring_30:
        st.warning(f"🟠 {len(expiring_30)} expiring in 30 days")

    # Drugs expiring in 31-90 days (exclude the 30-day ones)
    expiring_31_90 = [d for d in expiring_90 if d not in expiring_30]
    if expiring_31_90:
        st.info(f"🟡 {len(expiring_31_90)} expiring in 31–90 days")

    if not expired and not expiring_90:
        st.success("✅ All drugs within expiry")

    st.divider()
    st.caption(f"Today: {date.today().strftime('%d %b %Y')}")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Upload & Extract
# ══════════════════════════════════════════════════════════════════════════════
st.header("📋 Step 1: Upload Prescription")

uploaded_file = st.file_uploader(
    "Upload a photo of a handwritten prescription",
    type=["jpg", "jpeg", "png", "webp"]
)

if uploaded_file:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.image(Image.open(uploaded_file), caption="Uploaded Prescription", use_container_width=True)

    with col2:
        if st.button("🔍 Extract Prescription Details", type="primary"):
            with st.spinner("Analysing prescription with Gemini Vision..."):
                try:
                    uploaded_file.seek(0)
                    medicines = extract_prescription(uploaded_file)
                    st.session_state.medicines     = medicines
                    st.session_state.checked       = None
                    st.session_state.sale_messages = None
                except Exception as e:
                    st.error(f"Extraction failed: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Review & Correct
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.medicines is not None:
    st.header("✏️ Step 2: Review & Correct Extracted Data")
    st.caption("Gemini's best read of the prescription is shown below. Correct any mistakes before checking stock.")

    medicines = st.session_state.medicines

    col_add, col_remove = st.columns([1, 1])
    with col_add:
        if st.button("➕ Add a drug row"):
            medicines.append({"drug_name": "", "frequency": 1, "duration": 1, "required_quantity": 1})
            st.session_state.medicines = medicines
            st.rerun()
    with col_remove:
        if len(medicines) > 1:
            if st.button("➖ Remove last row"):
                medicines.pop()
                st.session_state.medicines = medicines
                st.rerun()

    updated = []
    for i, med in enumerate(medicines):
        st.markdown(f"**Drug {i+1}**")
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            name = st.text_input("Drug Name", value=med.get("drug_name") or "", key=f"name_{i}")
        with c2:
            freq = st.number_input("Freq/day", min_value=1, max_value=20,
                                   value=int(med.get("frequency") or 1), key=f"freq_{i}")
        with c3:
            dur = st.number_input("Duration (days)", min_value=1, max_value=365,
                                  value=int(med.get("duration") or 1), key=f"dur_{i}")
        qty = freq * dur
        st.caption(f"Required quantity: {freq} × {dur} = **{qty} units**")
        st.divider()
        updated.append({"drug_name": name, "frequency": freq, "duration": dur, "required_quantity": qty})

    if st.button("✅ Confirm & Check Stock Availability", type="primary"):
        empty = [i+1 for i, m in enumerate(updated) if not m["drug_name"].strip()]
        if empty:
            st.warning(f"Drug name is empty for row(s): {empty}. Please fill in all names.")
        else:
            checked = []
            for m in updated:
                name   = m["drug_name"].strip()
                qty    = m["required_quantity"]
                result = check_availability(name, qty)
                if not result["found"]:
                    checked.append({**m, "status": "❌ Not in inventory", "found": False, "sufficient": False, "drug": None})
                elif not result["sufficient"]:
                    drug = result["drug"]
                    checked.append({**m, "status": f"⚠️ Low stock ({drug['quantity']} available)", "found": True, "sufficient": False, "drug": drug})
                else:
                    drug = result["drug"]
                    # Warn if the drug is expiring soon even though stock is sufficient
                    expiry = drug.get("expiry_date")
                    warning = ""
                    if expiry:
                        days_left = (datetime.strptime(expiry, "%Y-%m-%d").date() - date.today()).days
                        if days_left < 0:
                            warning = " ⚠️ EXPIRED"
                        elif days_left <= 30:
                            warning = f" ⚠️ Expires in {days_left}d"
                        elif days_left <= 90:
                            warning = f" 🟡 Expires in {days_left}d"
                    checked.append({**m, "status": f"✅ In stock{warning}", "found": True, "sufficient": True, "drug": drug})
            st.session_state.checked       = checked
            st.session_state.sale_messages = None

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Availability Results
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.checked:
    st.header("🔎 Step 3: Availability Results")
    rows = []
    for m in st.session_state.checked:
        stock = m["drug"]["quantity"] if m["drug"] else "—"
        price = (f"${m['drug']['price_per_unit'] * m['required_quantity']:.2f}"
                 if m["drug"] and m.get("required_quantity") else "—")
        expiry = m["drug"]["expiry_date"] if m["drug"] else "—"
        rows.append({
            "Drug Name":    m.get("drug_name") or "—",
            "Required Qty": str(m.get("required_quantity") or "—"),
            "In Stock":     str(stock),
            "Expiry Date":  expiry,
            "Total Price":  price,
            "Status":       m["status"],
        })
    st.table(rows)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Sell
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.checked:
    sellable = [m for m in st.session_state.checked if m["sufficient"]]

    if sellable:
        st.header("💳 Step 4: Select Drugs to Sell")
        st.caption("Only drugs with sufficient stock are shown. Uncheck any you don't want to sell.")

        selected = []
        for i, m in enumerate(sellable):
            drug  = m["drug"]
            total = drug["price_per_unit"] * m["required_quantity"]
            label = (f"**{drug['name']}** ({drug['brand']}) — "
                     f"{m['required_quantity']} units × ${drug['price_per_unit']:.2f} = **${total:.2f}**")
            if st.checkbox(label, key=f"sell_{i}", value=True):
                selected.append(m)

        if selected:
            grand_total = sum(m["drug"]["price_per_unit"] * m["required_quantity"] for m in selected)
            st.info(f"🛒 {len(selected)} drug(s) selected — Grand Total: **${grand_total:.2f}**")

            if st.button("✅ Confirm Sale", type="primary"):
                messages = []
                for m in selected:
                    success = deduct_stock(m["drug"]["id"], m["required_quantity"])
                    if success:
                        messages.append(("success", f"✅ Sold {m['required_quantity']} units of {m['drug']['name']}"))
                    else:
                        messages.append(("error", f"❌ Failed: {m['drug']['name']} — stock may have changed"))
                st.session_state.sale_messages = messages
                st.session_state.medicines     = None
                st.session_state.checked       = None
    else:
        st.warning("⚠️ No drugs with sufficient stock available for sale.")

if st.session_state.sale_messages:
    st.header("🧾 Sale Results")
    for kind, msg in st.session_state.sale_messages:
        if kind == "success":
            st.success(msg)
        else:
            st.error(msg)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Live Inventory
# ══════════════════════════════════════════════════════════════════════════════
st.header("🏪 Live Inventory")

drugs = get_all_drugs()
if drugs:
    st.dataframe(
        drugs,
        column_config={
            "id":             st.column_config.NumberColumn("ID",             width="small"),
            "name":           st.column_config.TextColumn("Drug Name",        width="medium"),
            "brand":          st.column_config.TextColumn("Brand",            width="medium"),
            "quantity":       st.column_config.NumberColumn("Stock",          width="small"),
            "expiry_date":    st.column_config.TextColumn("Expiry Date",      width="medium"),
            "price_per_unit": st.column_config.NumberColumn("Price/Unit ($)", width="medium", format="$%.2f"),
        },
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No drugs in inventory.")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Sales Log
# ══════════════════════════════════════════════════════════════════════════════
st.header("🧾 Sales Log")

sales = get_sales_log()
if sales:
    st.dataframe(
        sales,
        column_config={
            "id":            st.column_config.NumberColumn("Sale ID",  width="small"),
            "name":          st.column_config.TextColumn("Drug",       width="medium"),
            "brand":         st.column_config.TextColumn("Brand",      width="medium"),
            "quantity_sold": st.column_config.NumberColumn("Qty Sold", width="small"),
            "sale_date":     st.column_config.TextColumn("Date",       width="medium"),
        },
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No sales recorded yet.")
