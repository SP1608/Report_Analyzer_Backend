from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_bytes
import pytesseract
import os
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Backend is working!"}
    
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        file_ext = file.filename.split(".")[-1].lower()

        images = []

        if file_ext == "pdf":
            # Convert PDF pages to images
            images = convert_from_bytes(
                file_bytes,
                poppler_path=r"C:\Users\SHRUTI PANDEY\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"
            )
        elif file_ext in ["png", "jpg", "jpeg"]:
            # Open image using PIL
            image = Image.open(io.BytesIO(file_bytes))
            images = [image]
        else:
            return {"success": False, "error": "Unsupported file type."}

        # OCR extraction
        full_text = ""
        for i, image in enumerate(images):
            extracted = pytesseract.image_to_string(image)
            full_text += f"\n--- Page {i+1} ---\n" + extracted

        if not full_text.strip():
            return {"success": False, "error": "No text extracted from file."}

        data = extract_medical_parameters(full_text)
        return {"success": True, "data": data}

    except Exception as e:
        return {"success": False, "error": str(e)}


def extract_medical_parameters(text: str):
    import re

    reference_data = {
        "Hemoglobin": {"range": (13.0, 17.0), "unit": "g/dL"},
        "WBC": {"range": (4000, 11000), "unit": "cells/mcL"},
        "Platelet": {"range": (150000, 450000), "unit": "platelets/mcL"},
        "RBC": {"range": (4.5, 6.0), "unit": "million/mcL"},
        "Glucose": {"range": (70, 99), "unit": "mg/dL"},
        "Creatinine": {"range": (0.6, 1.3), "unit": "mg/dL"},
        "Cholesterol": {"range": (0, 200), "unit": "mg/dL"},
        "HDL": {"range": (40, 60), "unit": "mg/dL"},
        "LDL": {"range": (0, 130), "unit": "mg/dL"},
        "Triglycerides": {"range": (0, 150), "unit": "mg/dL"},
    }

    lines = text.splitlines()
    records = []

    for line in lines:
        line = line.strip()
        match = re.match(r"([A-Za-z /()-]+)[:\s]+([\d.]+)\s*([a-zA-Z/%μ]+)", line)
        if match:
            param_raw = match.group(1).strip()
            value = match.group(2).strip()
            unit = match.group(3).strip()

            matched_param = next((p for p in reference_data if p.lower() in param_raw.lower()), None)

            if matched_param:
                ref_range = reference_data[matched_param]["range"]
                expected_unit = reference_data[matched_param]["unit"]

                try:
                    num_val = float(value)
                    status = "Normal" if ref_range[0] <= num_val <= ref_range[1] else "Needs Attention"
                except:
                    status = "Unknown"

                records.append({
                    "parameter": matched_param,
                    "value": value,
                    "unit": unit,
                    "range": f"{ref_range[0]} - {ref_range[1]} {expected_unit}",
                    "status": status,
                })
            else:
                records.append({
                    "parameter": param_raw,
                    "value": value,
                    "unit": unit,
                    "range": "-",
                    "status": "Unknown"
                })

    return records
