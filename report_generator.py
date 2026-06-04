from datetime import datetime
from database import get_case, get_documents, get_checklist, get_audit, get_resolutions
from rules_engine import get_checklist_summary
from cross_verifier import run_cross_verification, get_verification_summary

def generate_html_report(case_id: str) -> str:
    """Generate a full HTML exception/verification report for a case."""
    case = get_case(case_id)
    if not case:
        return '<p>Case not found.</p>'

    documents = get_documents(case_id)
    checklist = get_checklist(case_id)
    resolutions = get_resolutions(case_id)
    audit = get_audit(case_id)
    checklist_summary = get_checklist_summary(case_id)
    verification_report = run_cross_verification(case_id)
    ver_summary = get_verification_summary(verification_report)

    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    STATUS_COLORS = {
        'Missing': '#FF6B6B',
        'Submitted': '#4ECDC4',
        'Approved': '#45B7D1',
        'Rejected': '#FF6B6B',
        'Pending Review': '#FFA07A',
        'Submitted but Unreadable': '#FFD93D',
        'Not Applicable': '#95A5A6'
    }

    def color_for(status):
        return STATUS_COLORS.get(status, '#BDC3C7')

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='UTF-8'>
<title>Verification Report - {case_id}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; }}
  h1 {{ color: #2C3E50; border-bottom: 2px solid #3498DB; padding-bottom: 10px; }}
  h2 {{ color: #2980B9; margin-top: 30px; }}
  .summary-grid {{ display: flex; gap: 20px; flex-wrap: wrap; margin: 20px 0; }}
  .summary-card {{ background: #ECF0F1; border-radius: 8px; padding: 15px; min-width: 150px; text-align: center; }}
  .summary-card .number {{ font-size: 2em; font-weight: bold; color: #2C3E50; }}
  .summary-card .label {{ font-size: 0.9em; color: #7F8C8D; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  th {{ background: #3498DB; color: white; padding: 10px; text-align: left; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #ECF0F1; }}
  tr:nth-child(even) {{ background: #F9F9F9; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.85em; color: white; }}
  .conflict {{ color: #E74C3C; font-weight: bold; }}
  .ok {{ color: #27AE60; }}
  .pending {{ color: #F39C12; }}
  .footer {{ margin-top: 40px; font-size: 0.8em; color: #95A5A6; border-top: 1px solid #ECF0F1; padding-top: 10px; }}
</style>
</head>
<body>
<h1>Customer Onboarding Verification Report</h1>
<p><strong>Case ID:</strong> {case_id} | <strong>Generated:</strong> {now} | <strong>Status:</strong> {case.get('status', 'N/A')}</p>

<h2>Case Summary</h2>
<table>
  <tr><th>Field</th><th>Value</th></tr>
  <tr><td>Customer Name</td><td>{case.get('provisional_customer_name','')}</td></tr>
  <tr><td>Product</td><td>{case.get('product_type','')}</td></tr>
  <tr><td>Sales Officer</td><td>{case.get('sales_officer','')}</td></tr>
  <tr><td>Sales Area</td><td>{case.get('sales_area','')}</td></tr>
  <tr><td>Regional Office</td><td>{case.get('regional_office','')}</td></tr>
  <tr><td>Created At</td><td>{case.get('created_at','')}</td></tr>
  <tr><td>Created By</td><td>{case.get('created_by','')}</td></tr>
</table>

<h2>Document Checklist Status</h2>
<div class='summary-grid'>
  <div class='summary-card'><div class='number'>{checklist_summary['total']}</div><div class='label'>Total Items</div></div>
  <div class='summary-card'><div class='number' style='color:#27AE60'>{checklist_summary['submitted']}</div><div class='label'>Submitted</div></div>
  <div class='summary-card'><div class='number' style='color:#E74C3C'>{checklist_summary['missing']}</div><div class='label'>Missing</div></div>
  <div class='summary-card'><div class='number' style='color:#95A5A6'>{checklist_summary['not_applicable']}</div><div class='label'>Not Applicable</div></div>
</div>
<table>
  <tr><th>Document</th><th>Mandatory</th><th>Status</th><th>Notes</th></tr>
"""
    for item in checklist:
        status = item.get('status', 'Missing')
        mandatory = 'Yes' if item.get('mandatory_flag') else 'No'
        color = color_for(status)
        html += f"  <tr><td>{item['checklist_item_name']}</td><td>{mandatory}</td>"
        html += f"<td><span class='badge' style='background:{color}'>{status}</span></td>"
        html += f"<td>{item.get('comments','') or ''}</td></tr>\n"

    html += f"""</table>

<h2>Field Verification Summary</h2>
<div class='summary-grid'>
  <div class='summary-card'><div class='number'>{ver_summary['fields_found']}</div><div class='label'>Fields Found</div></div>
  <div class='summary-card'><div class='number' style='color:#E74C3C'>{ver_summary['fields_with_conflict']}</div><div class='label'>Conflicts</div></div>
  <div class='summary-card'><div class='number' style='color:#E74C3C'>{ver_summary['fields_missing']}</div><div class='label'>Not Found</div></div>
</div>
<table>
  <tr><th>Field</th><th>Sources Found</th><th>Suggested Value</th><th>Conflict</th><th>Reviewer Decision</th></tr>
"""
    for name, info in verification_report.items():
        conflict_marker = "<span class='conflict'>CONFLICT</span>" if info['has_conflict'] else "<span class='ok'>OK</span>"
        suggested = info.get('suggested_value') or '-'
        sources = ', '.join(set(s for s in info.get('sources', []) if s)) or '-'
        resolution = resolutions.get(name, {})
        decision = resolution.get('final_value', '-') if resolution else '-'
        html += f"  <tr><td>{name}</td><td>{sources}</td><td>{suggested}</td><td>{conflict_marker}</td><td>{decision}</td></tr>\n"

    html += f"""</table>

<h2>Uploaded Documents ({len(documents)})</h2>
<table>
  <tr><th>Filename</th><th>Classified As</th><th>Confidence</th><th>Pages</th><th>Uploaded</th></tr>
"""
    for doc in documents:
        conf = doc.get('classification_confidence', 0)
        conf_color = '#27AE60' if conf >= 0.80 else ('#F39C12' if conf >= 0.60 else '#E74C3C')
        html += f"  <tr><td>{doc['filename']}</td><td>{doc.get('classified_type','')}</td>"
        html += f"<td style='color:{conf_color}'>{conf:.0%}</td><td>{doc.get('page_count',1)}</td>"
        html += f"<td>{doc.get('upload_timestamp','')[:16]}</td></tr>\n"

    html += f"""</table>

<h2>Audit Trail ({len(audit)} events)</h2>
<table>
  <tr><th>Timestamp</th><th>Event</th><th>Actor</th><th>Details</th></tr>
"""
    for event in audit[-20:]:  # Show last 20
        html += f"  <tr><td>{event.get('event_timestamp','')[:16]}</td>"
        html += f"<td>{event.get('event_type','')}</td><td>{event.get('actor_id','')}</td>"
        html += f"<td>{event.get('comments','') or ''}</td></tr>\n"

    html += f"""</table>
<div class='footer'>Report generated on {now} | CS Customer Onboarding Portal</div>
</body></html>"""
    return html

def get_report_readiness(case_id: str) -> dict:
    """Check if a case is ready for CMR generation."""
    summary = get_checklist_summary(case_id)
    ver = run_cross_verification(case_id)
    ver_sum = get_verification_summary(ver)
    resolutions = get_resolutions(case_id)

    issues = []
    if summary['missing'] > 0:
        issues.append(f"{summary['missing']} mandatory document(s) still missing")
    if ver_sum['fields_with_conflict'] > 0:
        issues.append(f"{ver_sum['fields_with_conflict']} field conflict(s) need resolution")

    return {
        'ready': len(issues) == 0,
        'issues': issues,
        'checklist_complete': summary['missing'] == 0,
        'no_conflicts': ver_sum['fields_with_conflict'] == 0,
        'resolved_fields': len(resolutions)
    }
