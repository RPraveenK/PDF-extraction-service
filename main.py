from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import base64, io, re
from pypdf import PdfReader

app = FastAPI()
API_KEY = "change-me-to-a-long-random-string"

class Req(BaseModel):
    filename: str = ""
    content: str   # base64 PDF

def grab(pattern, text):
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None

def clean_team(raw):
    if not raw:
        return None
    t = re.sub(r"\(.*?\)", "", raw)          # drop (MEXICO)
    t = t.split(" - ")[-1].strip()            # drop leading 'PWT - '
    t = re.sub(r"\s+", " ", t).strip()
    if re.fullmatch(r"U[A-Z]O", t):           # UPO/UFO/UQO/UXO -> UP0/UF0/...
        t = t[:2] + "0"                       # (UGX untouched, JATCO untouched)
    return t

@app.post("/extract")
def extract(req: Req, x_api_key: str = Header(default="")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="bad key")
    pdf = PdfReader(io.BytesIO(base64.b64decode(req.content)))
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    flat = re.sub(r"\s+", " ", text)          # collapse line-wraps to one line

    # description: 'PRC-ENG <team part> <MON><YY>'
    m = re.search(r"PRC-ENG\s+(.+?)\s+([A-Z]{3}\d{2})", flat)
    team_raw = m.group(1) if m else None      # 'PWT - UPO' / 'JATCO CASTING' / 'NMEX (MEXICO)'
    month_raw = m.group(2) if m else None     # 'MAR23'

    return {
        "filename":    req.filename,
        "invoiceNo":   grab(r"Invoice No\.?\s*:\s*([A-Z0-9]+)", flat),
        "invoiceDate": grab(r"Invoice Date\s*:\s*(\d{4}/\d{2}/\d{2})", flat),
        "grandTotal":  grab(r"Grand total:\s*([\d,]+\.\d{2})", flat),
        "team":        clean_team(team_raw),
        "month":       month_raw.capitalize() if month_raw else None,  # MAR23 -> Mar23
    }
