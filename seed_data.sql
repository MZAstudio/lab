-- Smart Healthcare PM System – Seed Data
INSERT OR IGNORE INTO project_charter VALUES (
  1,'Smart Healthcare Project Management System',
  '1. Build a unified healthcare platform for 5 hospitals covering appointments, lab reports, doctor scheduling, online consultations, and billing.
2. Deliver within 16 weeks and PKR 5,000,000 budget.
3. Achieve 99.9% uptime and sub-2-second response times.
4. Comply with healthcare data protection regulations.',
  'Hospital Management (Primary Sponsor), Doctors and Medical Staff, Patients, Laboratory Staff, Billing Department, IT Department, Regulatory/Compliance Officers',
  'Patient appointment management, Laboratory report management, Doctor schedule management, Online consultations, Hospital billing, Multi-hospital support (5 hospitals)',
  'AI-based preliminary diagnosis, Mobile application, Third-party insurance integration, HR/Payroll, Inventory management',
  5000000.0,'2026-01-08','2026-04-26',datetime('now')
);

INSERT OR IGNORE INTO project_management_plan VALUES (
  1,
  'The project covers healthcare platform development for 5 hospitals. Scope managed via formal change control. Schedule tracked through activity-based WBS with forward-pass dependency calculation. Budget monitored with EVM against PKR 5,000,000 baseline.',
  'All deliverables must pass code review, unit testing (>80% coverage), integration testing, and UAT with hospital representatives. Critical defects resolved before UAT sign-off.',
  'Plan reviewed monthly. Change requests require PM approval before scope/schedule/budget adjustment.',
  datetime('now')
);

INSERT OR IGNORE INTO project_status VALUES (1,'Active','2026-03-15','Project progressing. Two change requests pending. Schedule slippage in testing phase.');

INSERT OR IGNORE INTO team_members(name,role) VALUES
  ('Ahmed Raza','Project Manager'),('Sara Khan','Backend Developer'),
  ('Ali Hassan','Backend Developer'),('Fatima Malik','Frontend Developer'),
  ('Usman Tariq','Frontend Developer'),('Zara Ahmed','Database Developer'),
  ('Bilal Sheikh','QA Engineer');

INSERT OR IGNORE INTO milestones(name,due_date,status) VALUES
  ('Project Kickoff','2026-01-08','Completed'),
  ('Requirements Finalized','2026-01-26','Completed'),
  ('Database Design Complete','2026-02-09','Completed'),
  ('Backend Core Complete','2026-02-23','Completed'),
  ('Frontend MVP Complete','2026-03-15','In Progress'),
  ('Integration & Testing Complete','2026-04-05','Pending'),
  ('UAT Sign-Off','2026-04-19','Pending'),
  ('Project Delivery','2026-04-26','Pending');

INSERT OR IGNORE INTO responsibilities(person_name,role,responsibility) VALUES
  ('Ahmed Raza','Project Manager','Overall project planning, scheduling, stakeholder communication, change control, and risk management'),
  ('Sara Khan','Backend Developer','Appointment and consultation API development, authentication, and server-side logic'),
  ('Ali Hassan','Backend Developer','Laboratory reports and billing backend services, database integration, and API documentation'),
  ('Fatima Malik','Frontend Developer','Patient portal UI, appointment booking interface, and responsive design'),
  ('Usman Tariq','Frontend Developer','Doctor dashboard, admin panel UI, reporting screens, and cross-browser testing'),
  ('Zara Ahmed','Database Developer','Database schema design, query optimization, data migration scripts, and backup'),
  ('Bilal Sheikh','QA Engineer','Test planning, defect tracking, regression testing, UAT coordination, and quality reporting');

INSERT OR IGNORE INTO requirements(title,description,priority,status,source) VALUES
  ('Patient Appointment Management','System shall allow patients to book, reschedule and cancel appointments at any of the 5 hospitals.','High','Approved','Initial'),
  ('Laboratory Report Management','System shall digitize lab test ordering, result entry and report distribution.','High','Approved','Initial'),
  ('Doctor Schedule Management','System shall manage doctor availability, duty rosters and appointment slot allocation.','High','Approved','Initial'),
  ('Online Consultation Platform','System shall provide secure video/text consultation between doctors and patients.','Medium','Approved','Initial'),
  ('Hospital Billing System','System shall generate invoices, process payments, apply insurance deductions and produce billing reports.','High','Approved','Initial'),
  ('Multi-Hospital Support (5 Hospitals)','System shall support centralized management of 5 hospital locations.','High','Approved','Initial'),
  ('AI-Based Preliminary Diagnosis','System shall provide AI-driven symptom analysis to suggest preliminary diagnoses.','Medium','Proposed','Change Request'),
  ('Mobile Application','Native mobile app for iOS and Android giving patients mobile access.','Medium','Proposed','Change Request');

INSERT OR IGNORE INTO wbs_deliverables(name,description,requirement_id) VALUES
  ('D1: System Architecture & Database','Database schema, ER diagrams and architecture documentation',6),
  ('D2: Appointment Management Module','Full appointment booking, scheduling and notification system',1),
  ('D3: Laboratory Reports Module','Lab test ordering, result capture and report generation',2),
  ('D4: Doctor Schedule Module','Doctor roster management and availability system',3),
  ('D5: Online Consultation Module','Video/text consultation platform',4),
  ('D6: Billing & Payments Module','Invoice generation, payment processing and reports',5),
  ('D7: Integration & Deployment','System integration, deployment scripts and go-live support',6);

INSERT OR IGNORE INTO wbs_work_packages(name,description,deliverable_id) VALUES
  ('WP1.1: Database Design','Design and create normalized database schema',1),
  ('WP1.2: Architecture Documentation','Document architecture, tech stack and API contracts',1),
  ('WP2.1: Appointment API Backend','REST APIs for appointment CRUD and scheduling logic',2),
  ('WP2.2: Appointment UI','Patient-facing appointment booking interface',2),
  ('WP3.1: Lab Module Backend','APIs for lab test orders and results',3),
  ('WP3.2: Lab Module UI','UI for lab staff to enter results and generate reports',3),
  ('WP4.1: Doctor Roster Backend','APIs for doctor schedule management',4),
  ('WP4.2: Doctor Dashboard UI','Doctor-facing schedule and appointment dashboard',4),
  ('WP5.1: Consultation Backend','Video/text consultation session management APIs',5),
  ('WP5.2: Consultation UI','Patient and doctor consultation interface',5),
  ('WP6.1: Billing Backend','Invoice, payment and insurance processing APIs',6),
  ('WP6.2: Billing UI','Billing management and reporting interface',6),
  ('WP7.1: Integration Testing','End-to-end integration test execution',7),
  ('WP7.2: UAT & Deployment','User acceptance testing and production deployment',7);

INSERT OR IGNORE INTO change_requests(title,description,justification,cost_impact,schedule_impact_days,status,requirement_id) VALUES
  ('AI Diagnosis Module Addition','Add an AI-based preliminary diagnosis module that analyzes patient symptoms.','Hospital management requests this to improve diagnostic accuracy. Competitive hospitals already offer this.',500000.0,14,'Pending',7),
  ('Mobile Application Development','Develop native iOS and Android mobile applications for patients.','Over 70% of patient interactions originate from mobile. A mobile app will significantly improve engagement.',300000.0,7,'Pending',8);

-- Activities (member IDs: Ahmed=1,Sara=2,Ali=3,Fatima=4,Usman=5,Zara=6,Bilal=7)
INSERT OR IGNORE INTO activities(name,work_package_id,assigned_member_id,estimated_duration,planned_start,planned_end,actual_start,percent_complete,planned_cost) VALUES
  ('A01: Project Kickoff & Planning',1,1,5,'2026-01-08','2026-01-12','2026-01-08',100,50000),
  ('A02: Database Schema Design',1,6,10,'2026-01-15','2026-01-26','2026-01-15',100,80000),
  ('A03: Architecture Documentation',2,1,5,'2026-01-22','2026-01-26','2026-01-22',100,30000),
  ('A04: Appointment API Development',3,2,15,'2026-01-29','2026-02-16','2026-01-29',100,150000),
  ('A05: Appointment UI Development',4,4,12,'2026-02-05','2026-02-20','2026-02-05',90,120000),
  ('A06: Lab Module Backend',5,3,12,'2026-01-29','2026-02-13','2026-01-29',100,120000),
  ('A07: Lab Module UI',6,5,10,'2026-02-05','2026-02-16','2026-02-07',85,100000),
  ('A08: Doctor Schedule Backend',7,2,10,'2026-02-19','2026-03-01','2026-02-19',100,100000),
  ('A09: Doctor Dashboard UI',8,4,10,'2026-02-19','2026-03-01','2026-02-21',80,100000),
  ('A10: Consultation Backend',9,3,12,'2026-03-04','2026-03-15','2026-03-04',70,130000),
  ('A11: Consultation UI',10,5,10,'2026-03-04','2026-03-15','2026-03-06',60,110000),
  ('A12: Billing Backend',11,3,12,'2026-03-04','2026-03-15','2026-03-04',65,130000),
  ('A13: Billing UI',12,4,10,'2026-03-11','2026-03-22',NULL,30,100000),
  ('A14: Integration Testing',13,7,15,'2026-03-25','2026-04-12',NULL,15,120000),
  ('A15: UAT & Deployment',14,1,10,'2026-04-15','2026-04-26',NULL,0,80000),
  ('A16: Performance Testing',13,7,8,'2026-03-25','2026-04-05',NULL,20,70000),
  ('A17: Security Audit',13,6,5,'2026-04-01','2026-04-05',NULL,0,50000),
  ('A18: Data Migration Scripts',1,6,7,'2026-02-05','2026-02-13','2026-02-05',100,60000);

INSERT OR IGNORE INTO activity_dependencies(activity_id,predecessor_id) VALUES
  (2,1),(3,1),(4,2),(4,3),(5,4),(6,2),(7,6),(8,4),(9,8),
  (10,8),(11,10),(12,6),(13,12),(14,5),(14,7),(14,9),(14,11),(14,13),
  (15,14),(16,14),(17,16),(15,17),(18,2);

INSERT OR IGNORE INTO actual_cost_entries(activity_id,amount,entry_date,description) VALUES
  (1,52000,'2026-01-12','Kickoff and planning'),
  (2,88000,'2026-01-26','DB design tools and review'),
  (3,31000,'2026-01-26','Architecture documentation'),
  (4,168000,'2026-02-16','Appointment API — complexity higher than estimated'),
  (5,115000,'2026-02-22','Appointment UI partial'),
  (6,125000,'2026-02-13','Lab backend including report generation'),
  (7,98000,'2026-02-20','Lab UI partial'),
  (8,110000,'2026-03-01','Doctor schedule backend'),
  (9,95000,'2026-03-05','Doctor dashboard UI partial'),
  (10,105000,'2026-03-15','Consultation backend partial'),
  (12,90000,'2026-03-15','Billing backend partial'),
  (18,62000,'2026-02-13','Data migration scripts');

INSERT OR IGNORE INTO defects(title,description,severity,assigned_to,deliverable_id,requirement_id,status) VALUES
  ('Appointment Double-Booking Bug','System allows two patients to book the same slot. Race condition under concurrent load.','Critical',2,2,1,'Open'),
  ('Patient Record Data Loss on Update','Updating a patient record overwrites fields with NULL due to incorrect UPDATE query.','Critical',3,1,1,'In Progress'),
  ('Lab Report PDF Generation Failure','PDF fails when special characters exist in patient names.','High',3,3,2,'Open'),
  ('Doctor Schedule Timezone Issue','Availability slots show incorrect times for different timezone hospitals.','High',2,4,3,'In Progress'),
  ('Billing Calculation Rounding Error','Invoice totals show rounding discrepancies for multi-item invoices.','Medium',3,6,5,'Resolved'),
  ('Consultation Session Timeout','Sessions timeout after 15 minutes without warning.','High',2,5,4,'Open'),
  ('UI Rendering Issue in IE11','Appointment UI date picker breaks in Internet Explorer 11.','Low',4,2,1,'Closed');

INSERT OR IGNORE INTO quality_checklists(deliverable_id,item_name,description) VALUES
  (1,'Schema normalization (3NF)','Verify all tables are in Third Normal Form'),
  (1,'Referential integrity constraints','All foreign keys properly defined'),
  (1,'Index optimization','Indexes on frequently queried columns'),
  (2,'API endpoint testing','All appointment API endpoints tested'),
  (2,'Concurrent booking handling','Race conditions handled with locking'),
  (2,'Input validation','All inputs validated server and client side'),
  (3,'Report generation accuracy','Lab reports generate correct values'),
  (3,'PDF output quality','PDFs render correctly for all character sets'),
  (4,'Schedule conflict detection','System prevents schedule conflicts'),
  (5,'Consultation security','All sessions use end-to-end encryption'),
  (6,'Billing accuracy','Invoice calculations verified'),
  (7,'End-to-end integration','Full workflow tested across all 5 hospitals');

INSERT OR IGNORE INTO inspection_results(checklist_id,result,inspection_date,inspector,remarks) VALUES
  (1,'Pass','2026-02-09','Zara Ahmed','All tables in 3NF'),
  (2,'Pass','2026-02-09','Zara Ahmed','FK constraints correctly implemented'),
  (3,'Pass','2026-02-09','Bilal Sheikh','Indexes added for key columns'),
  (4,'Pass','2026-02-20','Bilal Sheikh','All 24 endpoints tested and passing'),
  (5,'Fail','2026-02-22','Bilal Sheikh','CRITICAL: Race condition allows double-booking'),
  (6,'Pass','2026-02-20','Bilal Sheikh','Client and server validation working'),
  (7,'Pass','2026-02-16','Bilal Sheikh','Report values match manual calculations'),
  (8,'Fail','2026-02-16','Bilal Sheikh','PDF fails with Arabic/Urdu characters'),
  (9,'Pass','2026-03-05','Bilal Sheikh','Conflict detection working');

INSERT OR IGNORE INTO risks(title,description,likelihood,impact,category,status) VALUES
  ('Schedule Overrun Due to Scope Creep','Additional requirements may extend timeline beyond 16 weeks.',4,5,'Schedule','Open'),
  ('Budget Overrun from Complexity','Backend APIs may require more effort causing cost overrun.',4,4,'Cost','Open'),
  ('Critical Defects in Appointment Module','Race conditions in appointment scheduling may delay release.',5,5,'Quality','Open'),
  ('Third-Party Integration Delays','Hospital HIS API compatibility issues causing delays.',3,4,'Technical','Open'),
  ('Key Personnel Unavailability','Loss of DB Developer or Backend Developer could stall critical tasks.',2,5,'Resource','Open'),
  ('Data Migration Corruption Risk','Migrating hospital records may result in data corruption.',3,5,'Data','Open'),
  ('Regulatory Compliance Gap','System may not comply with healthcare data protection regulations.',2,4,'Compliance','Mitigated'),
  ('UAT Rejection by Hospital Staff','Hospital staff may reject the system during UAT.',3,4,'Acceptance','Open');

INSERT OR IGNORE INTO pdpc_actions(risk_id,potential_problem,preventive_action,corrective_action) VALUES
  (1,'Uncontrolled scope additions inflate schedule by >3 weeks','Implement formal change control; freeze scope after sign-off','Activate schedule compression; negotiate deadline extension'),
  (1,'Parallel work streams create integration conflicts','Hold weekly integration syncs; define API contracts upfront','Assign dedicated integration resource; emergency integration sprints'),
  (2,'Appointment module backend requires 50% more effort','Break tasks into smaller units; conduct spike before estimation','Re-allocate developer from lower-priority tasks; approve budget reserve'),
  (3,'Double-booking race condition causes data integrity failure','Implement pessimistic locking; conduct load testing with 100 concurrent users','Apply emergency patch with DB-level constraints; roll back if patch fails'),
  (3,'Critical defect found 1 week before UAT','Set defect SLA: Critical=24h; track open defects in daily standup','Postpone UAT by 1 week; fast-track defect resolution all hands'),
  (4,'Hospital HIS API returns unexpected data format','Request API docs and test environment 4 weeks before integration','Implement adapter layer; negotiate format with hospital IT'),
  (5,'Database Developer leaves project mid-way','Document all DB decisions; maintain up-to-date schema docs','Bring in contract specialist; pair programming for knowledge transfer'),
  (6,'Data migration corrupts 10% of patient records','Run migration in staging first; validate record counts and checksums','Restore from backup immediately; run corrected migration; notify hospitals');
