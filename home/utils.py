import re
import uuid
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse

import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

# ─── Tesseract path (Windows) ─────────────────────────────────────────────────
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ─── OCR Extraction ────────────────────────────────────────────────────────────

def extract_text_from_file(file):
    """Extract text from image or PDF file using Tesseract OCR."""
    text = ""
    try:
        if file.name.lower().endswith(".pdf"):
            file.seek(0)
            images = convert_from_bytes(file.read(), dpi=200)
            for img in images:
                text += pytesseract.image_to_string(img, lang='eng+hin') + "\n"
        else:
            image = Image.open(file)
            # Try with multiple languages for better Indian document support
            text = pytesseract.image_to_string(image, lang='eng+hin')
    except Exception as e:
        text = f"OCR_ERROR: {str(e)}"
    return text


def extract_entities(text):
    """
    Extract structured entities from OCR text.
    Returns a dict with keys matching form field names.
    """
    data = {}

    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', text).strip()

    # ── Full Name ─────────────────────────────────────────────────────────────
    name_patterns = [
        r"(?:Full\s*Name|Name|नाम)[:\s\-]+([A-Za-z][A-Za-z\s]{2,40})",
        r"(?:Applicant|Holder)[:\s]+([A-Z][A-Za-z\s]{2,40})",
        r"^([A-Z][A-Z\s]{4,30})$",  # ALL-CAPS name line
    ]
    for pat in name_patterns:
        m = re.search(pat, cleaned, re.I | re.M)
        if m:
            name = m.group(1).strip()
            if len(name) > 3 and 'GOVERNMENT' not in name.upper():
                data["full_name"] = name
                break

    # ── Father / Husband Name ────────────────────────────────────────────────
    father_patterns = [
        r"(?:Father['\u2019]?s?\s*Name|S/O|Son of|D/O|Daughter of|W/O|पिता)[:\s\-]+([A-Za-z\s]{3,40})",
    ]
    for pat in father_patterns:
        m = re.search(pat, cleaned, re.I)
        if m:
            data["father_name"] = m.group(1).strip()
            break

    # ── Date of Birth ─────────────────────────────────────────────────────────
    dob_patterns = [
        r"(?:DOB|Date\s*of\s*Birth|D\.O\.B\.?|जन्म\s*तिथि)[:\s\-]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
        r"(?:DOB|Date\s*of\s*Birth)[:\s\-]+(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})",
        r"\b(\d{2}[\/\-]\d{2}[\/\-]\d{4})\b",
    ]
    for pat in dob_patterns:
        m = re.search(pat, cleaned, re.I)
        if m:
            raw_dob = m.group(1).strip()
            data["dob"] = _normalize_date(raw_dob)
            break

    # ── Aadhaar Number ────────────────────────────────────────────────────────
    aadhaar_m = re.search(r"\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b", cleaned)
    if aadhaar_m:
        data["aadhaar"] = aadhaar_m.group(1).replace(' ', '').replace('-', '')
        # Format as XXXX XXXX XXXX
        raw = data["aadhaar"]
        if len(raw) == 12:
            data["aadhaar"] = f"{raw[:4]} {raw[4:8]} {raw[8:]}"

    # ── PAN Number ────────────────────────────────────────────────────────────
    pan_m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b", cleaned)
    if pan_m:
        data["pan_number"] = pan_m.group(1)

    # ── Voter ID ─────────────────────────────────────────────────────────────
    voter_m = re.search(r"\b([A-Z]{3}[0-9]{7})\b", cleaned)
    if voter_m:
        data["voter_id"] = voter_m.group(1)

    # ── Gender ────────────────────────────────────────────────────────────────
    gender_m = re.search(r"\b(Male|Female|Other|पुरुष|महिला)\b", cleaned, re.I)
    if gender_m:
        g = gender_m.group(1).strip()
        if g.lower() in ('पुरुष',):
            g = 'Male'
        elif g.lower() in ('महिला',):
            g = 'Female'
        data["gender"] = g.capitalize()

    # ── Mobile Number ─────────────────────────────────────────────────────────
    mobile_m = re.search(r"(?:Mobile|Phone|Mob|Ph)[.:\s\-]+(\+?91[\s\-]?)?(\d{10})", cleaned, re.I)
    if mobile_m:
        data["mobile"] = mobile_m.group(2)
    else:
        # Fallback: any 10-digit number starting with 6-9
        mobile_fallback = re.search(r"\b([6-9]\d{9})\b", cleaned)
        if mobile_fallback:
            data["mobile"] = mobile_fallback.group(1)

    # ── Address ───────────────────────────────────────────────────────────────
    addr_m = re.search(
        r"Address[:\s\-]+(.+?)(?=\s*(?:District|State|Pin|Gender|Mobile|Email|DOB|$))",
        cleaned, re.I | re.S
    )
    if addr_m:
        data["address"] = re.sub(r'\s+', ' ', addr_m.group(1)).strip()

    # ── District ─────────────────────────────────────────────────────────────
    district_m = re.search(r"District[:\s\-]+([A-Za-z\s]{2,30})", cleaned, re.I)
    if district_m:
        data["district"] = district_m.group(1).strip().rstrip(',')

    # ── State ─────────────────────────────────────────────────────────────────
    state_m = re.search(r"State[:\s\-]+([A-Za-z\s]{2,30})", cleaned, re.I)
    if state_m:
        data["state"] = state_m.group(1).strip().rstrip(',')

    # ── PIN Code ─────────────────────────────────────────────────────────────
    pin_m = re.search(r"\b(PIN|Pincode|Pin Code)[:\s]*(\d{6})\b", cleaned, re.I)
    if not pin_m:
        pin_m = re.search(r"\b(\d{6})\b", cleaned)
    if pin_m:
        pin_val = pin_m.group(2) if pin_m.lastindex and pin_m.lastindex >= 2 else pin_m.group(1)
        if re.match(r'[1-9]\d{5}', pin_val):
            data["pin_code"] = pin_val

    # ── Years of Residence ────────────────────────────────────────────────────
    res_m = re.search(r"(?:Years? of Residence|Residence Duration|Since)[:\s\-]+(\d+)", cleaned, re.I)
    if res_m:
        data["residence_years"] = res_m.group(1)

    # ── Annual Income ────────────────────────────────────────────────────────
    income_m = re.search(r"(?:Annual Income|Total Income|Income)[:\s\-]+(?:Rs\.?|₹)?\s*([\d,]+)", cleaned, re.I)
    if income_m:
        data["annual_income"] = income_m.group(1).replace(',', '')

    # ── Purpose ──────────────────────────────────────────────────────────────
    purpose_m = re.search(
        r"Purpose[:\s\-]+(Education|Government Job|Scholarship|Ration Card|Loan|Medical|Other)",
        cleaned, re.I
    )
    if purpose_m:
        data["purpose"] = purpose_m.group(1)

    return data


def _normalize_date(raw: str) -> str:
    """Convert various date formats to YYYY-MM-DD for Django DateField."""
    raw = raw.strip()
    # Try DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    m = re.match(r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})$", raw)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    # Try YYYY-MM-DD
    m2 = re.match(r"(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})$", raw)
    if m2:
        return f"{m2.group(1)}-{m2.group(2).zfill(2)}-{m2.group(3).zfill(2)}"
    return raw


# ─── PDF Generation ────────────────────────────────────────────────────────────

def _draw_certificate_border(c, width, height):
    """Draw an official-looking double border on the PDF page."""
    margin = 1.2 * cm
    c.setStrokeColor(colors.HexColor("#1e3a5f"))
    c.setLineWidth(3)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)
    c.setLineWidth(1)
    inner = margin + 6
    c.rect(inner, inner, width - 2 * inner, height - 2 * inner)


def _draw_header(c, width, height, title_text):
    """Draw the government header section."""
    # Orange-blue gradient strip (simulate with rectangles)
    c.setFillColor(colors.HexColor("#FF9933"))
    c.rect(1.2 * cm, height - 3.2 * cm, (width - 2.4 * cm) / 3, 0.4 * cm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#FFFFFF"))
    c.rect(1.2 * cm + (width - 2.4 * cm) / 3, height - 3.2 * cm, (width - 2.4 * cm) / 3, 0.4 * cm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#138808"))
    c.rect(1.2 * cm + 2 * (width - 2.4 * cm) / 3, height - 3.2 * cm, (width - 2.4 * cm) / 3, 0.4 * cm, fill=1, stroke=0)

    # Title
    c.setFillColor(colors.HexColor("#1e3a5f"))
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2, height - 2.2 * cm, "GOVERNMENT OF INDIA — CITIZEN SERVICES")
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 3.8 * cm, title_text)
    c.setLineWidth(1.5)
    c.setStrokeColor(colors.HexColor("#1e3a5f"))
    c.line(2 * cm, height - 4.1 * cm, width - 2 * cm, height - 4.1 * cm)


def _draw_field(c, label, value, x, y, label_width=5 * cm):
    """Draw a label: value pair."""
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor("#374151"))
    c.drawString(x, y, label + ":")
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawString(x + label_width, y, str(value) if value else "—")


def generate_domicile_pdf(application):
    """Generate a styled Domicile Certificate PDF."""
    response = HttpResponse(content_type='application/pdf')
    cert_id = str(application.certificate_no or application.id)
    response['Content-Disposition'] = f'attachment; filename="domicile_certificate_{cert_id}.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    _draw_certificate_border(c, width, height)
    _draw_header(c, width, height, "DOMICILE CERTIFICATE")

    # Certificate number & date
    from datetime import date
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawString(2 * cm, height - 4.7 * cm, f"Certificate No: {application.certificate_no}")
    c.drawRightString(width - 2 * cm, height - 4.7 * cm, f"Date: {date.today().strftime('%d %B %Y')}")

    # Body text
    lx = 2.2 * cm
    lw = 5.5 * cm
    y = height - 5.8 * cm
    step = 0.75 * cm

    fields = [
        ("Applicant Name", application.full_name),
        ("Father's Name", application.father_name or "—"),
        ("Gender", application.gender),
        ("Date of Birth", str(application.dob)),
        ("Mobile", application.mobile),
        ("Aadhaar No.", application.aadhaar or "—"),
        ("PAN No.", application.pan_number or "—"),
        ("Permanent Address", application.address),
        ("District", application.district),
        ("State", application.state),
        ("Years of Residence", str(application.residence_years)),
        ("Purpose", application.purpose),
    ]

    for label, value in fields:
        _draw_field(c, label, value, lx, y, lw)
        y -= step

    # Footer declaration
    y -= 0.5 * cm
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#374151"))
    c.drawCentredString(
        width / 2, y,
        "Certified that the above-mentioned person is a permanent resident as per records."
    )

    y -= 2.5 * cm
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 3 * cm, y, "Authorised Signatory")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 3 * cm, y - 0.5 * cm, "Revenue Department, Government of India")

    c.showPage()
    c.save()
    return response


def generate_income_pdf(application):
    """Generate a styled Income Certificate PDF."""
    response = HttpResponse(content_type='application/pdf')
    cert_id = str(application.certificate_no or application.id)
    response['Content-Disposition'] = f'attachment; filename="income_certificate_{cert_id}.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    _draw_certificate_border(c, width, height)
    _draw_header(c, width, height, "INCOME CERTIFICATE")

    from datetime import date
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawString(2 * cm, height - 4.7 * cm, f"Certificate No: {application.certificate_no}")
    c.drawRightString(width - 2 * cm, height - 4.7 * cm, f"Date: {date.today().strftime('%d %B %Y')}")

    lx = 2.2 * cm
    lw = 5.5 * cm
    y = height - 5.8 * cm
    step = 0.75 * cm

    fields = [
        ("Applicant Name", application.full_name),
        ("Father's Name", application.father_name or "—"),
        ("Gender", application.gender),
        ("Date of Birth", str(application.dob)),
        ("Mobile", application.mobile),
        ("Aadhaar No.", application.aadhaar or "—"),
        ("PAN No.", application.pan_number or "—"),
        ("Permanent Address", application.address),
        ("District", application.district),
        ("State", application.state),
        ("Annual Income", f"₹ {application.annual_income}"),
        ("Source of Income", application.income_source),
        ("Purpose", application.purpose),
    ]

    for label, value in fields:
        _draw_field(c, label, value, lx, y, lw)
        y -= step

    y -= 0.5 * cm
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#374151"))
    c.drawCentredString(
        width / 2, y,
        "Certified that the annual income of the above person is as stated above."
    )

    y -= 2.5 * cm
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 3 * cm, y, "Authorised Signatory")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 3 * cm, y - 0.5 * cm, "Revenue Department, Government of India")

    c.showPage()
    c.save()
    return response