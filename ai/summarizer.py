import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import warnings
warnings.filterwarnings("ignore")

import requests

try:
    import pymupdf as fitz  # PyMuPDF 1.24+
except ImportError:
    import fitz  # older PyMuPDF

from google import genai
from google.genai import types

from config import GEMINI_API_KEY


# ─── Settings ────────────────────────────────────────────
MODEL = "gemini-2.5-flash"        # bump to a newer flash model here when desired
TEXT_THRESHOLD = 200              # chars of extracted text below which we treat the PDF as scanned
MAX_PDF_BYTES = 18 * 1024 * 1024  # inline-data guard (~18MB); larger PDFs are skipped
AI_RETRIES = 3                    # attempts on transient Gemini errors (overload / rate limit)
AI_RETRY_DELAYS = [5, 15]         # seconds to wait between attempts

PROMPT = (
    "You are summarizing an official ESIC (Employees' State Insurance Corporation, India) circular. "
    "Write a clear, factual summary that captures the key points, who it affects, and any action or "
    "deadline. Keep each summary to 2-4 short sentences. "
    'Return ONLY a JSON object with exactly two keys: "en" (the summary in English) and '
    '"hi" (the same summary in Hindi).'
)

_client = None


def _get_client():
    """Lazily build the Gemini client. Returns None if no API key is configured."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            return None
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _download_pdf(url):
    resp = requests.get(url, timeout=30, verify=False, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })
    resp.raise_for_status()
    return resp.content


def _extract_text(pdf_bytes):
    text = ""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()


def _generate(client, contents):
    """Call Gemini, retrying on transient overload / rate-limit errors."""
    last_err = None
    for attempt in range(AI_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return response.text
        except Exception as e:
            last_err = e
            code = getattr(e, "code", None)
            msg = str(e)
            transient = code in (429, 500, 503) or any(
                s in msg for s in ("503", "429", "500", "UNAVAILABLE", "overloaded", "high demand")
            )
            if not transient or attempt == AI_RETRIES - 1:
                break
            wait = AI_RETRY_DELAYS[min(attempt, len(AI_RETRY_DELAYS) - 1)]
            print(f"  ⏳ Gemini busy ({code or 'transient'}) — retry {attempt + 1}/{AI_RETRIES - 1} in {wait}s")
            time.sleep(wait)
    raise last_err


def _summarize_text(client, text):
    return _generate(client, [PROMPT, "\n\nDocument text:\n" + text])


def _summarize_pdf(client, pdf_bytes):
    # Gemini OCRs scanned PDFs natively from the raw bytes
    return _generate(client, [
        PROMPT,
        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
    ])


def _parse(raw):
    """Parse the model's JSON reply into a summary dict, or None."""
    cleaned = raw.strip()
    # Safety net in case the model wraps JSON in a code fence
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(cleaned)
    en = (data.get("en") or "").strip()
    hi = (data.get("hi") or "").strip()
    if not en and not hi:
        return None
    return {"summary_en": en, "summary_hi": hi}


def generate_summary(circular):
    """
    Best-effort bilingual (EN + HI) summary of a circular's primary PDF.
    Returns {'summary_en': ..., 'summary_hi': ...} or None.
    Never raises — any failure just means no summary, and the caller posts without one.
    """
    client = _get_client()
    if client is None:
        print("  ⚠️ Summary: GEMINI_API_KEY not set — skipping")
        return None

    url = circular.get("circular_url")
    if not url:
        return None

    # 1. Download
    try:
        pdf_bytes = _download_pdf(url)
    except Exception as e:
        print(f"  ⚠️ Summary: PDF download failed: {e}")
        return None

    if not pdf_bytes.startswith(b"%PDF"):
        print("  ⚠️ Summary: target is not a PDF — skipping")
        return None

    if len(pdf_bytes) > MAX_PDF_BYTES:
        print("  ⚠️ Summary: PDF too large for inline summarization — skipping")
        return None

    # 2. Extract text to decide path (text PDF vs scanned)
    try:
        text = _extract_text(pdf_bytes)
    except Exception as e:
        print(f"  ⚠️ Summary: text extraction failed: {e}")
        text = ""

    # 3. Summarize
    try:
        if len(text) >= TEXT_THRESHOLD:
            raw = _summarize_text(client, text)
        else:
            raw = _summarize_pdf(client, pdf_bytes)  # OCR via Gemini
    except Exception as e:
        print(f"  ⚠️ Summary: Gemini call failed: {e}")
        return None

    # 4. Parse
    try:
        result = _parse(raw)
    except Exception as e:
        print(f"  ⚠️ Summary: could not parse model reply: {e}")
        return None

    if result:
        print(f"  📝 Summary generated ({'text' if len(text) >= TEXT_THRESHOLD else 'OCR'} path)")
    return result


if __name__ == "__main__":
    # Quick manual test — needs GEMINI_API_KEY set and a real PDF URL
    test = {"circular_url": "https://esic.gov.in/some-circular.pdf"}
    out = generate_summary(test)
    if out:
        print("\nEN:", out["summary_en"])
        print("\nHI:", out["summary_hi"])
    else:
        print("No summary produced.")