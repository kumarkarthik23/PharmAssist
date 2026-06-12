# 💊 PharmAssist — AI-Powered Pharmacy Assistant

A smart pharmacy management app that reads handwritten prescriptions using Google Gemini Vision, checks drug availability, processes sales, and manages inventory — all from a clean Streamlit interface.

---

## 🚀 Features

- 📸 **Prescription OCR** — Upload a photo of any handwritten prescription; Gemini 2.5 Flash extracts all drugs, frequency, and duration automatically
- ✏️ **Human-in-the-loop correction** — Review and fix extracted data before any database write
- 📦 **Stock availability check** — Instantly checks if sufficient stock exists for every drug on the prescription
- 💳 **Multi-drug sale processing** — Select individual drugs to sell via checkboxes; stock deducted atomically
- 🏪 **Live inventory** — Real-time view of all drugs, stock levels, expiry dates, and prices
- 🧾 **Sales log** — Full history of every transaction

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| AI / Vision | Google Gemini 2.5 Flash (google-genai SDK) |
| UI | Streamlit |
| Database | SQLite (built-in Python) |
| Config | python-dotenv |
| Language | Python 3.11 |

No LangChain. No LangGraph. No unnecessary frameworks.

---

## 📁 Project Structure

```
PharmAssist/
├── app.py              # Streamlit UI — all pages and interactions
├── rag_agent.py        # Gemini Vision — prescription extraction
├── db_utils.py         # SQLite — all database operations
├── pharmacy.db         # SQLite database (auto-created on first run)
├── requirements.txt    # 4 dependencies only
├── .env                # API key (not committed)
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/PharmAssist.git
cd PharmAssist
```

### 2. Create virtual environment
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your Gemini API key
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_api_key_here
```
Get a free key (no credit card) at: https://aistudio.google.com/apikey

### 5. Run the app
```bash
streamlit run app.py
```
Open http://localhost:8501 in your browser.

---

## 🔄 How It Works

```
Upload prescription image
        ↓
Gemini 2.5 Flash extracts all drugs
        ↓
Pharmacist reviews & corrects extracted data
        ↓
Stock availability checked for each drug
        ↓
Pharmacist selects drugs to sell
        ↓
Stock deducted + sale logged to DB
```

---

## 🗄️ Database Schema

**drugs** table
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| name | TEXT | Generic drug name |
| brand | TEXT | Brand name |
| quantity | INTEGER | Current stock |
| expiry_date | TEXT | Expiry date (YYYY-MM-DD) |
| price_per_unit | REAL | Price per unit |

**sales** table
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| drug_id | INTEGER | Foreign key → drugs |
| quantity_sold | INTEGER | Units sold |
| sale_date | TEXT | Date of sale |

---

## 🗺️ Roadmap

- [x] Multi-drug prescription extraction
- [x] Human-in-the-loop correction UI
- [x] Multi-drug sale with checkboxes
- [ ] Drug expiry alerts
- [ ] Low stock warnings
- [ ] Sales analytics dashboard
- [ ] Restock functionality
- [ ] Docker + Cloud deployment

---

## 📄 License

MIT License — free to use, modify, and distribute.
