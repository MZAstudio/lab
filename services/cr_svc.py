"""Change-request approval logic."""
from datetime import datetime, timedelta
from services.db import q, run, get_db


def approve_cr(cr_id):
    cr = q("SELECT * FROM change_requests WHERE id=?", (cr_id,), one=True)
    if not cr: return {'error': 'Change request not found.'}
    if cr['status'] != 'Pending': return {'error': f'Already {cr["status"]}.'}
    charter = q("SELECT * FROM project_charter WHERE id=1", one=True)
    if not charter: return {'error': 'Project charter not found.'}

    old_budget = float(charter['approved_budget'])
    old_deadline = charter['deadline']
    old_req_status = None
    if cr['requirement_id']:
        req = q("SELECT * FROM requirements WHERE id=?", (cr['requirement_id'],), one=True)
        if req: old_req_status = req['status']

    old_approved = [r['title'] for r in q("SELECT title FROM requirements WHERE status='Approved' ORDER BY id")]

    new_budget = old_budget + float(cr['cost_impact'])
    try:
        new_dl = (datetime.strptime(old_deadline, '%Y-%m-%d') +
                  timedelta(days=int(cr['schedule_impact_days']))).strftime('%Y-%m-%d')
    except Exception:
        new_dl = old_deadline

    with get_db() as c:
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("UPDATE change_requests SET status='Approved',approved_at=? WHERE id=?",
                  (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cr_id))
        if cr['requirement_id']:
            c.execute("UPDATE requirements SET status='Approved' WHERE id=?", (cr['requirement_id'],))
        c.execute("UPDATE project_charter SET approved_budget=?,deadline=?,updated_at=? WHERE id=1",
                  (new_budget, new_dl, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        c.commit()

    new_approved = [r['title'] for r in q("SELECT title FROM requirements WHERE status='Approved' ORDER BY id")]
    added = [t for t in new_approved if t not in old_approved]

    return {
        'success': True,
        'cr_title': cr['title'],
        'before': {'budget': old_budget, 'deadline': old_deadline,
                   'scope': old_approved, 'scope_count': len(old_approved)},
        'after': {'budget': new_budget, 'deadline': new_dl,
                  'scope': new_approved, 'scope_count': len(new_approved)},
        'added_to_scope': added,
        'budget_delta': float(cr['cost_impact']),
        'deadline_delta': int(cr['schedule_impact_days']),
        'req_approved': cr['requirement_id'] is not None,
    }


def reject_cr(cr_id):
    cr = q("SELECT * FROM change_requests WHERE id=?", (cr_id,), one=True)
    if not cr: return {'error': 'Change request not found.'}
    if cr['status'] != 'Pending': return {'error': f'Already {cr["status"]}.'}
    run("UPDATE change_requests SET status='Rejected' WHERE id=?", (cr_id,))
    return {'success': True, 'cr_title': cr['title'],
            'message': 'Rejected. No changes made to budget, deadline, or scope.'}


def cr_preview(cr_id):
    cr = q("SELECT * FROM change_requests WHERE id=?", (cr_id,), one=True)
    if not cr: return None
    charter = q("SELECT approved_budget,deadline FROM project_charter WHERE id=1", one=True)
    if not charter: return None
    old_b = float(charter['approved_budget'])
    old_d = charter['deadline']
    try:
        new_d = (datetime.strptime(old_d, '%Y-%m-%d') +
                 timedelta(days=int(cr['schedule_impact_days']))).strftime('%Y-%m-%d')
    except Exception:
        new_d = old_d
    return {'cr': dict(cr), 'old_budget': old_b,
            'new_budget': old_b + float(cr['cost_impact']),
            'old_deadline': old_d, 'new_deadline': new_d}
