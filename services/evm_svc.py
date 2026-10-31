"""EVM calculations: PV, EV, AC, CPI, SPI, CV, SV, warnings."""
from datetime import datetime, date as date_type
from services.db import q


def _pd(s):
    try: return datetime.strptime(s, '%Y-%m-%d').date()
    except: return None


def _div(a, b):
    return None if (b is None or b == 0) else a / b


def compute_evm(status_date_str='2024-03-15'):
    sd = _pd(status_date_str) or date_type(2024, 3, 15)
    acts = q("SELECT * FROM activities")
    if not acts:
        return _zero()
    bac = sum(float(a['planned_cost']) for a in acts)
    charter = q("SELECT approved_budget FROM project_charter WHERE id=1", one=True)
    approved = float(charter['approved_budget']) if charter else bac
    # PV: time-phased planned cost up to status date
    pv = 0.0
    for a in acts:
        ps, pe = _pd(a['planned_start']), _pd(a['planned_end'])
        if not ps or not pe: continue
        total = (pe - ps).days + 1
        if total <= 0: continue
        pc = float(a['planned_cost'])
        if sd < ps: pv_pct = 0.0
        elif sd >= pe: pv_pct = 1.0
        else: pv_pct = ((sd - ps).days + 1) / total
        pv += pc * pv_pct
    # EV: planned_cost * %complete
    ev = sum(float(a['planned_cost']) * float(a['percent_complete']) / 100 for a in acts)
    # AC: actual cost entries up to status date
    row = q("SELECT COALESCE(SUM(amount),0) total FROM actual_cost_entries WHERE entry_date<=?",
            (sd.strftime('%Y-%m-%d'),), one=True)
    ac = float(row['total']) if row else 0.0

    cpi = _div(ev, ac)
    spi = _div(ev, pv)
    cv = ev - ac
    sv = ev - pv

    warnings = []
    if cpi is None:
        warnings.append({'lvl': 'info', 'msg': 'No actual costs recorded yet — CPI cannot be calculated.'})
    elif cpi < 0.90:
        warnings.append({'lvl': 'critical', 'msg': f'CRITICAL: CPI = {cpi:.3f} — severe cost overrun. Immediate action required.'})
    elif cpi < 1.00:
        warnings.append({'lvl': 'caution', 'msg': f'CAUTION: CPI = {cpi:.3f} — cost performance below baseline.'})

    if spi is None:
        warnings.append({'lvl': 'info', 'msg': 'PV is zero — SPI cannot be calculated.'})
    elif spi < 0.90:
        warnings.append({'lvl': 'critical', 'msg': f'CRITICAL: SPI = {spi:.3f} — significant schedule delay detected.'})
    elif spi < 1.00:
        warnings.append({'lvl': 'caution', 'msg': f'CAUTION: SPI = {spi:.3f} — schedule performance below baseline.'})

    if bac > approved:
        warnings.append({'lvl': 'critical', 'msg': f'CRITICAL: Total planned cost PKR {bac:,.0f} exceeds approved budget PKR {approved:,.0f}.'})
    if ac > approved:
        warnings.append({'lvl': 'critical', 'msg': f'CRITICAL: Actual cost PKR {ac:,.0f} has exceeded approved budget PKR {approved:,.0f}.'})
    elif ac > approved * 0.90:
        warnings.append({'lvl': 'caution', 'msg': f'CAUTION: Actual cost PKR {ac:,.0f} approaching approved budget PKR {approved:,.0f}.'})

    return {
        'sd': sd.strftime('%Y-%m-%d'), 'bac': round(bac, 2),
        'approved': round(approved, 2),
        'pv': round(pv, 2), 'ev': round(ev, 2), 'ac': round(ac, 2),
        'cpi': round(cpi, 4) if cpi is not None else None,
        'spi': round(spi, 4) if spi is not None else None,
        'cv': round(cv, 2), 'sv': round(sv, 2),
        'warnings': warnings,
    }


def activity_cost_summary():
    return q("""SELECT a.id,a.name,a.planned_cost,a.percent_complete,
                       a.planned_start,a.planned_end,
                       COALESCE(SUM(ace.amount),0) actual_cost
               FROM activities a
               LEFT JOIN actual_cost_entries ace ON ace.activity_id=a.id
               GROUP BY a.id ORDER BY a.planned_start""")


def scurve_data():
    """Monthly PV, EV, AC cumulative series for S-curve chart."""
    acts = q("SELECT * FROM activities")
    entries = q("SELECT * FROM actual_cost_entries ORDER BY entry_date")
    from datetime import timedelta
    if not acts: return []
    # collect all months
    months = set()
    for a in acts:
        ps, pe = _pd(a['planned_start']), _pd(a['planned_end'])
        if ps: months.add(ps.replace(day=1))
        if pe: months.add(pe.replace(day=1))
    if not months: return []
    months = sorted(months)
    result = []
    cum_pv = cum_ev = cum_ac = 0.0
    for m in months:
        # last day of month
        if m.month == 12: eom = m.replace(year=m.year+1, month=1, day=1) - timedelta(days=1)
        else: eom = m.replace(month=m.month+1, day=1) - timedelta(days=1)
        # PV: time-phased to end of this month
        pv = 0.0
        for a in acts:
            ps, pe = _pd(a['planned_start']), _pd(a['planned_end'])
            if not ps or not pe: continue
            total = (pe - ps).days + 1
            if total <= 0: continue
            pc = float(a['planned_cost'])
            if eom < ps: frac = 0.0
            elif eom >= pe: frac = 1.0
            else: frac = ((eom - ps).days + 1) / total
            pv += pc * frac
        # EV and AC up to end of month (using all data as proxy by eom date)
        ev = sum(float(a['planned_cost']) * float(a['percent_complete']) / 100 for a in acts)  # total EV static per seed
        ac = sum(float(e['amount']) for e in entries if _pd(e['entry_date']) and _pd(e['entry_date']) <= eom)
        result.append({'month': m.strftime('%b %Y'), 'pv': round(pv, 0), 'ev': round(ev, 0), 'ac': round(ac, 0)})
    return result


def _zero():
    return {'sd': '', 'bac': 0, 'approved': 0, 'pv': 0, 'ev': 0, 'ac': 0,
            'cpi': None, 'spi': None, 'cv': 0, 'sv': 0,
            'warnings': [{'lvl': 'info', 'msg': 'No activities found.'}]}
