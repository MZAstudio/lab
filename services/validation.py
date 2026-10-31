"""Server-side validation helpers."""
from datetime import datetime


def required(v, field):
    if not v or (isinstance(v, str) and not v.strip()):
        return f'{field} is required.'

def date_fmt(v, field='Date'):
    if not v or not v.strip(): return f'{field} is required.'
    try: datetime.strptime(v.strip(), '%Y-%m-%d'); return None
    except: return f'{field} must be YYYY-MM-DD.'

def positive_num(v, field, allow_zero=True):
    try:
        f = float(v)
        if allow_zero and f < 0: return f'{field} must be ≥ 0.'
        if not allow_zero and f <= 0: return f'{field} must be > 0.'
    except: return f'{field} must be a number.'

def int_range(v, field, lo, hi):
    try:
        i = int(v)
        if i < lo or i > hi: return f'{field} must be {lo}–{hi}.'
    except: return f'{field} must be an integer.'

def end_after_start(s, e):
    try:
        if datetime.strptime(e, '%Y-%m-%d') < datetime.strptime(s, '%Y-%m-%d'):
            return 'End date must be ≥ start date.'
    except: pass

def errs(*results):
    return [r for r in results if r]
