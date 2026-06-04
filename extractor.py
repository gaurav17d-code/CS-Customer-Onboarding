import re
import json
import os
import uuid
from ocr_engine import get_word_bboxes, crop_region, save_crop_image, load_page_image

CONFIG_DIR = os.environ.get('CONFIG_DIR', 'config')

def load_patterns():
    path = os.path.join(CONFIG_DIR, 'extraction_patterns.json')
    with open(path) as f:
        return json.load(f)

def normalize_value(value: str, field_name: str) -> str:
    """Normalize extracted value: strip whitespace, uppercase identifiers."""
    if not value:
        return ''
    value = value.strip()
    id_fields = ['pan_no', 'tan_no', 'gst_no', 'cin_no', 'ifsc_code']
    if field_name in id_fields:
        value = value.upper().replace(' ', '')
    return value

def find_value_near_keyword(ocr_text: str, keywords: list, lines: list = None) -> tuple:
    """
    Search OCR text for a value appearing after/near a keyword label.
    Returns (value, confidence, line_index).
    """
    if not ocr_text:
        return None, 0.0, -1

    text_lines = ocr_text.split('\n') if lines is None else lines

    for line_idx, line in enumerate(text_lines):
        line_lower = line.lower()
        for kw in keywords:
            if kw.lower() in line_lower:
                # Extract value after colon or on next line
                after_colon = re.split(r'[:\-]', line, 1)
                if len(after_colon) > 1:
                    candidate = after_colon[-1].strip()
                    if candidate and len(candidate) > 1:
                        return candidate, 0.75, line_idx
                # Try next line
                if line_idx + 1 < len(text_lines):
                    next_line = text_lines[line_idx + 1].strip()
                    if next_line and len(next_line) > 1:
                        return next_line, 0.65, line_idx + 1
    return None, 0.0, -1

def find_regex_value(ocr_text: str, pattern: str) -> tuple:
    """Find a value matching a regex pattern in OCR text."""
    if not pattern or not ocr_text:
        return None, 0.0
    try:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            return match.group(), 0.90
    except Exception:
        pass
    return None, 0.0

def estimate_bbox_for_line(ocr_data: dict, line_idx: int, img_width: int, img_height: int) -> tuple:
    """Estimate bounding box for a line based on Tesseract word data."""
    if not ocr_data or 'text' not in ocr_data:
        # Return approximate region based on line index
        line_height = max(20, img_height // 40)
        y1 = line_idx * line_height
        y2 = y1 + line_height
        return 0, y1, img_width, y2

    # Find words on or near the line
    words = get_word_bboxes(ocr_data)
    if not words:
        line_height = max(20, img_height // 40)
        y1 = line_idx * line_height
        return 0, y1, img_width, y1 + line_height

    # Group words roughly by y-position into lines
    if words:
        sorted_words = sorted(words, key=lambda w: w['y'])
        # Get rough y-range for this line index
        total_lines = max(1, len(set(int(w['y'] / 20) for w in sorted_words)))
        line_height = img_height / max(total_lines, 30)
        y1 = int(line_idx * line_height)
        y2 = int(y1 + line_height * 1.5)

        # Find words in this y-range
        line_words = [w for w in sorted_words if y1 <= w['y'] <= y2]
        if line_words:
            bx1 = min(w['x'] for w in line_words)
            by1 = min(w['y'] for w in line_words)
            bx2 = max(w['x'] + w['w'] for w in line_words)
            by2 = max(w['y'] + w['h'] for w in line_words)
            return bx1, by1, bx2, by2

    return 0, 0, img_width, min(50, img_height)

def extract_fields_from_page(page: dict, doc_type: str) -> list:
    """
    Extract canonical fields from a single page for a given doc_type.
    Returns list of extraction result dicts.
    """
    try:
        patterns = load_patterns()
    except Exception:
        return []

    field_defs = patterns.get('field_patterns', {}).get(doc_type, {})
    if not field_defs:
        return []

    ocr_text = page.get('ocr_text', '')
    ocr_data = page.get('ocr_data', {})
    img_width = page.get('width', 800)
    img_height = page.get('height', 1000)

    results = []

    for canonical_name, field_def in field_defs.items():
        regex = field_def.get('regex')
        keywords = field_def.get('keywords', [])

        extracted_value = None
        confidence = 0.0
        line_idx = -1

        # Try regex first
        if regex:
            val, conf = find_regex_value(ocr_text, regex)
            if val:
                extracted_value = val
                confidence = conf

        # Try keyword proximity
        if not extracted_value and keywords:
            val, conf, lidx = find_value_near_keyword(ocr_text, keywords)
            if val:
                extracted_value = val
                confidence = conf
                line_idx = lidx

        if extracted_value:
            normalized = normalize_value(extracted_value, canonical_name)

            # Estimate bounding box
            bbox = estimate_bbox_for_line(ocr_data, max(0, line_idx), img_width, img_height)

            # Try to crop and save evidence image
            crop_path = None
            try:
                img = load_page_image(page.get('image_path', ''))
                if img:
                    x1, y1, x2, y2 = bbox
                    crop = crop_region(img, x1, y1, x2, y2)
                    field_id = str(uuid.uuid4())
                    crop_path = save_crop_image(crop, field_id)
            except Exception:
                pass

            results.append({
                'field_id': str(uuid.uuid4()),
                'canonical_field_name': canonical_name,
                'extracted_value': extracted_value,
                'normalized_value': normalized,
                'confidence_score': confidence,
                'bbox': bbox,
                'line_idx': line_idx,
                'crop_path': crop_path,
                'extractor_name': 'regex_keyword'
            })

    return results

def extract_all_pages(pages: list, doc_type: str) -> list:
    """Extract fields from all pages of a document."""
    all_results = []
    for page in pages:
        page_results = extract_fields_from_page(page, doc_type)
        for r in page_results:
            r['page_id'] = page.get('page_id', '')
            r['page_number'] = page.get('page_number', 1)
            r['image_path'] = page.get('image_path', '')
        all_results.extend(page_results)
    return all_results

def validate_format(value: str, field_name: str, format_rules: dict) -> tuple:
    """Validate a value against format rules. Returns (is_valid, message)."""
    pattern = format_rules.get(field_name)
    if not pattern:
        return True, 'No format rule'
    if not value:
        return False, 'Empty value'
    match = re.fullmatch(pattern, value.strip(), re.IGNORECASE)
    if match:
        return True, 'Valid'
    return False, f'Does not match expected format for {field_name}'


# Function alias for compatibility with pages
extract_fields = extract_fields_from_page
