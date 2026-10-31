PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS project_charter (
    id INTEGER PRIMARY KEY,
    project_name TEXT NOT NULL,
    objectives TEXT NOT NULL,
    stakeholders TEXT NOT NULL,
    in_scope TEXT NOT NULL,
    out_scope TEXT NOT NULL,
    approved_budget REAL NOT NULL CHECK(approved_budget>=0),
    start_date TEXT NOT NULL,
    deadline TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project_management_plan (
    id INTEGER PRIMARY KEY,
    scope_description TEXT NOT NULL,
    quality_standards TEXT NOT NULL,
    notes TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project_status (
    id INTEGER PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'Active',
    status_date TEXT DEFAULT (date('now')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending'
        CHECK(status IN ('Pending','In Progress','Completed','Delayed'))
);

CREATE TABLE IF NOT EXISTS responsibilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_name TEXT NOT NULL,
    role TEXT NOT NULL,
    responsibility TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS closure_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    closure_date TEXT NOT NULL,
    final_notes TEXT NOT NULL,
    lessons_learned TEXT NOT NULL,
    closure_status TEXT NOT NULL DEFAULT 'Open'
        CHECK(closure_status IN ('Open','Closed','Archived'))
);

CREATE TABLE IF NOT EXISTS requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'Medium'
        CHECK(priority IN ('High','Medium','Low')),
    status TEXT NOT NULL DEFAULT 'Proposed'
        CHECK(status IN ('Proposed','Approved','Rejected')),
    source TEXT DEFAULT 'Initial',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS wbs_deliverables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    requirement_id INTEGER REFERENCES requirements(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS wbs_work_packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    deliverable_id INTEGER NOT NULL
        REFERENCES wbs_deliverables(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS change_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    justification TEXT NOT NULL,
    cost_impact REAL NOT NULL DEFAULT 0,
    schedule_impact_days INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Pending'
        CHECK(status IN ('Pending','Approved','Rejected')),
    requirement_id INTEGER REFERENCES requirements(id) ON DELETE SET NULL,
    approved_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    work_package_id INTEGER REFERENCES wbs_work_packages(id) ON DELETE SET NULL,
    assigned_member_id INTEGER REFERENCES team_members(id) ON DELETE SET NULL,
    estimated_duration INTEGER NOT NULL DEFAULT 1 CHECK(estimated_duration>0),
    planned_start TEXT NOT NULL,
    planned_end TEXT NOT NULL,
    actual_start TEXT,
    actual_end TEXT,
    percent_complete REAL NOT NULL DEFAULT 0
        CHECK(percent_complete>=0 AND percent_complete<=100),
    planned_cost REAL NOT NULL DEFAULT 0 CHECK(planned_cost>=0)
);

CREATE TABLE IF NOT EXISTS activity_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    predecessor_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    UNIQUE(activity_id, predecessor_id),
    CHECK(activity_id != predecessor_id)
);

CREATE TABLE IF NOT EXISTS actual_cost_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    amount REAL NOT NULL CHECK(amount>=0),
    entry_date TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS defects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('Critical','High','Medium','Low')),
    assigned_to INTEGER REFERENCES team_members(id) ON DELETE SET NULL,
    deliverable_id INTEGER REFERENCES wbs_deliverables(id) ON DELETE SET NULL,
    requirement_id INTEGER REFERENCES requirements(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'Open'
        CHECK(status IN ('Open','In Progress','Resolved','Closed')),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS quality_checklists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deliverable_id INTEGER NOT NULL
        REFERENCES wbs_deliverables(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS inspection_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checklist_id INTEGER NOT NULL
        REFERENCES quality_checklists(id) ON DELETE CASCADE,
    result TEXT NOT NULL CHECK(result IN ('Pass','Fail')),
    inspection_date TEXT NOT NULL,
    inspector TEXT NOT NULL,
    remarks TEXT
);

CREATE TABLE IF NOT EXISTS risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    likelihood INTEGER NOT NULL CHECK(likelihood BETWEEN 1 AND 5),
    impact INTEGER NOT NULL CHECK(impact BETWEEN 1 AND 5),
    category TEXT DEFAULT 'General',
    status TEXT NOT NULL DEFAULT 'Open'
        CHECK(status IN ('Open','Mitigated','Closed'))
);

CREATE TABLE IF NOT EXISTS pdpc_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    risk_id INTEGER NOT NULL REFERENCES risks(id) ON DELETE CASCADE,
    potential_problem TEXT NOT NULL,
    preventive_action TEXT NOT NULL,
    corrective_action TEXT NOT NULL
);
