"""Text-based bank-statement PDF extraction with a review-before-save flow."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pypdf import PdfReader
from app.services import categorize

MAX_PDF_BYTES = 12 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_TRANSACTIONS = 1000
DATE_LINE = re.compile(r"^\d{1,2} [A-Z][a-z]{2} \d{4}$")
TIME_LINE = re.compile(r"^\d{1,2}:\d{2} (?:AM|PM)$", re.I)
MONEY = re.compile(r"₹\s*([\d,]+\.\d{2})")
GPAY_DATE_LINE = re.compile(r"^\d{1,2} [A-Z][a-z]{2}, \d{4}$")
GPAY_TIME_LINE = re.compile(r"^\d{1,2}:\d{2}\s*(?:AM|PM)$", re.I)
GPAY_AMOUNT = re.compile(r"₹\s*([\d,]+(?:\.\d{1,2})?)")

def _gpay_rows(pages: list[str], pdf_hash: str) -> list[dict]:
    """Parse Google Pay transaction statement exports (one date/time block per payment)."""
    rows = []
    row_number = 0
    for page_text in pages:
        lines = [" ".join(line.split()) for line in page_text.splitlines()]
        starts = [
            i for i in range(len(lines) - 1)
            if GPAY_DATE_LINE.fullmatch(lines[i]) and GPAY_TIME_LINE.fullmatch(lines[i + 1])
        ]
        for pos, start in enumerate(starts):
            end = starts[pos + 1] if pos + 1 < len(starts) else len(lines)
            block = lines[start:end]
            details = next((line for line in block[2:] if re.match(r"^(?:Paid to|Received from)\b", line, re.I)), "")
            direction = re.match(r"^(Paid to|Received from)\s+(.+)$", details, re.I)
            if not direction:
                continue
            amount_line = next((line for line in block if GPAY_AMOUNT.search(line)), "")
            amount_match = GPAY_AMOUNT.search(amount_line)
            if not amount_match:
                continue
            amount = Decimal(amount_match.group(1).replace(",", ""))
            if amount <= 0:
                continue
            try:
                date_value = datetime.strptime(block[0], "%d %b, %Y").date().isoformat()
            except ValueError:
                continue
            merchant = direction.group(2).strip()
            txn_match = re.search(r"UPI\s*Transaction\s*ID\s*:\s*([A-Za-z0-9_-]+)", " ".join(block), re.I)
            external_ref = txn_match.group(1) if txn_match else None
            source_ref = "id:" + external_ref if external_ref else hashlib.sha256(f"{pdf_hash}:{row_number}".encode()).hexdigest()
            prediction = categorize(merchant)
            if any(term in merchant.lower() for term in ("canteen", "foodworks")):
                prediction = {"category": "Food & Dining", "confidence": 0.90, "method": "merchant rule"}
            rows.append({
                "date": date_value,
                "amount": float(amount),
                "type": "income" if direction.group(1).lower() == "received from" else "expense",
                "category": prediction["category"],
                "confidence": prediction["confidence"],
                "merchant": merchant[:160],
                "description": "Google Pay statement entry",
                "payment_method": "UPI",
                "source_ref": source_ref,
                "external_ref": external_ref,
            })
            row_number += 1
    return rows

def _famx_rows(pages: list[str], pdf_hash: str) -> list[dict]:
    rows = []
    row_number = 0
    for page_text in pages:
        lines = [line.strip() for line in page_text.splitlines()]
        starts = [i for i in range(len(lines)-1) if DATE_LINE.fullmatch(lines[i]) and TIME_LINE.fullmatch(lines[i+1])]
        for pos, start in enumerate(starts):
            end = starts[pos+1] if pos+1 < len(starts) else len(lines)
            block = lines[start:end]
            detail = block[2] if len(block) > 2 else ""
            direction = detail[:3].lower()
            if direction not in {"to ", "fro"}:
                continue
            kind = "expense" if direction == "to " else "income"
            merchant = detail[3:].strip()
            txn_id = next((x.split(":", 1)[1].strip() for x in block if x.startswith("Txn ID:")), "")
            utr = next((x.split(":", 1)[1].strip() for x in block if x.startswith("UTR:")), "")
            amount_pairs = [MONEY.findall(x) for x in block if len(MONEY.findall(x)) >= 2]
            if not amount_pairs:
                continue
            amount = Decimal(amount_pairs[-1][0].replace(",", ""))
            if amount <= 0:
                continue
            date_value = datetime.strptime(block[0], "%d %b %Y").date().isoformat()
            external_ref = txn_id or utr
            source_ref = "id:" + external_ref if external_ref else hashlib.sha256(f"{pdf_hash}:{row_number}".encode()).hexdigest()
            prediction = categorize(merchant)
            if "canteen" in merchant.lower() or "foodworks" in merchant.lower():
                prediction = {"category": "Food & Dining", "confidence": 0.90, "method": "merchant rule"}
            rows.append({
                "date": date_value, "amount": float(amount), "type": kind,
                "category": prediction["category"], "confidence": prediction["confidence"],
                "merchant": merchant[:160], "description": "UPI statement entry",
                "payment_method": "UPI", "source_ref": source_ref,
                "external_ref": external_ref or None,
            })
            row_number += 1
    return rows

def _generic_rows(pages: list[str], pdf_hash: str) -> list[dict]:
    """Conservative fallback for text rows that state debit/credit direction."""
    rows = []
    date_re = re.compile(r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})(?:\s+|$)")
    direction_re = re.compile(r"\b(credit|credited|deposit|received|cr|debit|debited|withdrawal|withdrawn|paid|dr)\b", re.I)
    amount_re = re.compile(r"(?:₹|INR\s*|Rs\.?\s*)?([\d,]+\.\d{2})")
    row_number = 0
    for page_text in pages:
        lines = [" ".join(line.split()) for line in page_text.splitlines()]
        starts = [i for i, line in enumerate(lines) if date_re.match(line)]
        for pos, start in enumerate(starts):
            end = starts[pos+1] if pos+1 < len(starts) else len(lines)
            block = lines[start:end]
            match = date_re.match(block[0])
            if not match: continue
            body = " ".join([block[0][match.end():], *block[1:]]).strip()
            direction = direction_re.search(body)
            if not direction:
                continue
            token = direction.group(1).lower()
            kind = "income" if token in {"credit", "credited", "deposit", "received", "cr"} else "expense"
            values = [Decimal(x.replace(",", "")) for x in amount_re.findall(body)]
            if not values:
                continue
            date_text = match.group(1)
            date_value = None
            for fmt in ("%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%m/%d/%y", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d"):
                try:
                    date_value = datetime.strptime(date_text, fmt).date().isoformat()
                    break
                except ValueError:
                    pass
            if not date_value:
                continue
            amount = values[0]
            if amount <= 0:
                continue
            merchant = direction_re.sub("", body)
            merchant = amount_re.sub("", merchant).strip(" -|:") or "Bank transaction"
            prediction = categorize(merchant + " " + body)
            source_ref = hashlib.sha256(f"{pdf_hash}:{row_number}".encode()).hexdigest()
            rows.append({
                "date": date_value, "amount": float(amount), "type": kind,
                "category": prediction["category"], "confidence": prediction["confidence"],
                "merchant": merchant[:160], "description": "Imported from bank statement PDF",
                "payment_method": "Bank transfer", "source_ref": source_ref,
                "external_ref": None,
            })
            row_number += 1
    return rows

def parse_statement_pdf(content: bytes) -> dict:
    if len(content) > MAX_PDF_BYTES:
        raise ValueError("PDF is larger than the 12 MB upload limit.")
    if not content.startswith(b"%PDF-"):
        raise ValueError("Please choose a valid PDF bank statement.")
    try:
        reader = PdfReader(BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise ValueError("This PDF is password-protected. Export an unlocked copy to import it.")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ValueError("PDF has more than 100 pages; split it into smaller statements.")
        pages = [(page.extract_text() or "") for page in reader.pages]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("We couldn't read this PDF. Try exporting a text-based bank statement.") from exc
    if not any(text.strip() for text in pages):
        raise ValueError("This PDF has no selectable text. Scanned statements need OCR and are not supported yet.")
    pdf_hash = hashlib.sha256(content).hexdigest()
    rows = _gpay_rows(pages, pdf_hash)
    if not rows:
        rows = _famx_rows(pages, pdf_hash)
    if not rows:
        rows = _generic_rows(pages, pdf_hash)
    if not rows:
        raise ValueError("No supported transactions found. Use a text-based statement with clear dates and debit/credit labels.")
    if len(rows) > MAX_TRANSACTIONS:
        raise ValueError("PDF contains more than 1,000 transactions; split it into smaller statements.")
    rows.sort(key=lambda x: (x["date"], x["merchant"]))
    income = sum((Decimal(str(row["amount"])) for row in rows if row["type"] == "income"), Decimal(0))
    expenses = sum((Decimal(str(row["amount"])) for row in rows if row["type"] == "expense"), Decimal(0))
    return {
        "transactions": rows,
        "summary": {
            "count": len(rows), "income": float(income), "expenses": float(expenses),
            "from_date": rows[0]["date"], "to_date": rows[-1]["date"],
        },
    }
