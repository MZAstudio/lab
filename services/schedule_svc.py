"""Schedule service: forward-pass, circular-dependency detection, delay impact."""
from datetime import datetime, timedelta, date as date_type
from collections import deque
from services.db import q


def _pd(s):
    if not s: return None
    for fmt in ('%Y-%m-%d',):
        try: return datetime.strptime(s, fmt).date()
        except: pass
    return None


def get_activities():
    return q("""SELECT a.*,tm.name member_name,wp.name wp_name
                FROM activities a
                LEFT JOIN team_members tm ON a.assigned_member_id=tm.id
                LEFT JOIN wbs_work_packages wp ON a.work_package_id=wp.id
                ORDER BY a.planned_start""")


def get_deps():
    """Returns {activity_id: [predecessor_id,...]}"""
    rows = q("SELECT activity_id,predecessor_id FROM activity_dependencies")
    d = {}
    for r in rows:
        d.setdefault(r['activity_id'], []).append(r['predecessor_id'])
    return d


def _successors(deps):
    """Reverse map: {pred_id: [successor_ids]}"""
    s = {}
    for aid, preds in deps.items():
        for p in preds:
            s.setdefault(p, []).append(aid)
    return s


def detect_circular(activities, deps, new_id=None, new_preds=None):
    """DFS cycle detection. Returns True if cycle found."""
    ids = {a['id'] for a in activities}
    succ = _successors(deps)
    if new_id and new_preds:
        for p in new_preds:
            succ.setdefault(p, []).append(new_id)
        ids.add(new_id)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in ids}
    def dfs(node):
        color[node] = GRAY
        for nb in succ.get(node, []):
            if nb not in color: continue
            if color[nb] == GRAY: return True
            if color[nb] == WHITE and dfs(nb): return True
        color[node] = BLACK
        return False
    for n in list(ids):
        if color.get(n, WHITE) == WHITE:
            if dfs(n): return True
    return False


def forward_pass(activities, deps):
    """Compute earliest start/end per activity.
    Returns {id: {'es': date, 'ee': date}}"""
    act_map = {a['id']: a for a in activities}
    in_deg = {a['id']: len(deps.get(a['id'], [])) for a in activities}
    succ = _successors(deps)
    queue = deque([aid for aid, d in in_deg.items() if d == 0])
    result = {}
    while queue:
        aid = queue.popleft()
        a = act_map[aid]
        ps = _pd(a['planned_start'])
        if not ps:
            continue
        preds = deps.get(aid, [])
        if preds:
            pred_ends = [result[p]['ee'] for p in preds if p in result and result[p]['ee']]
            if pred_ends:
                earliest = max(pred_ends) + timedelta(days=1)
                if earliest > ps:
                    ps = earliest
        dur = int(a['estimated_duration'])
        result[aid] = {'es': ps, 'ee': ps + timedelta(days=dur - 1)}
        for s in succ.get(aid, []):
            in_deg[s] -= 1
            if in_deg[s] == 0:
                queue.append(s)
    return result


def _all_successors(act_id, deps):
    succ = _successors(deps)
    visited, queue = set(), [act_id]
    while queue:
        node = queue.pop()
        for s in succ.get(node, []):
            if s not in visited:
                visited.add(s)
                queue.append(s)
    return visited


def get_delayed(status_date_str='2024-03-15'):
    sd = _pd(status_date_str) or date_type(2024, 3, 15)
    activities = get_activities()
    deps = get_deps()
    act_map = {a['id']: a for a in activities}
    delayed = []
    for a in activities:
        pe = _pd(a['planned_end'])
        ps = _pd(a['planned_start'])
        pct = float(a['percent_complete'])
        if not pe or not ps: continue
        is_delayed = False
        reason = ''
        days_late = 0
        if pe < sd and pct < 100:
            is_delayed = True
            days_late = (sd - pe).days
            reason = f"Past planned end ({a['planned_end']}) with {pct:.0f}% complete"
        elif ps <= sd <= pe:
            total = (pe - ps).days + 1
            elapsed = (sd - ps).days + 1
            expected = min(100, (elapsed / total) * 100) if total > 0 else 0
            if expected - pct > 15:
                is_delayed = True
                days_late = int((expected - pct) / 100 * int(a['estimated_duration']))
                reason = f"Behind plan: expected {expected:.0f}% but {pct:.0f}% complete"
        if is_delayed:
            succs = _all_successors(a['id'], deps)
            remaining = int(a['estimated_duration']) * (1 - pct / 100)
            proj_end = sd + timedelta(days=int(remaining))
            delayed.append({
                'id': a['id'], 'name': a['name'],
                'planned_end': a['planned_end'],
                'percent_complete': pct,
                'reason': reason, 'days_late': days_late,
                'projected_end': proj_end.strftime('%Y-%m-%d'),
                'affected_ids': list(succs),
                'affected_names': [act_map[s]['name'] for s in succs if s in act_map]
            })
    return delayed


def projected_deadline(status_date_str='2024-03-15'):
    sd = _pd(status_date_str) or date_type(2024, 3, 15)
    activities = get_activities()
    ends = []
    for a in activities:
        pct = float(a['percent_complete'])
        ps = _pd(a['planned_start'])
        dur = int(a['estimated_duration'])
        if pct >= 100:
            pe = _pd(a['planned_end']) or (ps + timedelta(days=dur - 1) if ps else sd)
        else:
            remaining = dur * (1 - pct / 100)
            start = _pd(a['actual_start']) or ps or sd
            pe = max(start, sd) + timedelta(days=int(remaining))
        if pe:
            ends.append(pe)
    return max(ends) if ends else None
