"""
Agent 1 — PDF Parser
Extracts mutual fund folio and transaction data from CAMS/KFintech PDF statements.

Two-tier strategy:
  Tier 1: Regex-based extraction (fast, deterministic)
  Tier 2: LLM extraction via Groq (handles any format, used only if Tier 1 yields 0 folios)
"""
import pdfplumber
import re
import json
from utils.llm import chat

# Folio number — handles both "Folio No: 12345678/01" and "Account No. 12345678"
FOLIO_RE = re.compile(r'(?:Folio No[.:\s]+|Account No[.:\s]+)([\w/\-]+)', re.IGNORECASE)

# Scheme name — up to the next newline or "ISIN" label
SCHEME_RE = re.compile(r'Scheme\s*[:\-]?\s*(.+?)(?:\n|ISIN)', re.IGNORECASE)

# ISIN — 2 uppercase letters + 10 alphanumeric chars
ISIN_RE = re.compile(r'ISIN\s*[:\-]?\s*([A-Z]{2}[A-Z0-9]{10})', re.IGNORECASE)

# Transaction row — handles both DD-Mon-YYYY and DD/MM/YYYY date formats
TXN_RE = re.compile(
    r'(\d{2}[-/]\w{3,}[-/]\d{4}|\d{2}/\d{2}/\d{4})'   # date
    r'[\s\t]+([\w\s/\(\)]+?)'                             # transaction type
    r'[\s\t]+([\d,]+\.\d{2,})'                            # amount
    r'[\s\t]+([\d\-]+\.\d{3,})'                           # units (can be negative for redemption)
    r'[\s\t]+([\d]+\.\d{2,})'                             # NAV
    r'[\s\t]+([\d]+\.\d{2,})',                            # balance units
    re.IGNORECASE,
)

PURCHASE_TYPES = {'purchase', 'sip', 'systematic', 'switch in', 'lump sum', 'new purchase', 'additional'}

def _is_purchase(txn_type: str) -> bool:
    t = txn_type.lower().strip()
    return any(p in t for p in PURCHASE_TYPES)

def extract_text(pdf_path: str) -> str:
    text = ''
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=3, y_tolerance=3) or ''
                text += page_text + '\n'
    except Exception as e:
        print(f'[Parser] pdfplumber error: {e}')
    return text

def parse_regex(text: str) -> list[dict]:
    folios = []
    split_pattern = re.compile(r'(?=Folio No|Account No\.?\s+\d)', re.IGNORECASE)
    sections = split_pattern.split(text)

    if len(sections) <= 1:
        sections = re.split(r'\n(?=-{10,})', text)

    for section in sections:
        if not section.strip(): continue
        folio_m  = FOLIO_RE.search(section)
        scheme_m = SCHEME_RE.search(section)
        isin_m   = ISIN_RE.search(section)
        txn_matches = TXN_RE.findall(section)

        if not txn_matches: continue

        purchases = []
        last_balance = 0.0
        for t in txn_matches:
            date_str, txn_type, amt_str, units_str, nav_str, bal_str = t
            try:
                amt = float(amt_str.replace(',', ''))
                units = float(units_str.replace(',', ''))
                nav = float(nav_str.replace(',', ''))
                bal = float(bal_str.replace(',', ''))
                last_balance = bal
                if _is_purchase(txn_type):
                    purchases.append({'date': date_str.strip(), 'type': txn_type.strip(), 'amount': amt, 'units': units, 'nav': nav, 'balance': bal})
            except ValueError: continue

        if not purchases: continue
        folios.append({
            'folio': folio_m.group(1).strip() if folio_m else 'UNKNOWN',
            'scheme_name': scheme_m.group(1).strip() if scheme_m else 'Unknown Scheme',
            'isin': isin_m.group(1).strip() if isin_m else '',
            'transactions': purchases,
            'total_units': last_balance,
            'avg_nav': round(sum(p['nav'] for p in purchases) / len(purchases), 4),
        })
    return folios

def parse_llm_fallback(text: str) -> list[dict]:
    snippet = text[:4000]
    prompt = f"Extract ALL mutual fund folio data from this text. Return ONLY JSON array.\nText:\n{snippet}"
    raw = chat([{'role': 'user', 'content': prompt}], temperature=0.1, max_tokens=2000)
    raw = re.sub(r'^```json\s*|^```\s*|```$', '', raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except:
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        return json.loads(m.group()) if m else []

def run_parser(state: dict) -> dict:
    pdf_path = state.get('pdf_path', '')
    text = extract_text(pdf_path)
    if not text.strip(): return {'folios': [], 'parse_errors': ['Empty PDF']}
    folios = parse_regex(text)
    errors = []
    if not folios:
        folios = parse_llm_fallback(text)
        errors.append('Used LLM fallback') if folios else errors.append('Failed parsing')
    return {'folios': folios, 'parse_errors': errors}