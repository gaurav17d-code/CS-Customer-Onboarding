import os
import uuid
import hashlib
from pathlib import Path
from PIL import Image
import numpy as np

# Tesseract OCR
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# PDF to image
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

# OpenCV for image preprocessing
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

STORAGE_ROOT = os.environ.get('STORAGE_ROOT', 'storage')

def ensure_dirs():
    for d in ['storage/uploads', 'storage/pages', 'storage/crops']:
        os.makedirs(d, exist_ok=True)

def file_hash(filepath):
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def preprocess_image(img: Image.Image) -> Image.Image:
    """Apply deskew, denoise, contrast enhancement to improve OCR accuracy."""
    if not CV2_AVAILABLE:
        return img
    try:
        img_array = np.array(img.convert('RGB'))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        # Adaptive threshold
        thresh = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        return Image.fromarray(thresh)
    except Exception:
        return img

def pdf_to_images(pdf_path: str) -> list:
    """Convert PDF to list of PIL Images."""
    if not PDF2IMAGE_AVAILABLE:
        return []
    try:
        images = convert_from_path(pdf_path, dpi=200)
        return images
    except Exception as e:
        print(f'PDF conversion error: {e}')
        return []

def run_ocr(img: Image.Image) -> dict:
    """Run Tesseract OCR and return text + bounding box data."""
    if not TESSERACT_AVAILABLE:
        return {'text': '', 'data': {}}
    try:
        processed = preprocess_image(img)
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(processed, config=custom_config, lang='eng')
        data = pytesseract.image_to_data(
            processed, config=custom_config, lang='eng',
            output_type=pytesseract.Output.DICT
        )
        return {'text': text, 'data': data}
    except Exception as e:
        print(f'OCR error: {e}')
        return {'text': '', 'data': {}}

def get_word_bboxes(ocr_data: dict) -> list:
    """Extract word-level bounding boxes from Tesseract output."""
    boxes = []
    n = len(ocr_data.get('text', []))
    for i in range(n):
        word = ocr_data['text'][i].strip()
        conf = int(ocr_data['conf'][i]) if ocr_data['conf'][i] != '-1' else 0
        if word and conf > 0:
            boxes.append({
                'word': word,
                'conf': conf / 100.0,
                'x': ocr_data['left'][i],
                'y': ocr_data['top'][i],
                'w': ocr_data['width'][i],
                'h': ocr_data['height'][i]
            })
    return boxes

def crop_region(img: Image.Image, x1: int, y1: int, x2: int, y2: int,
                 padding: int = 10) -> Image.Image:
    """Crop a region from image with optional padding."""
    w, h = img.size
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w, x2 + padding)
    y2 = min(h, y2 + padding)
    return img.crop((x1, y1, x2, y2))

def save_page_image(img: Image.Image, doc_id: str, page_num: int) -> str:
    """Save page image to storage and return path."""
    ensure_dirs()
    filename = f'{doc_id}_page_{page_num:03d}.png'
    path = os.path.join(STORAGE_ROOT, 'pages', filename)
    img.save(path, 'PNG')
    return path

def save_crop_image(img: Image.Image, field_id: str) -> str:
    """Save cropped field image."""
    ensure_dirs()
    filename = f'crop_{field_id}.png'
    path = os.path.join(STORAGE_ROOT, 'crops', filename)
    img.save(path, 'PNG')
    return path

def process_uploaded_file(file_bytes: bytes, filename: str, case_id: str) -> dict:
    """
    Main entry: save file, split into pages, run OCR.
    Returns dict with doc_id, storage_path, pages list.
    """
    ensure_dirs()
    doc_id = str(uuid.uuid4())
    ext = Path(filename).suffix.lower()
    save_path = os.path.join(STORAGE_ROOT, 'uploads', f'{doc_id}{ext}')

    with open(save_path, 'wb') as f:
        f.write(file_bytes)

    checksum = hashlib.md5(file_bytes).hexdigest()
    pages = []

    if ext == '.pdf':
        images = pdf_to_images(save_path)
        if not images:
            # Fallback: try treating as image
            try:
                img = Image.open(save_path)
                images = [img]
            except Exception:
                images = []
    else:
        try:
            img = Image.open(save_path)
            images = [img]
        except Exception:
            images = []

    for i, img in enumerate(images):
        page_num = i + 1
        page_img_path = save_page_image(img, doc_id, page_num)
        ocr_result = run_ocr(img)
        w, h = img.size
        pages.append({
            'page_id': str(uuid.uuid4()),
            'page_number': page_num,
            'image_path': page_img_path,
            'ocr_text': ocr_result['text'],
            'ocr_data': ocr_result['data'],
            'width': w,
            'height': h,
            'image': img
        })

    return {
        'doc_id': doc_id,
        'storage_path': save_path,
        'checksum': checksum,
        'page_count': len(pages),
        'pages': pages,
        'mime_type': ext.lstrip('.')
    }

def load_page_image(image_path: str) -> Image.Image:
    """Load a stored page image."""
    try:
        return Image.open(image_path)
    except Exception:
        return None

def highlight_region_on_image(img: Image.Image, x1: int, y1: int,
                               x2: int, y2: int, color=(255, 255, 0),
                               width: int = 3) -> Image.Image:
    """Draw a highlight rectangle on image for evidence display."""
    if not CV2_AVAILABLE:
        return img
    try:
        img_arr = np.array(img.convert('RGB'))
        cv2.rectangle(img_arr, (x1, y1), (x2, y2), color, width)
        return Image.fromarray(img_arr)
    except Exception:
        return img
