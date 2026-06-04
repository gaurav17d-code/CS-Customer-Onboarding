import json
import os
import re
from pathlib import Path

CONFIG_DIR = os.environ.get('CONFIG_DIR', 'config')

def load_patterns():
    path = os.path.join(CONFIG_DIR, 'extraction_patterns.json')
    with open(path) as f:
        return json.load(f)

DOC_TYPE_LABELS = {
    'gst_certificate': 'GST Certificate',
    'gst_annexure': 'GST Annexure',
    'pan': 'PAN',
    'aadhaar': 'Aadhaar',
    'tan': 'TAN',
    'cin': 'CIN / Certificate of Incorporation',
    'cancelled_cheque': 'Cancelled Cheque',
    'work_order': 'Work Order',
    'tds_tcs_declaration': 'TDS/TCS Declaration',
    'storage_licence': 'Storage Licence',
    'noc': 'NOC',
    'transport_licence': 'Transport Licence',
    'end_user_certificate': 'End User Certificate',
    'other': 'Other / Unclassified'
}

FILENAME_HINTS = {
    'gst': 'gst_certificate',
    'gstin': 'gst_certificate',
    'annexure': 'gst_annexure',
    'pan': 'pan',
    'aadhaar': 'aadhaar',
    'aadhar': 'aadhaar',
    'tan': 'tan',
    'cin': 'cin',
    'incorporation': 'cin',
    'cheque': 'cancelled_cheque',
    'chq': 'cancelled_cheque',
    'bank': 'cancelled_cheque',
    'work_order': 'work_order',
    'workorder': 'work_order',
    'wo_': 'work_order',
    'tds': 'tds_tcs_declaration',
    'tcs': 'tds_tcs_declaration',
    'declaration': 'tds_tcs_declaration',
    'storage': 'storage_licence',
    'noc': 'noc',
    'transport': 'transport_licence',
    'vehicle': 'transport_licence',
    'end_user': 'end_user_certificate',
    'enduser': 'end_user_certificate',
    'euc': 'end_user_certificate',
    'sez': 'end_user_certificate'
}

def classify_by_filename(filename: str) -> tuple:
    """Returns (doc_type, confidence) based on filename hints."""
    stem = Path(filename).stem.lower().replace(' ', '_').replace('-', '_')
    for hint, doc_type in FILENAME_HINTS.items():
        if hint in stem:
            return doc_type, 0.80
    return None, 0.0

def classify_by_ocr_text(ocr_text: str) -> tuple:
    """Returns (doc_type, confidence) based on OCR keyword matching."""
    try:
        patterns = load_patterns()
    except Exception:
        return 'other', 0.0

    text_lower = ocr_text.lower()
    scores = {}

    for doc_type, keywords in patterns.get('document_keywords', {}).items():
        score = 0
        for kw in keywords:
            if kw.lower() in text_lower:
                score += 1
        if score > 0:
            scores[doc_type] = score / len(keywords)

    if not scores:
        return 'other', 0.0

    best = max(scores, key=scores.get)
    # Normalize confidence: cap at 0.95
    confidence = min(0.95, 0.50 + scores[best] * 0.45)
    return best, round(confidence, 3)

def classify_document(filename: str, ocr_text: str) -> tuple:
    """
    Combined classifier: filename hint first, then OCR text.
    Returns (doc_type, confidence, method).
    """
    # Try filename first
    fn_type, fn_conf = classify_by_filename(filename)
    if fn_type and fn_conf >= 0.75:
        return fn_type, fn_conf, 'filename'

    # Fall back to OCR text
    if ocr_text and ocr_text.strip():
        ocr_type, ocr_conf = classify_by_ocr_text(ocr_text)
        if ocr_conf >= 0.40:
            # Merge with filename hint if consistent
            if fn_type and fn_type == ocr_type:
                combined_conf = min(0.97, fn_conf * 0.3 + ocr_conf * 0.7 + 0.10)
                return ocr_type, round(combined_conf, 3), 'combined'
            return ocr_type, ocr_conf, 'ocr'

    if fn_type:
        return fn_type, fn_conf, 'filename'

    return 'other', 0.0, 'unclassified'

def needs_human_review(confidence: float, threshold: float = 0.65) -> bool:
    """Returns True if document classification confidence is below threshold."""
    return confidence < threshold

def get_all_doc_type_labels() -> dict:
    return DOC_TYPE_LABELS

def label_for(doc_type: str) -> str:
    return DOC_TYPE_LABELS.get(doc_type, doc_type)
