from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.http import HttpResponse
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import re


def generate_domicile_pdf(application):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="domicile_certificate.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height-80, "DOMICILE CERTIFICATE")

    c.setFont("Helvetica", 12)
    y = height - 150

    lines = [
        f"Certificate No: {application.certificate_no}",
        f"Name: {application.full_name}",
        f"Gender: {application.gender}",
        f"Date of Birth: {application.dob}",
        f"Address: {application.address}",
        f"District: {application.district}",
        f"State: {application.state}",
        f"Purpose: {application.purpose}",
    ]

    for line in lines:
        c.drawString(80, y, line)
        y -= 25

    c.drawString(80, y-30, "Issued by Government Authority")
    c.showPage()
    c.save()

    return response

# windows path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_text_from_file(file):
    text = ""

    if file.name.endswith(".pdf"):
        images = convert_from_bytes(file.read())
        for img in images:
            text += pytesseract.image_to_string(img)

    else:
        image = Image.open(file)
        text = pytesseract.image_to_string(image)

    return text


def extract_entities(text):
    data = {}

    # Normalize text
    text = re.sub(r'\s+', ' ', text).strip()

    # Full Name
    name_match = re.search(r"(?:Full\s*Name|Name)[:\s\-]+([A-Za-z ]{3,})", text, re.I)
    if name_match:
        data["full_name"] = name_match.group(1).strip()

    # DOB
    dob_match = re.search(r"(DOB|Date of Birth|D\.O\.B\.?)[:\s\-]+([\d]{1,2}[\-/\. ][\d]{1,2}[\-/\. ][\d]{4})", text, re.I)
    if dob_match:
        data["dob"] = dob_match.group(1)

    # Aadhaar
    aadhaar_match = re.search(r"\d{4}\s\d{4}\s\d{4}", text)
    if aadhaar_match:
        data["aadhaar"] = aadhaar_match.group()

    # Gender
    gender_match = re.search(r"Gender[:\s\-]+(Male|Female|Other)", text, re.I)
    if gender_match:
        data["gender"] = gender_match.group(1)

    # Mobile
    mobile_match = re.search(r"(?:Mobile|Phone)[:\s\-]+(\d{10})", text)
    if mobile_match:
        data["mobile"] = mobile_match.group(1)

    # Address
    address_match = re.search(r"Address[:\s\-]+(.+?)(?:District|State|Gender|Mobile|Email|$)", text, re.I)
    if address_match:
        data["address"] = address_match.group(1).strip()

    # District
    district_match = re.search(r"District[:\s\-]+([A-Za-z ]+)", text, re.I)
    if district_match:
        data["district"] = district_match.group(1).strip()

    # State
    state_match = re.search(r"State[:\s\-]+([A-Za-z ]+)", text, re.I)
    if state_match:
        data["state"] = state_match.group(1).strip()

    # Years of Residence
    residence_match = re.search(r"(?:Years of Residence|Residence Duration)[:\s\-]+(\d+)", text, re.I)
    if residence_match:
        data["residence_years"] = residence_match.group(1)

    # Purpose
    purpose_match = re.search(r"Purpose[:\s\-]+(Education|Government Job|Scholarship|Other)", text, re.I)
    if purpose_match:
        data["purpose"] = purpose_match.group(1)

    return data