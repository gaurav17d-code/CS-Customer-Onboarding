import sqlite3
import os
import json
from datetime import datetime
import uuid

DB_PATH = os.environ.get('DB_PATH', 'onboarding.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS onboarding_case (
        case_id TEXT PRIMARY KEY,
        product_type TEXT NOT NULL,
        provisional_customer_name TEXT,
        sales_officer TEXT,
        sales_area TEXT,
        regional_office TEXT,
        status TEXT DEFAULT 'Draft',
        remarks TEXT,
        created_at TEXT,
        created_by TEXT
    );
    CREATE TABLE IF NOT EXISTS uploaded_document (
        document_id TEXT PRIMARY KEY,
        case_id TEXT,
        filename TEXT,
        file_type TEXT,
        mime_type TEXT,
        page_count INTEGER DEFAULT 1,
        upload_timestamp TEXT,
        uploaded_by TEXT,
        classified_type TEXT,
        classification_confidence REAL DEFAULT 0.0,
        checksum TEXT,
        storage_path TEXT,
        FOREIGN KEY(case_id) REFERENCES onboarding_case(case_id)
    );
    CREATE TABLE IF NOT EXISTS document_page (
        page_id TEXT PRIMARY KEY,
        document_id TEXT,
        page_number INTEGER,
        image_path TEXT,
        ocr_text TEXT,
        width INTEGER,
        height INTEGER,
        FOREIGN KEY(document_id) REFERENCES uploaded_document(document_id)
    );
    CREATE TABLE IF NOT EXISTS extracted_field (
        field_id TEXT PRIMARY KEY,
        case_id TEXT,
        canonical_field_name TEXT,
        source_document_id TEXT,
        source_page_id TEXT,
        source_document_type TEXT,
        extracted_value TEXT,
        normalized_value TEXT,
        confidence_score REAL DEFAULT 0.0,
        bbox_x1 INTEGER, bbox_y1 INTEGER, bbox_x2 INTEGER, bbox_y2 INTEGER,
        extractor_name TEXT,
        review_status TEXT DEFAULT 'pending',
        reviewer_selected_flag INTEGER DEFAULT 0,
        FOREIGN KEY(case_id) REFERENCES onboarding_case(case_id)
    );
    CREATE TABLE IF NOT EXISTS checklist_item_status (
        checklist_status_id TEXT PRIMARY KEY,
        case_id TEXT,
        product_type TEXT,
        checklist_item_name TEXT,
        mandatory_flag INTEGER DEFAULT 1,
        conditional_rule TEXT,
        status TEXT DEFAULT 'Missing',
        linked_document_id TEXT,
        comments TEXT,
        FOREIGN KEY(case_id) REFERENCES onboarding_case(case_id)
    );
    CREATE TABLE IF NOT EXISTS field_resolution (
        resolution_id TEXT PRIMARY KEY,
        case_id TEXT,
        canonical_field_name TEXT,
        final_value TEXT,
        selected_source_field_id TEXT,
        resolution_type TEXT,
        reviewer_id TEXT,
        reviewer_comment TEXT,
        resolved_at TEXT,
        FOREIGN KEY(case_id) REFERENCES onboarding_case(case_id)
    );
    CREATE TABLE IF NOT EXISTS audit_event (
        event_id TEXT PRIMARY KEY,
        case_id TEXT,
        event_type TEXT,
        actor_id TEXT,
        event_timestamp TEXT,
        old_value TEXT,
        new_value TEXT,
        comments TEXT
    );
    ''')
    conn.commit()
    conn.close()

# Case helpers
def create_case(case_id, product_type, customer_name, sales_officer, sales_area,
                regional_office, remarks, created_by):
    conn = get_conn()
    conn.execute("""
        INSERT INTO onboarding_case
        (case_id,product_type,provisional_customer_name,sales_officer,
         sales_area,regional_office,status,remarks,created_at,created_by)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (case_id, product_type, customer_name, sales_officer, sales_area,
          regional_office, 'Draft', remarks, datetime.now().isoformat(), created_by))
    conn.commit(); conn.close()

def get_all_cases():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM onboarding_case ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_case(case_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM onboarding_case WHERE case_id=?', (case_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_case_status(case_id, status):
    conn = get_conn()
    conn.execute('UPDATE onboarding_case SET status=? WHERE case_id=?', (status, case_id))
    conn.commit(); conn.close()

# Document helpers
def save_document(doc_id, case_id, filename, file_type, mime_type, page_count,
                  uploaded_by, classified_type, confidence, checksum, storage_path):
    conn = get_conn()
    conn.execute("""
        INSERT INTO uploaded_document
        (document_id,case_id,filename,file_type,mime_type,page_count,
         upload_timestamp,uploaded_by,classified_type,classification_confidence,
         checksum,storage_path)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (doc_id, case_id, filename, file_type, mime_type, page_count,
          datetime.now().isoformat(), uploaded_by, classified_type, confidence,
          checksum, storage_path))
    conn.commit(); conn.close()

def get_documents(case_id):
    conn = get_conn()
    rows = conn.execute('SELECT * FROM uploaded_document WHERE case_id=?', (case_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_document(doc_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM uploaded_document WHERE document_id=?', (doc_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_document_classification(doc_id, classified_type, confidence):
    conn = get_conn()
    conn.execute('UPDATE uploaded_document SET classified_type=?, classification_confidence=? WHERE document_id=?',
                 (classified_type, confidence, doc_id))
    conn.commit(); conn.close()

# Page helpers
def save_page(page_id, doc_id, page_num, image_path, ocr_text, width, height):
    conn = get_conn()
    conn.execute("""
        INSERT INTO document_page (page_id,document_id,page_number,image_path,ocr_text,width,height)
        VALUES (?,?,?,?,?,?,?)
    """, (page_id, doc_id, page_num, image_path, ocr_text, width, height))
    conn.commit(); conn.close()

def get_pages(doc_id):
    conn = get_conn()
    rows = conn.execute('SELECT * FROM document_page WHERE document_id=? ORDER BY page_number', (doc_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_page(page_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM document_page WHERE page_id=?', (page_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

# Extracted field helpers
def save_extracted_field(field_id, case_id, canonical_name, doc_id, page_id,
                          doc_type, extracted, normalized, confidence, bbox, extractor_name):
    conn = get_conn()
    conn.execute("""
        INSERT INTO extracted_field
        (field_id,case_id,canonical_field_name,source_document_id,source_page_id,
         source_document_type,extracted_value,normalized_value,confidence_score,
         bbox_x1,bbox_y1,bbox_x2,bbox_y2,extractor_name,review_status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'pending')
    """, (field_id, case_id, canonical_name, doc_id, page_id, doc_type,
          extracted, normalized, confidence,
          bbox[0], bbox[1], bbox[2], bbox[3], extractor_name))
    conn.commit(); conn.close()

def get_fields_for_case(case_id):
    conn = get_conn()
    rows = conn.execute('SELECT * FROM extracted_field WHERE case_id=?', (case_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_fields_by_canonical(case_id, canonical_name):
    conn = get_conn()
    rows = conn.execute('SELECT * FROM extracted_field WHERE case_id=? AND canonical_field_name=?',
                        (case_id, canonical_name)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Checklist helpers
def upsert_checklist_status(status_id, case_id, product_type, item_name,
                             mandatory, cond_rule, status, linked_doc_id, comments):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO checklist_item_status
        (checklist_status_id,case_id,product_type,checklist_item_name,
         mandatory_flag,conditional_rule,status,linked_document_id,comments)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (status_id, case_id, product_type, item_name, mandatory,
          cond_rule, status, linked_doc_id, comments))
    conn.commit(); conn.close()

def get_checklist(case_id):
    conn = get_conn()
    rows = conn.execute('SELECT * FROM checklist_item_status WHERE case_id=?', (case_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Resolution helpers
def save_resolution(res_id, case_id, canonical_name, final_value,
                    source_field_id, resolution_type, reviewer_id, comment):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO field_resolution
        (resolution_id,case_id,canonical_field_name,final_value,
         selected_source_field_id,resolution_type,reviewer_id,reviewer_comment,resolved_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (res_id, case_id, canonical_name, final_value, source_field_id,
          resolution_type, reviewer_id, comment, datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_resolutions(case_id):
    conn = get_conn()
    rows = conn.execute('SELECT * FROM field_resolution WHERE case_id=?', (case_id,)).fetchall()
    conn.close()
    return {r['canonical_field_name']: dict(r) for r in rows}

# Audit helpers
def log_audit(case_id, event_type, actor_id, old_val, new_val, comment):
    conn = get_conn()
    conn.execute("""
        INSERT INTO audit_event (event_id,case_id,event_type,actor_id,
        event_timestamp,old_value,new_value,comments)
        VALUES (?,?,?,?,?,?,?,?)
    """, (str(uuid.uuid4()), case_id, event_type, actor_id,
          datetime.now().isoformat(), old_val, new_val, comment))
    conn.commit(); conn.close()

def get_audit(case_id):
    conn = get_conn()
    rows = conn.execute('SELECT * FROM audit_event WHERE case_id=? ORDER BY event_timestamp',
                        (case_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Stats helper
def get_case_stats(case_id):
    conn = get_conn()
    docs = conn.execute('SELECT COUNT(*) as c FROM uploaded_document WHERE case_id=?', (case_id,)).fetchone()['c']
    missing = conn.execute("SELECT COUNT(*) as c FROM checklist_item_status WHERE case_id=? AND status='Missing'", (case_id,)).fetchone()['c']
    mismatches = conn.execute("SELECT COUNT(*) as c FROM extracted_field WHERE case_id=? AND review_status='conflict'", (case_id,)).fetchone()['c']
    pending = conn.execute("SELECT COUNT(*) as c FROM extracted_field WHERE case_id=? AND review_status='pending'", (case_id,)).fetchone()['c']
    conn.close()
    return {'docs': docs, 'missing': missing, 'mismatches': mismatches, 'pending': pending}
