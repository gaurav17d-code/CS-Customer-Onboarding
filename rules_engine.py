import json
import os
import uuid
from database import upsert_checklist_status, get_checklist, get_documents

CONFIG_DIR = os.environ.get('CONFIG_DIR', 'config')

def load_rules():
    path = os.path.join(CONFIG_DIR, 'checklist_rules.json')
    with open(path) as f:
        return json.load(f)

STATUS_MISSING = 'Missing'
STATUS_SUBMITTED = 'Submitted'
STATUS_APPROVED = 'Approved'
STATUS_REJECTED = 'Rejected'
STATUS_PENDING = 'Pending Review'
STATUS_UNREADABLE = 'Submitted but Unreadable'
STATUS_NOT_APPLICABLE = 'Not Applicable'

def initialize_checklist(case_id: str, product_type: str, conditions: dict = None):
    """
    Initialize checklist items for a case based on product type and conditions.
    conditions dict: {'tds_applicable': True, 'is_company': True, 'transport_applicable': False}
    """
    try:
        rules = load_rules()
    except Exception as e:
        return []

    product_rules = rules.get(product_type, {})
    if not product_rules:
        return []

    if conditions is None:
        conditions = {}

    checklist_items = []

    # Mandatory items
    for item_def in product_rules.get('mandatory', []):
        status_id = str(uuid.uuid4())
        upsert_checklist_status(
            status_id, case_id, product_type,
            item_def['item'], 1, None, STATUS_MISSING, None, None
        )
        checklist_items.append({
            'id': status_id,
            'item': item_def['item'],
            'doc_type': item_def['doc_type'],
            'mandatory': True,
            'condition': None,
            'status': STATUS_MISSING
        })

    # Conditional items
    for item_def in product_rules.get('conditional', []):
        cond = item_def.get('condition')
        cond_label = item_def.get('condition_label', '')
        applicable = conditions.get(cond, False)
        status = STATUS_MISSING if applicable else STATUS_NOT_APPLICABLE
        status_id = str(uuid.uuid4())
        upsert_checklist_status(
            status_id, case_id, product_type,
            item_def['item'], 0, f'{cond}={applicable}',
            status, None, f'Conditional: {cond_label}'
        )
        checklist_items.append({
            'id': status_id,
            'item': item_def['item'],
            'doc_type': item_def['doc_type'],
            'mandatory': False,
            'condition': cond,
            'condition_label': cond_label,
            'applicable': applicable,
            'status': status
        })

    return checklist_items

def update_checklist_from_documents(case_id: str, product_type: str):
    """
    Compare uploaded documents against checklist and update statuses.
    Called after documents are uploaded and classified.
    """
    try:
        rules = load_rules()
    except Exception:
        return

    product_rules = rules.get(product_type, {})
    checklist_db = get_checklist(case_id)
    documents = get_documents(case_id)

    # Build set of classified doc types from uploaded documents
    uploaded_types = {}
    for doc in documents:
        dt = doc.get('classified_type', 'other')
        conf = doc.get('classification_confidence', 0.0)
        if dt not in uploaded_types or conf > uploaded_types[dt]['conf']:
            uploaded_types[dt] = {'doc_id': doc['document_id'], 'conf': conf}

    all_items = product_rules.get('mandatory', []) + product_rules.get('conditional', [])
    doc_type_to_item = {i['doc_type']: i['item'] for i in all_items}

    for checklist_row in checklist_db:
        item_name = checklist_row['checklist_item_name']
        current_status = checklist_row['status']

        if current_status == STATUS_NOT_APPLICABLE:
            continue

        # Find matching doc_type for this item
        matching_doc_type = None
        for item_def in all_items:
            if item_def['item'] == item_name:
                matching_doc_type = item_def['doc_type']
                break

        if matching_doc_type and matching_doc_type in uploaded_types:
            doc_info = uploaded_types[matching_doc_type]
            conf = doc_info['conf']
            new_status = STATUS_SUBMITTED if conf >= 0.50 else STATUS_UNREADABLE
            upsert_checklist_status(
                checklist_row['checklist_status_id'],
                case_id, product_type, item_name,
                checklist_row['mandatory_flag'],
                checklist_row['conditional_rule'],
                new_status,
                doc_info['doc_id'],
                checklist_row['comments']
            )

def get_checklist_summary(case_id: str) -> dict:
    """Return summary counts for the checklist."""
    checklist = get_checklist(case_id)
    total = len(checklist)
    missing = sum(1 for c in checklist if c['status'] == STATUS_MISSING)
    submitted = sum(1 for c in checklist if c['status'] in [STATUS_SUBMITTED, STATUS_APPROVED])
    pending = sum(1 for c in checklist if c['status'] == STATUS_PENDING)
    not_applicable = sum(1 for c in checklist if c['status'] == STATUS_NOT_APPLICABLE)
    return {
        'total': total,
        'missing': missing,
        'submitted': submitted,
        'pending': pending,
        'not_applicable': not_applicable,
        'complete': missing == 0
    }

def get_product_types() -> list:
    try:
        rules = load_rules()
        return list(rules.keys())
    except Exception:
        return ['Bitumen', 'Sulphur', 'HSD', 'SEZ']

def get_checklist_items_for_product(product_type: str) -> list:
    """Get all checklist items (mandatory + conditional) for a product."""
    try:
        rules = load_rules()
    except Exception:
        return []
    product_rules = rules.get(product_type, {})
    items = []
    for i in product_rules.get('mandatory', []):
        items.append({**i, 'mandatory': True, 'condition': None})
    for i in product_rules.get('conditional', []):
        items.append({**i, 'mandatory': False})
    return items
