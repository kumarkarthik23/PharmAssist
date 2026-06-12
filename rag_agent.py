import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

EXTRACTION_PROMPT = """
You are an expert pharmacy assistant AI with deep knowledge of handwritten medical prescriptions.

Your task: Extract EVERY medicine from this prescription image. Missing even one drug is a critical error.

Return ONLY this JSON structure — no markdown, no explanation, no code fences:
{
  "medicines": [
    {"drug_name": "DrugA", "frequency": 2, "duration": 3},
    {"drug_name": "DrugB", "frequency": 1, "duration": 5}
  ]
}

════ STEP 1 — COUNT THE DRUGS FIRST ════
Before extracting, count how many numbered items (1. 2. 3. 4. etc.) appear in the prescription.
Your output MUST contain exactly that many entries. Never stop early.

════ STEP 2 — DRUG NAME ════
- Read the full drug name including suffix (OZ, MR, NR, Plus, etc.)
- Common misreads to watch for: "OFLAZEST OZ", "AZENAC MR", "ANDIAL", "ZOFER"
- If unsure, write your best guess — never leave it null if text is visible

════ STEP 3 — FREQUENCY (doses per day) ════
Prescriptions use morning-afternoon-night patterns. YOU MUST SUM ALL NUMBERS:
  "1-0-1"   → 1+0+1 = 2
  "1-1-1"   → 1+1+1 = 3
  "1-0-0"   → 1+0+0 = 1
  "2-1-1"   → 2+1+1 = 4
  "0-0-1"   → 0+0+1 = 1
  "1-1-0"   → 1+1+0 = 2
  dashes with numbers below the drug name = dosing pattern, always SUM them
  "twice daily"=2, "once daily"=1, "three times"=3, "QID"=4, "TID"=3, "BID"=2, "OD"=1
  "every 6h"=4, "every 8h"=3, "every 12h"=2
NEVER take just the first number. Always SUM the entire pattern.

════ STEP 4 — DURATION ════
- Look for "X days", "X weeks"(×7), "X months"(×30)
- A SINGLE DURATION written once with a brace/bracket APPLIES TO ALL DRUGS grouped under it
- If duration is written once on the side next to multiple drugs, apply it to ALL of them
- If truly not visible, use null

════ FINAL CHECK ════
Before returning, verify:
- Did you extract the same number of drugs you counted in Step 1?
- Did you SUM the dosing pattern for every drug?
- Did you apply shared duration to all grouped drugs?
"""

def extract_prescription(image_input) -> list[dict]:
    """
    Accepts a file path, raw bytes, or Streamlit UploadedFile.
    Returns a list of dicts: drug_name, frequency, duration, required_quantity
    """
    if hasattr(image_input, "read"):
        image_bytes = image_input.read()
        mime_type = getattr(image_input, "type", "image/jpeg")
    elif isinstance(image_input, (str, Path)):
        path = Path(image_input)
        image_bytes = path.read_bytes()
        suffix = path.suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".png": "image/png", ".webp": "image/webp"}
        mime_type = mime_map.get(suffix, "image/jpeg")
    elif isinstance(image_input, bytes):
        image_bytes = image_input
        mime_type = "image/jpeg"
    else:
        raise ValueError(f"Unsupported image input type: {type(image_input)}")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            types.Part.from_text(text=EXTRACTION_PROMPT),
        ]
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    parsed = json.loads(raw)
    medicines = parsed.get("medicines", [])

    results = []
    for med in medicines:
        med.setdefault("drug_name", None)
        med.setdefault("frequency", None)
        med.setdefault("duration", None)
        if med["frequency"] and med["duration"]:
            med["required_quantity"] = med["frequency"] * med["duration"]
        else:
            med["required_quantity"] = None
        results.append(med)

    return results
