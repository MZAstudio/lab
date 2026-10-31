"""Smart Healthcare Project Management System — Flask Application."""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from services.db import init_db, q, run, qd, get_db
from services.schedule_svc import (get_activities, get_deps, detect_circular,
                                    forward_pass, get_delayed, projected_deadline)
from services.evm_svc import compute_evm, activity_cost_summary, scurve_data
from services.cr_svc import approve_cr, reject_cr, cr_preview
from services.validation import required, date_fmt, positive_num, int_range, end_after_start, errs

app = Flask(__name__)
app.secret_key = 'hpm_2024_secret'

# ── Global helpers ────────────────────────────────────────────────────────────
def _kpi(sd='2024-03-15'):
    charter = q("SELECT * FROM project_charter WHERE id=1", one=True)
    acts = get_activities()
    evm = compute_evm(sd)
    total = len(acts)
    prog = sum(float(a['percent_complete']) for a in acts) / total if total else 0
    planned = sum(float(a['planned_cost']) for a in acts)
    pd = projected_deadline(sd)
    return {
        'approved_budget': float(charter['approved_budget']) if charter else 0,
        'planned_cost': planned,
        'actual_cost': evm['ac'],
        'progress': round(prog, 1),
        'deadline': charter['deadline'] if charter else '—',
        'projected_finish': pd.strftime('%Y-%m-%d') if pd else '—',
        'cpi': evm['cpi'], 'spi': evm['spi'],
        'evm': evm,
    }

def _health(kpi):
    c, s = kpi.get('cpi'), kpi.get('spi')
    charter = q("SELECT deadline FROM project_charter WHERE id=1", one=True)
    pd = kpi.get('projected_finish','')
    missed = charter and pd and pd > charter['deadline']
    if missed or (c and c < 0.90) or (s and s < 0.90):
        return 'Critical'
    if (c and c < 1.0) or (s and s < 1.0):
        return 'At Risk'
    return 'On Track'

# ── Overview ──────────────────────────────────────────────────────────────────
@app.route('/', methods=['GET'])
def overview():
    sd = request.args.get('sd', '2024-03-15')
    try:
        kpi = _kpi(sd)
        charter = q("SELECT * FROM project_charter WHERE id=1", one=True)
        pending_cr = q("SELECT * FROM change_requests WHERE status='Pending' ORDER BY created_at DESC")
        delayed = get_delayed(sd)
        crit_defects = q("SELECT d.*,tm.name aname FROM defects d LEFT JOIN team_members tm ON d.assigned_to=tm.id WHERE d.severity='Critical' AND d.status NOT IN ('Resolved','Closed')")
        milestones = q("SELECT * FROM milestones ORDER BY due_date")
        health = _health(kpi)
        return render_template('overview.html', sd=sd, kpi=kpi, charter=charter,
                               pending_cr=pending_cr, delayed=delayed,
                               crit_defects=crit_defects, milestones=milestones,
                               health=health, tab='overview')
    except Exception as e:
        traceback.print_exc()
        return render_template('error.html', err=str(e))

# ── Initiation ────────────────────────────────────────────────────────────────
@app.route('/initiation', methods=['GET'])
def initiation():
    sd = request.args.get('sd', '2024-03-15')
    charter = q("SELECT * FROM project_charter WHERE id=1", one=True)
    plan = q("SELECT * FROM project_management_plan WHERE id=1", one=True)
    status = q("SELECT * FROM project_status WHERE id=1", one=True)
    milestones = q("SELECT * FROM milestones ORDER BY due_date")
    responsibilities = q("SELECT * FROM responsibilities ORDER BY role")
    closures = q("SELECT * FROM closure_records ORDER BY closure_date DESC")
    team = q("SELECT * FROM team_members ORDER BY name")
    acts = get_activities()
    planned_total = sum(float(a['planned_cost']) for a in acts)
    approved_reqs = q("SELECT * FROM requirements WHERE status='Approved' ORDER BY priority")
    kpi = _kpi(sd)
    health = _health(kpi)
    return render_template('initiation.html', sd=sd, charter=charter, plan=plan,
                           status=status, milestones=milestones,
                           responsibilities=responsibilities, closures=closures,
                           team=team, planned_total=planned_total,
                           approved_reqs=approved_reqs, acts_count=len(acts),
                           kpi=kpi, health=health, tab='initiation')

@app.route('/initiation/charter', methods=['POST'])
def save_charter():
    f = request.form
    es = errs(
        required(f.get('project_name'), 'Project name'),
        required(f.get('objectives'), 'Objectives'),
        required(f.get('stakeholders'), 'Stakeholders'),
        required(f.get('in_scope'), 'In-scope'),
        required(f.get('out_scope'), 'Out-of-scope'),
        positive_num(f.get('approved_budget'), 'Budget', allow_zero=False),
        date_fmt(f.get('start_date'), 'Start date'),
        date_fmt(f.get('deadline'), 'Deadline'),
    )
    if f.get('start_date') and f.get('deadline'):
        e = end_after_start(f['start_date'], f['deadline'])
        if e: es.append(e)
    if es: return jsonify({'errors': es}), 400
    existing = q("SELECT id FROM project_charter WHERE id=1", one=True)
    if existing:
        run("""UPDATE project_charter SET project_name=?,objectives=?,stakeholders=?,
               in_scope=?,out_scope=?,approved_budget=?,start_date=?,deadline=?,updated_at=datetime('now') WHERE id=1""",
            (f['project_name'],f['objectives'],f['stakeholders'],f['in_scope'],
             f['out_scope'],float(f['approved_budget']),f['start_date'],f['deadline']))
    else:
        run("""INSERT INTO project_charter(id,project_name,objectives,stakeholders,in_scope,out_scope,approved_budget,start_date,deadline)
               VALUES(1,?,?,?,?,?,?,?,?)""",
            (f['project_name'],f['objectives'],f['stakeholders'],f['in_scope'],
             f['out_scope'],float(f['approved_budget']),f['start_date'],f['deadline']))
    return jsonify({'ok': True, 'msg': 'Charter saved.'})

@app.route('/initiation/plan', methods=['POST'])
def save_plan():
    f = request.form
    es = errs(required(f.get('scope_description'),'Scope description'),
              required(f.get('quality_standards'),'Quality standards'))
    if es: return jsonify({'errors': es}), 400
    if q("SELECT id FROM project_management_plan WHERE id=1", one=True):
        run("UPDATE project_management_plan SET scope_description=?,quality_standards=?,notes=?,updated_at=datetime('now') WHERE id=1",
            (f['scope_description'],f['quality_standards'],f.get('notes','')))
    else:
        run("INSERT INTO project_management_plan(id,scope_description,quality_standards,notes) VALUES(1,?,?,?)",
            (f['scope_description'],f['quality_standards'],f.get('notes','')))
    return jsonify({'ok': True, 'msg': 'Plan saved.'})

@app.route('/initiation/status', methods=['POST'])
def save_status():
    f = request.form
    es = errs(required(f.get('status'),'Status'), date_fmt(f.get('status_date'),'Status date'))
    if es: return jsonify({'errors': es}), 400
    if q("SELECT id FROM project_status WHERE id=1", one=True):
        run("UPDATE project_status SET status=?,status_date=?,notes=? WHERE id=1",
            (f['status'],f['status_date'],f.get('notes','')))
    else:
        run("INSERT INTO project_status(id,status,status_date,notes) VALUES(1,?,?,?)",
            (f['status'],f['status_date'],f.get('notes','')))
    return jsonify({'ok': True, 'msg': 'Status updated.'})

@app.route('/initiation/milestone', methods=['POST'])
def save_milestone():
    f = request.form
    action = f.get('_action','add')
    if action == 'delete':
        mid = f.get('id')
        run("DELETE FROM milestones WHERE id=?", (mid,))
        return jsonify({'ok': True, 'msg': 'Milestone deleted.'})
    es = errs(required(f.get('name'),'Name'), date_fmt(f.get('due_date'),'Due date'))
    if es: return jsonify({'errors': es}), 400
    mid = f.get('id')
    if mid:
        run("UPDATE milestones SET name=?,due_date=?,status=? WHERE id=?",
            (f['name'],f['due_date'],f.get('status','Pending'),mid))
    else:
        dup = q("SELECT id FROM milestones WHERE name=?", (f['name'],), one=True)
        if dup: return jsonify({'errors': ['Milestone name already exists.']}), 400
        run("INSERT INTO milestones(name,due_date,status) VALUES(?,?,?)",
            (f['name'],f['due_date'],f.get('status','Pending')))
    return jsonify({'ok': True, 'msg': 'Milestone saved.'})

@app.route('/initiation/responsibility', methods=['POST'])
def save_responsibility():
    f = request.form
    if f.get('_action') == 'delete':
        run("DELETE FROM responsibilities WHERE id=?", (f.get('id'),))
        return jsonify({'ok': True, 'msg': 'Deleted.'})
    es = errs(required(f.get('person_name'),'Name'),required(f.get('role'),'Role'),
              required(f.get('responsibility'),'Responsibility'))
    if es: return jsonify({'errors': es}), 400
    rid = f.get('id')
    if rid:
        run("UPDATE responsibilities SET person_name=?,role=?,responsibility=? WHERE id=?",
            (f['person_name'],f['role'],f['responsibility'],rid))
    else:
        run("INSERT INTO responsibilities(person_name,role,responsibility) VALUES(?,?,?)",
            (f['person_name'],f['role'],f['responsibility']))
    return jsonify({'ok': True, 'msg': 'Saved.'})

@app.route('/initiation/closure', methods=['POST'])
def save_closure():
    f = request.form
    if f.get('_action') == 'delete':
        run("DELETE FROM closure_records WHERE id=?", (f.get('id'),))
        return jsonify({'ok': True, 'msg': 'Deleted.'})
    es = errs(date_fmt(f.get('closure_date'),'Closure date'),
              required(f.get('final_notes'),'Final notes'),
              required(f.get('lessons_learned'),'Lessons learned'))
    if es: return jsonify({'errors': es}), 400
    cid = f.get('id')
    if cid:
        run("UPDATE closure_records SET closure_date=?,final_notes=?,lessons_learned=?,closure_status=? WHERE id=?",
            (f['closure_date'],f['final_notes'],f['lessons_learned'],f.get('closure_status','Open'),cid))
    else:
        run("INSERT INTO closure_records(closure_date,final_notes,lessons_learned,closure_status) VALUES(?,?,?,?)",
            (f['closure_date'],f['final_notes'],f['lessons_learned'],f.get('closure_status','Open')))
    return jsonify({'ok': True, 'msg': 'Saved.'})

# ── Scope & WBS ───────────────────────────────────────────────────────────────
@app.route('/scope')
def scope():
    sd = request.args.get('sd', '2024-03-15')
    reqs = q("SELECT * FROM requirements ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, status")
    deliverables = q("""SELECT d.*,r.title req_title,r.status req_status
                        FROM wbs_deliverables d LEFT JOIN requirements r ON d.requirement_id=r.id ORDER BY d.id""")
    wps = q("SELECT * FROM wbs_work_packages ORDER BY deliverable_id,id")
    crs = q("""SELECT cr.*,r.title req_title FROM change_requests cr
               LEFT JOIN requirements r ON cr.requirement_id=r.id ORDER BY cr.created_at DESC""")
    approved_reqs = q("SELECT * FROM requirements WHERE status='Approved' ORDER BY title")
    kpi = _kpi(sd)
    health = _health(kpi)
    wp_map = {}
    for wp in wps: wp_map.setdefault(wp['deliverable_id'], []).append(dict(wp))
    tree = [{'d': dict(d), 'wps': wp_map.get(d['id'], [])} for d in deliverables]
    return render_template('scope.html', sd=sd, reqs=reqs, tree=tree,
                           crs=crs, approved_reqs=approved_reqs,
                           kpi=kpi, health=health, tab='scope')

@app.route('/scope/req', methods=['POST'])
def save_req():
    f = request.form
    action = f.get('_action','add')
    if action == 'delete':
        rid = f.get('id')
        for tbl,col in [('wbs_deliverables','requirement_id'),('defects','requirement_id'),('change_requests','requirement_id')]:
            if q(f"SELECT id FROM {tbl} WHERE {col}=?", (rid,), one=True):
                return jsonify({'errors': [f'Cannot delete: requirement is referenced by {tbl}.']}), 400
        run("DELETE FROM requirements WHERE id=?", (rid,))
        return jsonify({'ok': True, 'msg': 'Requirement deleted.'})
    if action in ('approve','reject'):
        run("UPDATE requirements SET status=? WHERE id=?",
            ('Approved' if action=='approve' else 'Rejected', f.get('id')))
        return jsonify({'ok': True, 'msg': f'Requirement {action}d.'})
    es = errs(required(f.get('title'),'Title'), required(f.get('description'),'Description'))
    if es: return jsonify({'errors': es}), 400
    rid = f.get('id')
    if rid:
        dup = q("SELECT id FROM requirements WHERE title=? AND id!=?", (f['title'],rid), one=True)
        if dup: return jsonify({'errors': ['Title already exists.']}), 400
        run("UPDATE requirements SET title=?,description=?,priority=?,status=? WHERE id=?",
            (f['title'],f['description'],f.get('priority','Medium'),f.get('status','Proposed'),rid))
    else:
        dup = q("SELECT id FROM requirements WHERE title=?", (f['title'],), one=True)
        if dup: return jsonify({'errors': ['Title already exists.']}), 400
        run("INSERT INTO requirements(title,description,priority,status,source) VALUES(?,?,?,?,?)",
            (f['title'],f['description'],f.get('priority','Medium'),'Proposed',f.get('source','Initial')))
    return jsonify({'ok': True, 'msg': 'Requirement saved.'})

@app.route('/scope/deliverable', methods=['POST'])
def save_deliverable():
    f = request.form
    if f.get('_action') == 'delete':
        did = f.get('id')
        wps = q("SELECT id FROM wbs_work_packages WHERE deliverable_id=?", (did,))
        for wp in wps:
            if q("SELECT id FROM activities WHERE work_package_id=?", (wp['id'],), one=True):
                return jsonify({'errors': ['Cannot delete: activities linked to work packages in this deliverable.']}), 400
        if q("SELECT id FROM defects WHERE deliverable_id=?", (did,), one=True):
            return jsonify({'errors': ['Cannot delete: defects reference this deliverable.']}), 400
        run("DELETE FROM wbs_deliverables WHERE id=?", (did,))
        return jsonify({'ok': True, 'msg': 'Deliverable deleted.'})
    es = errs(required(f.get('name'),'Name'))
    if es: return jsonify({'errors': es}), 400
    req_id = f.get('requirement_id') or None
    if req_id:
        r = q("SELECT status FROM requirements WHERE id=?", (req_id,), one=True)
        if not r or r['status'] != 'Approved':
            return jsonify({'errors': ['Only Approved requirements can be linked to WBS deliverables.']}), 400
    did = f.get('id')
    if did:
        dup = q("SELECT id FROM wbs_deliverables WHERE name=? AND id!=?", (f['name'],did), one=True)
        if dup: return jsonify({'errors': ['Name already exists.']}), 400
        run("UPDATE wbs_deliverables SET name=?,description=?,requirement_id=? WHERE id=?",
            (f['name'],f.get('description',''),req_id,did))
    else:
        dup = q("SELECT id FROM wbs_deliverables WHERE name=?", (f['name'],), one=True)
        if dup: return jsonify({'errors': ['Name already exists.']}), 400
        run("INSERT INTO wbs_deliverables(name,description,requirement_id) VALUES(?,?,?)",
            (f['name'],f.get('description',''),req_id))
    return jsonify({'ok': True, 'msg': 'Deliverable saved.'})

@app.route('/scope/workpackage', methods=['POST'])
def save_wp():
    f = request.form
    if f.get('_action') == 'delete':
        wid = f.get('id')
        if q("SELECT id FROM activities WHERE work_package_id=?", (wid,), one=True):
            return jsonify({'errors': ['Cannot delete: activities linked to this work package.']}), 400
        run("DELETE FROM wbs_work_packages WHERE id=?", (wid,))
        return jsonify({'ok': True, 'msg': 'Work package deleted.'})
    es = errs(required(f.get('name'),'Name'), required(f.get('deliverable_id'),'Deliverable'))
    if es: return jsonify({'errors': es}), 400
    wid = f.get('id')
    if wid:
        run("UPDATE wbs_work_packages SET name=?,description=?,deliverable_id=? WHERE id=?",
            (f['name'],f.get('description',''),f['deliverable_id'],wid))
    else:
        run("INSERT INTO wbs_work_packages(name,description,deliverable_id) VALUES(?,?,?)",
            (f['name'],f.get('description',''),f['deliverable_id']))
    return jsonify({'ok': True, 'msg': 'Work package saved.'})

@app.route('/scope/cr', methods=['POST'])
def save_cr():
    f = request.form
    action = f.get('_action','add')
    if action == 'approve':
        r = approve_cr(int(f.get('id')))
        if 'error' in r: return jsonify({'errors': [r['error']]}), 400
        return jsonify({'ok': True, 'msg': f'CR approved.', 'result': r})
    if action == 'reject':
        r = reject_cr(int(f.get('id')))
        if 'error' in r: return jsonify({'errors': [r['error']]}), 400
        return jsonify({'ok': True, 'msg': 'CR rejected. Nothing changed.'})
    if action == 'delete':
        cr = q("SELECT status FROM change_requests WHERE id=?", (f.get('id'),), one=True)
        if cr and cr['status'] == 'Approved':
            return jsonify({'errors': ['Cannot delete an approved CR.']}), 400
        run("DELETE FROM change_requests WHERE id=?", (f.get('id'),))
        return jsonify({'ok': True, 'msg': 'Deleted.'})
    es = errs(required(f.get('title'),'Title'), required(f.get('description'),'Description'),
              required(f.get('justification'),'Justification'),
              positive_num(f.get('cost_impact'),'Cost impact'),
              int_range(f.get('schedule_impact_days'),'Schedule impact days',0,365))
    if es: return jsonify({'errors': es}), 400
    req_id = f.get('requirement_id') or None
    run("""INSERT INTO change_requests(title,description,justification,cost_impact,schedule_impact_days,status,requirement_id)
           VALUES(?,?,?,?,?,'Pending',?)""",
        (f['title'],f['description'],f['justification'],
         float(f['cost_impact']),int(f['schedule_impact_days']),req_id))
    return jsonify({'ok': True, 'msg': 'Change request submitted.'})

@app.route('/api/cr_preview/<int:cid>')
def api_cr_preview(cid):
    data = cr_preview(cid)
    if not data: return jsonify({'error': 'Not found'}), 404
    return jsonify(data)

# ── Schedule ──────────────────────────────────────────────────────────────────
@app.route('/schedule')
def schedule():
    sd = request.args.get('sd', '2024-03-15')
    acts = get_activities()
    deps = get_deps()
    fp = forward_pass(acts, deps)
    delayed = get_delayed(sd)
    delayed_ids = {d['id'] for d in delayed}
    pd = projected_deadline(sd)
    charter = q("SELECT start_date,deadline FROM project_charter WHERE id=1", one=True)
    wps = qd("""SELECT wp.id,wp.name,d.name dname FROM wbs_work_packages wp
                JOIN wbs_deliverables d ON wp.deliverable_id=d.id ORDER BY d.name,wp.name""")
    team = qd("SELECT * FROM team_members ORDER BY name")
    milestones = qd("SELECT * FROM milestones ORDER BY due_date")
    gantt = []
    for a in acts:
        fe = fp.get(a['id'])
        gantt.append({
            'id': a['id'], 'name': a['name'],
            'planned_start': a['planned_start'], 'planned_end': a['planned_end'],
            'es': fe['es'].strftime('%Y-%m-%d') if fe else a['planned_start'],
            'ee': fe['ee'].strftime('%Y-%m-%d') if fe else a['planned_end'],
            'pct': float(a['percent_complete']),
            'delayed': a['id'] in delayed_ids,
            'preds': deps.get(a['id'], []),
            'member': a['member_name'], 'dur': a['estimated_duration']
        })
    kpi = _kpi(sd)
    health = _health(kpi)
    return render_template('schedule.html', sd=sd, acts=acts, deps=deps,
                           gantt=gantt, milestones=milestones,
                           delayed=delayed, delayed_ids=list(delayed_ids),
                           projected_deadline=pd, charter=charter,
                           wps=wps, team=team,
                           kpi=kpi, health=health, tab='schedule')

@app.route('/schedule/activity', methods=['POST'])
def save_activity():
    f = request.form
    action = f.get('_action','add')
    if action == 'delete':
        aid = f.get('id')
        if q("SELECT id FROM actual_cost_entries WHERE activity_id=?", (aid,), one=True):
            return jsonify({'errors': ['Cannot delete: cost entries exist for this activity.']}), 400
        run("DELETE FROM activities WHERE id=?", (aid,))
        return jsonify({'ok': True, 'msg': 'Activity deleted.'})
    es = errs(required(f.get('name'),'Name'),
              date_fmt(f.get('planned_start'),'Planned start'),
              date_fmt(f.get('planned_end'),'Planned end'),
              int_range(f.get('estimated_duration'),'Duration',1,999),
              positive_num(f.get('planned_cost'),'Planned cost'),
              int_range(f.get('percent_complete'),'% complete',0,100))
    if f.get('planned_start') and f.get('planned_end'):
        e = end_after_start(f['planned_start'],f['planned_end'])
        if e: es.append(e)
    if es: return jsonify({'errors': es}), 400
    aid = f.get('id')
    wp = f.get('work_package_id') or None
    mb = f.get('assigned_member_id') or None
    if aid:
        run("""UPDATE activities SET percent_complete=?,actual_start=?,actual_end=?,planned_cost=? WHERE id=?""",
            (float(f.get('percent_complete',0)), f.get('actual_start') or None,
             f.get('actual_end') or None, float(f.get('planned_cost',0)), aid))
        return jsonify({'ok': True, 'msg': 'Activity updated.'})
    dup = q("SELECT id FROM activities WHERE name=?", (f['name'],), one=True)
    if dup: return jsonify({'errors': ['Activity name already exists.']}), 400
    new_id = run("""INSERT INTO activities(name,work_package_id,assigned_member_id,estimated_duration,
                    planned_start,planned_end,actual_start,percent_complete,planned_cost)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                 (f['name'],wp,mb,int(f['estimated_duration']),
                  f['planned_start'],f['planned_end'],f.get('actual_start') or None,
                  float(f.get('percent_complete',0)),float(f.get('planned_cost',0))))
    preds = [int(p) for p in request.form.getlist('predecessors') if p]
    if preds:
        acts = get_activities()
        deps = get_deps()
        if detect_circular(acts, deps, new_id, preds):
            run("DELETE FROM activities WHERE id=?", (new_id,))
            return jsonify({'errors': ['Circular dependency detected. Activity not saved.']}), 400
        for p in preds:
            try: run("INSERT INTO activity_dependencies(activity_id,predecessor_id) VALUES(?,?)", (new_id, p))
            except: pass
    return jsonify({'ok': True, 'msg': 'Activity added.'})

@app.route('/schedule/dependency', methods=['POST'])
def save_dep():
    f = request.form
    if f.get('_action') == 'delete':
        run("DELETE FROM activity_dependencies WHERE activity_id=? AND predecessor_id=?",
            (f.get('act_id'), f.get('pred_id')))
        return jsonify({'ok': True, 'msg': 'Dependency removed.'})
    aid, pid = int(f.get('act_id',0)), int(f.get('pred_id',0))
    if aid == pid: return jsonify({'errors': ['Activity cannot depend on itself.']}), 400
    acts = get_activities()
    deps = get_deps()
    if detect_circular(acts, deps, aid, [pid]):
        return jsonify({'errors': ['Circular dependency detected.']}), 400
    try:
        run("INSERT INTO activity_dependencies(activity_id,predecessor_id) VALUES(?,?)", (aid, pid))
        return jsonify({'ok': True, 'msg': 'Dependency added.'})
    except Exception:
        return jsonify({'errors': ['Dependency already exists.']}), 400

# ── Cost & EVM ────────────────────────────────────────────────────────────────
@app.route('/cost')
def cost():
    sd = request.args.get('sd', '2024-03-15')
    evm = compute_evm(sd)
    summary = activity_cost_summary()
    entries = q("""SELECT ace.*,a.name aname FROM actual_cost_entries ace
                   JOIN activities a ON ace.activity_id=a.id ORDER BY ace.entry_date DESC""")
    acts = q("SELECT id,name FROM activities ORDER BY planned_start")
    sc = scurve_data()
    kpi = _kpi(sd)
    health = _health(kpi)
    return render_template('cost.html', sd=sd, evm=evm, summary=summary,
                           entries=entries, acts=acts, scurve=sc,
                           kpi=kpi, health=health, tab='cost')

@app.route('/cost/entry', methods=['POST'])
def save_cost_entry():
    f = request.form
    if f.get('_action') == 'delete':
        run("DELETE FROM actual_cost_entries WHERE id=?", (f.get('id'),))
        return jsonify({'ok': True, 'msg': 'Deleted.'})
    es = errs(required(f.get('activity_id'),'Activity'),
              positive_num(f.get('amount'),'Amount',allow_zero=False),
              date_fmt(f.get('entry_date'),'Entry date'))
    if es: return jsonify({'errors': es}), 400
    if not q("SELECT id FROM activities WHERE id=?", (f['activity_id'],), one=True):
        return jsonify({'errors': ['Activity not found.']}), 400
    run("INSERT INTO actual_cost_entries(activity_id,amount,entry_date,description) VALUES(?,?,?,?)",
        (int(f['activity_id']),float(f['amount']),f['entry_date'],f.get('description','')))
    return jsonify({'ok': True, 'msg': 'Cost entry recorded.'})

# ── Quality & Risk ────────────────────────────────────────────────────────────
@app.route('/quality')
def quality():
    sd = request.args.get('sd', '2024-03-15')
    sev_f = request.args.get('sev','')
    status_f = request.args.get('st','')
    sql = """SELECT d.*,tm.name aname,del.name dname FROM defects d
             LEFT JOIN team_members tm ON d.assigned_to=tm.id
             LEFT JOIN wbs_deliverables del ON d.deliverable_id=del.id"""
    params = []
    conds = []
    if sev_f: conds.append("d.severity=?"); params.append(sev_f)
    if status_f: conds.append("d.status=?"); params.append(status_f)
    if conds: sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY CASE d.severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END"
    defects = q(sql, params)
    checklists = q("""SELECT qc.*,d.name dname FROM quality_checklists qc
                      JOIN wbs_deliverables d ON qc.deliverable_id=d.id ORDER BY d.name,qc.item_name""")
    inspections = q("""SELECT ir.*,qc.item_name,d.name dname FROM inspection_results ir
                       JOIN quality_checklists qc ON ir.checklist_id=qc.id
                       JOIN wbs_deliverables d ON qc.deliverable_id=d.id ORDER BY ir.inspection_date DESC""")
    risks = q("SELECT * FROM risks ORDER BY likelihood*impact DESC")
    pdpc = q("""SELECT p.*,r.title rtitle FROM pdpc_actions p
                JOIN risks r ON p.risk_id=r.id ORDER BY r.likelihood*r.impact DESC""")
    team = q("SELECT * FROM team_members ORDER BY name")
    deliverables = q("SELECT * FROM wbs_deliverables ORDER BY name")
    reqs = q("SELECT id,title FROM requirements WHERE status='Approved' ORDER BY title")
    # kanban
    kanban = {'Open':[],'In Progress':[],'Resolved':[],'Closed':[]}
    for d in defects:
        kanban.setdefault(d['status'],[]).append(dict(d))
    # checklist per deliverable
    cl_map = {}
    for cl in checklists:
        cl_map.setdefault(cl['deliverable_id'],[]).append(dict(cl))
    insp_map = {}
    for ir in inspections:
        insp_map.setdefault(ir['checklist_id'],[]).append(dict(ir))
    # risk matrix 5x5
    risk_matrix = [[[] for _ in range(5)] for _ in range(5)]
    for r in risks:
        l, i = int(r['likelihood'])-1, int(r['impact'])-1
        risk_matrix[l][i].append(dict(r))
    # pdpc tree
    pdpc_tree = {}
    for p in pdpc:
        pdpc_tree.setdefault(p['risk_id'],{'title':p['rtitle'],'actions':[]})['actions'].append(dict(p))
    kpi = _kpi(sd)
    health = _health(kpi)
    return render_template('quality.html', sd=sd,
                           defects=defects, kanban=kanban,
                           checklists=checklists, cl_map=cl_map, insp_map=insp_map,
                           risks=risks, risk_matrix=risk_matrix,
                           pdpc_tree=pdpc_tree,
                           team=team, deliverables=deliverables, reqs=reqs,
                           sev_f=sev_f, status_f=status_f,
                           kpi=kpi, health=health, tab='quality')

@app.route('/quality/defect', methods=['POST'])
def save_defect():
    f = request.form
    if f.get('_action') == 'delete':
        run("DELETE FROM defects WHERE id=?", (f.get('id'),))
        return jsonify({'ok': True, 'msg': 'Deleted.'})
    if f.get('_action') == 'status':
        run("UPDATE defects SET status=? WHERE id=?", (f.get('status'), f.get('id')))
        return jsonify({'ok': True, 'msg': 'Status updated.'})
    es = errs(required(f.get('title'),'Title'), required(f.get('description'),'Description'),
              required(f.get('severity'),'Severity'))
    if es: return jsonify({'errors': es}), 400
    did = f.get('id')
    kw = dict(title=f['title'],desc=f['description'],sev=f['severity'],
              asgn=f.get('assigned_to') or None,
              deliv=f.get('deliverable_id') or None,
              req=f.get('requirement_id') or None,
              st=f.get('status','Open'))
    if did:
        run("UPDATE defects SET title=?,description=?,severity=?,assigned_to=?,deliverable_id=?,requirement_id=?,status=? WHERE id=?",
            (kw['title'],kw['desc'],kw['sev'],kw['asgn'],kw['deliv'],kw['req'],kw['st'],did))
    else:
        run("INSERT INTO defects(title,description,severity,assigned_to,deliverable_id,requirement_id,status) VALUES(?,?,?,?,?,?,?)",
            (kw['title'],kw['desc'],kw['sev'],kw['asgn'],kw['deliv'],kw['req'],kw['st']))
    return jsonify({'ok': True, 'msg': 'Defect saved.'})

@app.route('/quality/checklist', methods=['POST'])
def save_checklist():
    f = request.form
    if f.get('_action') == 'delete':
        cid = f.get('id')
        if q("SELECT id FROM inspection_results WHERE checklist_id=?", (cid,), one=True):
            return jsonify({'errors': ['Cannot delete: inspection results exist.']}), 400
        run("DELETE FROM quality_checklists WHERE id=?", (cid,))
        return jsonify({'ok': True, 'msg': 'Deleted.'})
    es = errs(required(f.get('deliverable_id'),'Deliverable'), required(f.get('item_name'),'Item name'))
    if es: return jsonify({'errors': es}), 400
    cid = f.get('id')
    if cid:
        run("UPDATE quality_checklists SET deliverable_id=?,item_name=?,description=? WHERE id=?",
            (f['deliverable_id'],f['item_name'],f.get('description',''),cid))
    else:
        run("INSERT INTO quality_checklists(deliverable_id,item_name,description) VALUES(?,?,?)",
            (f['deliverable_id'],f['item_name'],f.get('description','')))
    return jsonify({'ok': True, 'msg': 'Saved.'})

@app.route('/quality/inspection', methods=['POST'])
def save_inspection():
    f = request.form
    if f.get('_action') == 'delete':
        run("DELETE FROM inspection_results WHERE id=?", (f.get('id'),))
        return jsonify({'ok': True, 'msg': 'Deleted.'})
    es = errs(required(f.get('checklist_id'),'Checklist item'),
              required(f.get('result'),'Result'),
              date_fmt(f.get('inspection_date'),'Inspection date'),
              required(f.get('inspector'),'Inspector'))
    if es: return jsonify({'errors': es}), 400
    iid = f.get('id')
    if iid:
        run("UPDATE inspection_results SET checklist_id=?,result=?,inspection_date=?,inspector=?,remarks=? WHERE id=?",
            (f['checklist_id'],f['result'],f['inspection_date'],f['inspector'],f.get('remarks',''),iid))
    else:
        run("INSERT INTO inspection_results(checklist_id,result,inspection_date,inspector,remarks) VALUES(?,?,?,?,?)",
            (f['checklist_id'],f['result'],f['inspection_date'],f['inspector'],f.get('remarks','')))
    return jsonify({'ok': True, 'msg': 'Inspection result saved.'})

@app.route('/quality/risk', methods=['POST'])
def save_risk():
    f = request.form
    if f.get('_action') == 'delete':
        rid = f.get('id')
        if q("SELECT id FROM pdpc_actions WHERE risk_id=?", (rid,), one=True):
            return jsonify({'errors': ['Cannot delete: PDPC actions are linked.']}), 400
        run("DELETE FROM risks WHERE id=?", (rid,))
        return jsonify({'ok': True, 'msg': 'Risk deleted.'})
    es = errs(required(f.get('title'),'Title'), required(f.get('description'),'Description'),
              int_range(f.get('likelihood'),'Likelihood',1,5),
              int_range(f.get('impact'),'Impact',1,5))
    if es: return jsonify({'errors': es}), 400
    rid = f.get('id')
    if rid:
        run("UPDATE risks SET title=?,description=?,likelihood=?,impact=?,category=?,status=? WHERE id=?",
            (f['title'],f['description'],int(f['likelihood']),int(f['impact']),
             f.get('category','General'),f.get('status','Open'),rid))
    else:
        run("INSERT INTO risks(title,description,likelihood,impact,category,status) VALUES(?,?,?,?,?,?)",
            (f['title'],f['description'],int(f['likelihood']),int(f['impact']),
             f.get('category','General'),f.get('status','Open')))
    return jsonify({'ok': True, 'msg': 'Risk saved.'})

@app.route('/quality/pdpc', methods=['POST'])
def save_pdpc():
    f = request.form
    if f.get('_action') == 'delete':
        run("DELETE FROM pdpc_actions WHERE id=?", (f.get('id'),))
        return jsonify({'ok': True, 'msg': 'Deleted.'})
    es = errs(required(f.get('risk_id'),'Risk'),
              required(f.get('potential_problem'),'Potential problem'),
              required(f.get('preventive_action'),'Preventive action'),
              required(f.get('corrective_action'),'Corrective action'))
    if es: return jsonify({'errors': es}), 400
    if not q("SELECT id FROM risks WHERE id=?", (f['risk_id'],), one=True):
        return jsonify({'errors': ['Risk not found.']}), 400
    pid = f.get('id')
    if pid:
        run("UPDATE pdpc_actions SET risk_id=?,potential_problem=?,preventive_action=?,corrective_action=? WHERE id=?",
            (f['risk_id'],f['potential_problem'],f['preventive_action'],f['corrective_action'],pid))
    else:
        run("INSERT INTO pdpc_actions(risk_id,potential_problem,preventive_action,corrective_action) VALUES(?,?,?,?)",
            (f['risk_id'],f['potential_problem'],f['preventive_action'],f['corrective_action']))
    return jsonify({'ok': True, 'msg': 'PDPC entry saved.'})

# ── Team (helper used by drawers) ─────────────────────────────────────────────
@app.route('/team/member', methods=['POST'])
def save_team():
    f = request.form
    if f.get('_action') == 'delete':
        tid = f.get('id')
        if q("SELECT id FROM activities WHERE assigned_member_id=?", (tid,), one=True):
            return jsonify({'errors': ['Cannot delete: member assigned to activities.']}), 400
        run("DELETE FROM team_members WHERE id=?", (tid,))
        return jsonify({'ok': True, 'msg': 'Deleted.'})
    es = errs(required(f.get('name'),'Name'), required(f.get('role'),'Role'))
    if es: return jsonify({'errors': es}), 400
    tid = f.get('id')
    if tid:
        run("UPDATE team_members SET name=?,role=? WHERE id=?", (f['name'],f['role'],tid))
    else:
        if q("SELECT id FROM team_members WHERE name=?", (f['name'],), one=True):
            return jsonify({'errors': ['Name already exists.']}), 400
        run("INSERT INTO team_members(name,role) VALUES(?,?)", (f['name'],f['role']))
    return jsonify({'ok': True, 'msg': 'Team member saved.'})

# ── Error handler ─────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', err='Page not found (404)'), 404

@app.errorhandler(500)
def server_err(e):
    return render_template('error.html', err=str(e)), 500

if __name__ == '__main__':
    init_db()
    print("DB ready. Starting at http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
