from database import get_fields_for_case, get_fields_by_canonical
from difflib import SequenceMatcher

CANONICAL_FIELDS = [
    'customer_name', 'gst_no', 'pan_no', 'tan_no', 'cin_no',
    'account_number', 'ifsc_code', 'bank_name', 'state', 'address',
    'contact_name', 'mobile', 'email', 'gst_registration_type'
]

NAME_PRECEDENCE = [
    'gst_certificate', 'cin', 'pan', 'tan', 'aadhaar', 'cancelled_cheque'
]

def similarity(a: str, b: str) -> float:
    """String similarity ratio 0-1."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def group_fields_by_canonical(case_id: str) -> dict:
    """
    Group all extracted fields by canonical name.
    Returns {canonical_name: [field_dict, ...]}
    """
    all_fields = get_fields_for_case(case_id)
    grouped = {}
    for f in all_fields:
        name = f['canonical_field_name']
        if name not in grouped:
            grouped[name] = []
        grouped[name].append(f)
    return grouped

def detect_conflicts(fields: list, threshold: float = 0.85) -> dict:
    """
    Given a list of extracted field instances for the same canonical name,
    detect conflicts where values differ beyond threshold.
    Returns: {'has_conflict': bool, 'values': [...], 'conflict_pairs': [...]}
    """
    if not fields:
        return {'has_conflict': False, 'values': [], 'conflict_pairs': []}

    values = [f.get('normalized_value') or f.get('extracted_value', '') for f in fields]
    values = [v for v in values if v]

    if len(values) <= 1:
        return {'has_conflict': False, 'values': values, 'conflict_pairs': []}

    conflict_pairs = []
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            sim = similarity(values[i], values[j])
            if sim < threshold:
                conflict_pairs.append({
                    'value_a': values[i],
                    'source_a': fields[i].get('source_document_type'),
                    'value_b': values[j],
                    'source_b': fields[j].get('source_document_type'),
                    'similarity': round(sim, 3)
                })

    return {
        'has_conflict': len(conflict_pairs) > 0,
        'values': values,
        'conflict_pairs': conflict_pairs
    }

def suggest_best_value(fields: list, canonical_name: str,
                        precedence_list: list = None) -> dict:
    """
    Suggest the best value for a canonical field based on source precedence.
    Returns: {'value': str, 'confidence': float, 'source_doc_type': str, 'field': dict}
    """
    if not fields:
        return {'value': None, 'confidence': 0.0, 'source_doc_type': None, 'field': None}

    prec = precedence_list if precedence_list else NAME_PRECEDENCE

    # Sort by precedence then by confidence
    def sort_key(f):
        doc_type = f.get('source_document_type', 'other')
        try:
            prec_idx = prec.index(doc_type)
        except ValueError:
            prec_idx = len(prec)
        return (prec_idx, -f.get('confidence_score', 0.0))

    sorted_fields = sorted(fields, key=sort_key)
    best = sorted_fields[0]
    return {
        'value': best.get('normalized_value') or best.get('extracted_value', ''),
        'confidence': best.get('confidence_score', 0.0),
        'source_doc_type': best.get('source_document_type'),
        'field': best
    }

def run_cross_verification(case_id: str) -> dict:
    """
    Run full cross-document verification for all canonical fields.
    Returns a verification report dict.
    """
    grouped = group_fields_by_canonical(case_id)
    report = {}

    for canonical_name in CANONICAL_FIELDS:
        fields = grouped.get(canonical_name, [])
        conflict_info = detect_conflicts(fields)
        suggestion = suggest_best_value(fields, canonical_name)

        report[canonical_name] = {
            'canonical_name': canonical_name,
            'found_count': len(fields),
            'sources': [f.get('source_document_type') for f in fields],
            'values': conflict_info['values'],
            'has_conflict': conflict_info['has_conflict'],
            'conflict_pairs': conflict_info['conflict_pairs'],
            'suggested_value': suggestion['value'],
            'suggested_confidence': suggestion['confidence'],
            'suggested_source': suggestion['source_doc_type'],
            'suggested_field': suggestion['field'],
            'fields': fields
        }

    # Also include any fields found that are not in the default list
    for name, fields in grouped.items():
        if name not in report:
            conflict_info = detect_conflicts(fields)
            suggestion = suggest_best_value(fields, name)
            report[name] = {
                'canonical_name': name,
                'found_count': len(fields),
                'sources': [f.get('source_document_type') for f in fields],
                'values': conflict_info['values'],
                'has_conflict': conflict_info['has_conflict'],
                'conflict_pairs': conflict_info['conflict_pairs'],
                'suggested_value': suggestion['value'],
                'suggested_confidence': suggestion['confidence'],
                'suggested_source': suggestion['source_doc_type'],
                'suggested_field': suggestion['field'],
                'fields': fields
            }

    return report

def get_verification_summary(report: dict) -> dict:
    total = len(report)
    found = sum(1 for v in report.values() if v['found_count'] > 0)
    conflicts = sum(1 for v in report.values() if v['has_conflict'])
    missing = sum(1 for v in report.values() if v['found_count'] == 0)
    return {
        'total_fields': total,
        'fields_found': found,
        'fields_missing': missing,
        'fields_with_conflict': conflicts
    }
