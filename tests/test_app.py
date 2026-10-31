"""Automated tests for Smart Healthcare PM System."""
import sys, os, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app as application
from services.db import init_db, q, run
from services.schedule_svc import detect_circular, forward_pass, get_delayed, get_activities, get_deps
from services.evm_svc import compute_evm, _div
from services.cr_svc import approve_cr, reject_cr

@pytest.fixture(autouse=True)
def setup():
    application.app.config['TESTING'] = True
    init_db()

@pytest.fixture
def client():
    with application.app.test_client() as c:
        yield c

# ── TC01: Schedule dependency forward pass ─────────────────────────────────
def test_TC01_forward_pass():
    acts = [
        type('A',(),{'id':1,'planned_start':'2024-01-08','planned_end':'2024-01-12','estimated_duration':5,'percent_complete':100})(),
        type('A',(),{'id':2,'planned_start':'2024-01-15','planned_end':'2024-01-26','estimated_duration':10,'percent_complete':100})(),
    ]
    deps = {2: [1]}
    result = forward_pass(acts, deps)
    # activity 2 should not start before activity 1 ends
    assert result[2]['es'] >= result[1]['ee']

# ── TC02: Circular dependency rejection ────────────────────────────────────
def test_TC02_circular_dependency():
    acts = [
        type('A',(),{'id':1})(), type('A',(),{'id':2})(), type('A',(),{'id':3})()
    ]
    # A->B->C->A is circular
    deps = {2:[1], 3:[2]}
    assert detect_circular(acts, deps, 1, [3]) == True

def test_TC02b_no_false_circular():
    acts = [type('A',(),{'id':i})() for i in [1,2,3,4]]
    deps = {2:[1], 3:[2], 4:[3]}
    assert detect_circular(acts, deps, None, None) == False

# ── TC03: Delayed activity detection ──────────────────────────────────────
def test_TC03_delayed_activities():
    delayed = get_delayed('2024-03-15')
    # seed data has activities that should be delayed by 2024-03-15
    assert isinstance(delayed, list)
    for d in delayed:
        assert 'name' in d
        assert 'reason' in d
        assert 'affected_ids' in d

# ── TC04: EVM formulas ────────────────────────────────────────────────────
def test_TC04_evm_formulas():
    evm = compute_evm('2024-03-15')
    assert 'pv' in evm
    assert 'ev' in evm
    assert 'ac' in evm
    assert evm['pv'] >= 0
    assert evm['ev'] >= 0
    assert evm['ac'] >= 0
    # CPI = EV/AC
    if evm['cpi'] is not None and evm['ac'] > 0:
        assert abs(evm['cpi'] - evm['ev']/evm['ac']) < 0.001
    # SPI = EV/PV
    if evm['spi'] is not None and evm['pv'] > 0:
        assert abs(evm['spi'] - evm['ev']/evm['pv']) < 0.001

# ── TC05: Division by zero in EVM ─────────────────────────────────────────
def test_TC05_division_by_zero():
    assert _div(100, 0) is None
    assert _div(0, 0) is None
    assert _div(100, 50) == 2.0
    assert _div(0, 100) == 0.0

# ── TC06: EVM threshold warnings ──────────────────────────────────────────
def test_TC06_threshold_warnings():
    evm = compute_evm('2024-03-15')
    lvls = [w['lvl'] for w in evm['warnings']]
    cpi = evm['cpi']
    spi = evm['spi']
    if cpi is not None and cpi < 0.90:
        assert 'critical' in lvls
    if spi is not None and spi < 0.90:
        assert 'critical' in lvls

# ── TC07: Unapproved requirement blocked from scope ───────────────────────
def test_TC07_unapproved_req_blocked(client):
    # Try linking a Proposed requirement to a WBS deliverable
    proposed = q("SELECT id FROM requirements WHERE status='Proposed' LIMIT 1", one=True)
    if not proposed:
        pytest.skip("No proposed requirements in seed data")
    resp = client.post('/scope/deliverable', data={
        'name': 'Test Deliverable Blocked',
        'description': 'Test',
        'requirement_id': str(proposed['id'])
    })
    data = resp.get_json()
    assert resp.status_code == 400
    assert data.get('errors')

# ── TC08: Change request approval updates budget/deadline/scope ────────────
def test_TC08_cr_approval():
    pending = q("SELECT * FROM change_requests WHERE status='Pending' LIMIT 1", one=True)
    if not pending:
        pytest.skip("No pending CRs")
    charter_before = q("SELECT approved_budget,deadline FROM project_charter WHERE id=1", one=True)
    old_budget = float(charter_before['approved_budget'])
    old_deadline = charter_before['deadline']
    result = approve_cr(pending['id'])
    assert result.get('success') == True
    charter_after = q("SELECT approved_budget,deadline FROM project_charter WHERE id=1", one=True)
    assert float(charter_after['approved_budget']) == old_budget + float(pending['cost_impact'])
    assert charter_after['deadline'] != old_deadline or int(pending['schedule_impact_days']) == 0
    # reset for other tests
    run("UPDATE change_requests SET status='Pending',approved_at=NULL WHERE id=?", (pending['id'],))
    run("UPDATE project_charter SET approved_budget=?,deadline=? WHERE id=1", (old_budget, old_deadline))
    if pending['requirement_id']:
        run("UPDATE requirements SET status='Proposed' WHERE id=?", (pending['requirement_id'],))

# ── TC09: Rejected CR changes nothing ─────────────────────────────────────
def test_TC09_cr_rejection_changes_nothing():
    pending = q("SELECT * FROM change_requests WHERE status='Pending' LIMIT 1", one=True)
    if not pending:
        pytest.skip("No pending CRs")
    charter_before = q("SELECT approved_budget,deadline FROM project_charter WHERE id=1", one=True)
    old_budget = float(charter_before['approved_budget'])
    old_deadline = charter_before['deadline']
    result = reject_cr(pending['id'])
    assert result.get('success') == True
    charter_after = q("SELECT approved_budget,deadline FROM project_charter WHERE id=1", one=True)
    assert float(charter_after['approved_budget']) == old_budget
    assert charter_after['deadline'] == old_deadline
    # reset
    run("UPDATE change_requests SET status='Pending' WHERE id=?", (pending['id'],))

# ── TC10: Input validation errors ─────────────────────────────────────────
def test_TC10_validation_errors(client):
    # empty charter fields
    resp = client.post('/initiation/charter', data={'project_name': '', 'approved_budget': '-100'})
    data = resp.get_json()
    assert resp.status_code == 400
    assert data.get('errors')

def test_TC10b_invalid_date(client):
    resp = client.post('/initiation/milestone', data={'name': 'Test', 'due_date': 'not-a-date'})
    data = resp.get_json()
    assert resp.status_code == 400

def test_TC10c_likelihood_out_of_range(client):
    resp = client.post('/quality/risk', data={
        'title': 'Test', 'description': 'Test', 'likelihood': '6', 'impact': '3'
    })
    data = resp.get_json()
    assert resp.status_code == 400

# ── TC11: Referential integrity blocks deletion ───────────────────────────
def test_TC11_referential_integrity(client):
    # Try deleting a requirement that has a WBS deliverable
    approved = q("SELECT r.id FROM requirements r JOIN wbs_deliverables d ON d.requirement_id=r.id WHERE r.status='Approved' LIMIT 1", one=True)
    if not approved:
        pytest.skip("No linked requirement found")
    resp = client.post('/scope/req', data={'id': str(approved['id']), '_action': 'delete'})
    data = resp.get_json()
    assert resp.status_code == 400
    assert data.get('errors')

# ── TC12: All pages load without error ────────────────────────────────────
def test_TC12_all_pages_load(client):
    routes = ['/?sd=2024-03-15','/initiation?sd=2024-03-15','/scope?sd=2024-03-15',
              '/schedule?sd=2024-03-15','/cost?sd=2024-03-15','/quality?sd=2024-03-15']
    for route in routes:
        resp = client.get(route)
        assert resp.status_code == 200, f"Route {route} returned {resp.status_code}"
