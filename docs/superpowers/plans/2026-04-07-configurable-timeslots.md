# Configurable Time Slots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded timeslots with a user-configurable template managed through a new Time Slots tab in the web UI.

**Architecture:** The `time_slots` table gains `slot_type` (TEXT) and `slot_order` (INTEGER) columns. A shared template is defined once and fanned out across Mon-Fri. New backend functions handle template CRUD, and a new frontend tab provides add/remove/reorder/save controls with a warning dialog when assignments exist.

**Tech Stack:** Python/Flask, SQLite, vanilla HTML/CSS/JS (single-file frontend)

---

### Task 1: Add `slot_type` and `slot_order` columns to schema and update seed logic

**Files:**
- Modify: `tools/scheduler_db.py:18-33` (remove hardcoded PERIODS/DEFAULT_TIME_SLOTS, update seed)
- Modify: `tools/scheduler_db.py:46-144` (schema + init_db)

- [ ] **Step 1: Update the schema in `init_db`**

In `tools/scheduler_db.py`, replace the `time_slots` CREATE TABLE statement with:

```python
        CREATE TABLE IF NOT EXISTS time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            is_break INTEGER DEFAULT 0,
            slot_type TEXT NOT NULL DEFAULT 'Class Period',
            slot_order INTEGER NOT NULL DEFAULT 0
        );
```

- [ ] **Step 2: Replace hardcoded constants with default template**

Remove the `DEFAULT_TIME_SLOTS`, `DAYS`, and `PERIODS` constants (lines 18-33) and replace with:

```python
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

DEFAULT_TEMPLATE = [
    {'start_time': '08:00', 'end_time': '08:45', 'slot_type': 'Class Period'},
    {'start_time': '08:50', 'end_time': '09:35', 'slot_type': 'Class Period'},
    {'start_time': '09:40', 'end_time': '10:25', 'slot_type': 'Class Period'},
    {'start_time': '10:30', 'end_time': '11:15', 'slot_type': 'Class Period'},
    {'start_time': '11:20', 'end_time': '12:05', 'slot_type': 'Lunch'},
    {'start_time': '12:10', 'end_time': '12:55', 'slot_type': 'Class Period'},
    {'start_time': '13:00', 'end_time': '13:45', 'slot_type': 'Class Period'},
    {'start_time': '13:50', 'end_time': '14:35', 'slot_type': 'Class Period'},
]
```

- [ ] **Step 3: Update the seed logic in `init_db`**

Replace the existing time slot seeding block (the `if existing == 0` block near line 136) with:

```python
    # Seed time slots if empty
    existing = c.execute("SELECT COUNT(*) FROM time_slots").fetchone()[0]
    if existing == 0:
        for day in DAYS:
            for order, slot in enumerate(DEFAULT_TEMPLATE, 1):
                is_break = 0 if slot['slot_type'] == 'Class Period' else 1
                c.execute(
                    "INSERT INTO time_slots (day, start_time, end_time, is_break, slot_type, slot_order) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (day, slot['start_time'], slot['end_time'], is_break, slot['slot_type'], order)
                )
```

- [ ] **Step 4: Verify the database initializes correctly**

Delete `.tmp/scheduler.db` and run:
```bash
python tools/scheduler_db.py
```
Expected: "Database initialized successfully." with no errors.

- [ ] **Step 5: Verify seeded data has new columns**

Run:
```bash
python -c "import sys; sys.path.insert(0,'tools'); from scheduler_db import init_db, get_time_slots; init_db(); slots=get_time_slots(); print(f'{len(slots)} slots'); print(slots[0]); print(slots[4])"
```
Expected: 40 slots. First slot has `slot_type: 'Class Period'`, `slot_order: 1`. Fifth slot (index 4) has `slot_type: 'Lunch'`, `slot_order: 5`.

- [ ] **Step 6: Commit**

```bash
git add tools/scheduler_db.py
git commit -m "feat: add slot_type and slot_order columns, replace hardcoded timeslot constants"
```

---

### Task 2: Add template CRUD functions and `has_assignments` helper

**Files:**
- Modify: `tools/scheduler_db.py` (add new functions after the existing time slots section, around line 237)

- [ ] **Step 1: Add `get_time_slot_template` function**

Add after the existing `get_time_slots` function:

```python
def get_time_slot_template(db_path=None):
    """Returns the unique slot template from Monday (since all days are identical)."""
    conn = get_db(db_path)
    rows = conn.execute(
        "SELECT slot_order, start_time, end_time, slot_type, is_break "
        "FROM time_slots WHERE day = 'Monday' ORDER BY slot_order"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 2: Add `save_time_slot_template` function**

Add after `get_time_slot_template`:

```python
def save_time_slot_template(slots, db_path=None):
    """
    Saves a new time slot template. Deletes all existing time_slots
    and inserts new ones fanned out across Mon-Fri.
    
    slots: list of {'start_time': str, 'end_time': str, 'slot_type': str}
    """
    conn = get_db(db_path)
    conn.execute("DELETE FROM time_slots")
    for day in DAYS:
        for order, slot in enumerate(slots, 1):
            is_break = 0 if slot['slot_type'] == 'Class Period' else 1
            conn.execute(
                "INSERT INTO time_slots (day, start_time, end_time, is_break, slot_type, slot_order) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (day, slot['start_time'], slot['end_time'], is_break, slot['slot_type'], order)
            )
    conn.commit()
    conn.close()
```

- [ ] **Step 3: Add `has_assignments` function**

Add after `save_time_slot_template`:

```python
def has_assignments(db_path=None):
    conn = get_db(db_path)
    count = conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
    conn.close()
    return count > 0
```

- [ ] **Step 4: Verify the new functions work**

```bash
python -c "
import sys; sys.path.insert(0,'tools')
from scheduler_db import init_db, get_time_slot_template, save_time_slot_template, has_assignments
init_db()
template = get_time_slot_template()
print(f'Template has {len(template)} slots')
for s in template:
    print(f'  {s[\"slot_order\"]}: {s[\"start_time\"]}-{s[\"end_time\"]} ({s[\"slot_type\"]})')
print(f'Has assignments: {has_assignments()}')
"
```
Expected: 8 slots with correct order, times, and types. `has_assignments: False`.

- [ ] **Step 5: Commit**

```bash
git add tools/scheduler_db.py
git commit -m "feat: add template CRUD functions and has_assignments helper"
```

---

### Task 3: Add API endpoints for template and assignment check

**Files:**
- Modify: `tools/app.py:14-25` (update imports)
- Modify: `tools/app.py` (add new routes, after the existing timeslots route around line 185)

- [ ] **Step 1: Update imports in `app.py`**

Add `get_time_slot_template`, `save_time_slot_template`, and `has_assignments` to the import from `scheduler_db`. The updated import block:

```python
from scheduler_db import (
    init_db, add_teacher, get_teachers, update_teacher, delete_teacher,
    add_classroom, get_classrooms, delete_classroom,
    get_time_slots, add_constraint, get_constraints, delete_constraint,
    create_assignment, delete_assignment,
    get_full_schedule, get_schedule_for_teacher, get_schedule_for_classroom,
    detect_conflicts, clear_auto_assignments,
    get_subjects, add_subject, delete_subject,
    assign_subject_to_teacher, remove_subject_from_teacher,
    get_teacher_subjects, get_teachers_with_subjects,
    get_grade_levels, assign_grade_to_teacher, remove_grade_from_teacher,
    get_time_slot_template, save_time_slot_template, has_assignments
)
```

- [ ] **Step 2: Add the template GET endpoint**

Add after the existing `/api/timeslots` GET route (around line 185):

```python
@app.route('/api/timeslots/template', methods=['GET'])
def api_get_template():
    return jsonify(get_time_slot_template())
```

- [ ] **Step 3: Add the template PUT endpoint**

Add after the GET template route:

```python
@app.route('/api/timeslots/template', methods=['PUT'])
def api_save_template():
    data = request.get_json()
    slots = data.get('slots', [])
    clear = data.get('clear_assignments', False)

    if not slots:
        return jsonify({'error': 'At least one time slot is required'}), 400

    for s in slots:
        if not s.get('start_time') or not s.get('end_time') or not s.get('slot_type'):
            return jsonify({'error': 'Each slot needs start_time, end_time, and slot_type'}), 400

    if has_assignments() and not clear:
        return jsonify({'error': 'Assignments exist. Set clear_assignments=true to proceed.'}), 409

    if clear:
        from scheduler_db import get_db
        conn = get_db()
        conn.execute("DELETE FROM assignments")
        conn.commit()
        conn.close()

    save_time_slot_template(slots)
    return jsonify({'message': f'Template saved with {len(slots)} slots across 5 days.'})
```

- [ ] **Step 4: Add the assignments/exists endpoint**

Add after the template PUT route:

```python
@app.route('/api/assignments/exists', methods=['GET'])
def api_assignments_exist():
    return jsonify({'exists': has_assignments()})
```

- [ ] **Step 5: Verify endpoints work**

Start the server and test with curl:
```bash
python tools/app.py &
sleep 2
curl -s http://localhost:5000/api/timeslots/template | python -m json.tool | head -20
curl -s http://localhost:5000/api/assignments/exists | python -m json.tool
```
Expected: Template returns 8 slots with `slot_order`, `start_time`, `end_time`, `slot_type`. Assignments exists returns `{"exists": false}`.

Stop the server after testing.

- [ ] **Step 6: Commit**

```bash
git add tools/app.py
git commit -m "feat: add API endpoints for timeslot template CRUD and assignment check"
```

---

### Task 4: Update schedule generator break detection

**Files:**
- Modify: `tools/schedule_generator.py:69-73`

- [ ] **Step 1: Update break detection in generate_schedule**

The current break check at line 70 (`if slot['is_break']:`) already works because `is_break` is still populated (derived from `slot_type`). However, update the `get_time_slots` query ordering to also sort by `slot_order`. 

In `tools/scheduler_db.py`, update the `get_time_slots` function to sort by `slot_order` as primary sort within a day:

```python
def get_time_slots(db_path=None):
    conn = get_db(db_path)
    rows = conn.execute(
        "SELECT * FROM time_slots ORDER BY CASE day "
        "WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 "
        "WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 END, slot_order, start_time"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 2: Verify schedule generation still works**

```bash
python -c "
import sys; sys.path.insert(0,'tools')
from scheduler_db import init_db, seed_sample_data
init_db()
seed_sample_data()
from schedule_generator import generate_schedule
result = generate_schedule()
print(result['message'])
"
```
Expected: Schedule generates with assignments, skipped breaks, and no errors.

- [ ] **Step 3: Commit**

```bash
git add tools/scheduler_db.py tools/schedule_generator.py
git commit -m "feat: update time slot ordering to use slot_order column"
```

---

### Task 5: Add Time Slots tab to the frontend — HTML structure

**Files:**
- Modify: `tools/web/index.html:466-470` (add nav button)
- Modify: `tools/web/index.html:544` (add page div before closing `</main>`)

- [ ] **Step 1: Add the Time Slots nav button**

In the `<nav>` section (line 466-470), add a Time Slots button between Classrooms and the closing `</nav>`:

```html
  <nav>
    <button class="active" onclick="showPage('schedule')">Schedule</button>
    <button onclick="showPage('teachers')">Teachers</button>
    <button onclick="showPage('classrooms')">Classrooms</button>
    <button onclick="showPage('timeslots')">Time Slots</button>
  </nav>
```

- [ ] **Step 2: Add the Time Slots page HTML**

Insert before the closing `</main>` tag (after the classrooms page div, around line 544):

```html
  <!-- ===== Time Slots Page ===== -->
  <div id="page-timeslots" class="page">
    <div class="add-form">
      <h3>Time Slot Template</h3>
      <p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;">
        Define the periods for each school day. This template applies to all weekdays (Mon-Fri).
      </p>
      <div id="timeslot-list"></div>
      <div style="margin-top:12px;display:flex;gap:8px;">
        <button class="btn" onclick="addSlotRow()">+ Add Slot</button>
        <button class="btn btn-primary" onclick="saveTemplate()">Save Time Slots</button>
      </div>
    </div>
  </div>
```

- [ ] **Step 3: Add the warning modal HTML**

Insert after the edit-teacher modal overlay (around line 600), before the toast div:

```html
<!-- ===== Time Slot Warning Modal ===== -->
<div id="timeslot-warning-overlay" class="modal-overlay" onclick="if(event.target===this)closeTimeslotWarning()">
  <div class="modal" style="max-width:420px;">
    <h3 style="color:var(--danger);">Warning</h3>
    <p style="margin:12px 0;font-size:14px;">
      Changing time slots will affect existing schedules. All current assignments will be cleared.
    </p>
    <div class="modal-actions">
      <button class="btn" onclick="closeTimeslotWarning()">Cancel</button>
      <button class="btn btn-danger" onclick="confirmSaveTemplate()">Clear & Save</button>
    </div>
  </div>
</div>
```

- [ ] **Step 4: Commit**

```bash
git add tools/web/index.html
git commit -m "feat: add Time Slots tab HTML structure and warning modal"
```

---

### Task 6: Add Time Slots tab CSS

**Files:**
- Modify: `tools/web/index.html` (add CSS before the closing `</style>` tag, around line 460)

- [ ] **Step 1: Add timeslot-specific styles**

Insert before the closing `</style>` tag:

```css
  /* --- Time Slot Editor --- */
  .slot-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
  }

  .slot-row:last-child { border-bottom: none; }

  .slot-order {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    min-width: 28px;
    text-align: center;
  }

  .slot-row input[type="time"] {
    padding: 6px 8px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 13px;
    font-family: inherit;
  }

  .slot-type-group {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1;
  }

  .slot-type-select {
    padding: 6px 8px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 13px;
    font-family: inherit;
    min-width: 120px;
  }

  .slot-break-label {
    padding: 6px 8px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 13px;
    font-family: inherit;
    width: 140px;
  }

  .slot-actions {
    display: flex;
    gap: 4px;
  }

  .slot-actions button {
    background: none;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    cursor: pointer;
    padding: 4px 8px;
    font-size: 12px;
    color: var(--text-secondary);
    transition: all 0.15s;
  }

  .slot-actions button:hover {
    background: var(--bg);
    color: var(--text);
  }

  .slot-actions button.slot-delete:hover {
    background: var(--danger);
    color: white;
    border-color: var(--danger);
  }
```

- [ ] **Step 2: Commit**

```bash
git add tools/web/index.html
git commit -m "feat: add CSS styles for Time Slots editor"
```

---

### Task 7: Add Time Slots tab JavaScript

**Files:**
- Modify: `tools/web/index.html` (add JS in the `<script>` section)

- [ ] **Step 1: Add template state variable**

Add to the state variables section (around line 606, after `let currentPage = 'schedule';`):

```javascript
  let slotTemplate = [];
```

- [ ] **Step 2: Add fetchTemplate to init**

Add `fetchTemplate()` to the `Promise.all` in the `init` function:

```javascript
  async function init() {
    await Promise.all([
      fetchTeachers(),
      fetchClassrooms(),
      fetchTimeSlots(),
      fetchSchedule(),
      fetchSubjects(),
      fetchGradeLevels(),
      fetchTemplate()
    ]);
    renderDayTabs();
    renderSchedule();
  }
```

- [ ] **Step 3: Add fetchTemplate function**

Add after the `fetchGradeLevels` function:

```javascript
  async function fetchTemplate() {
    slotTemplate = await (await fetch('/api/timeslots/template')).json();
    renderTimeSlotsPage();
  }
```

- [ ] **Step 4: Add renderTimeSlotsPage function**

Add after `fetchTemplate`:

```javascript
  function renderTimeSlotsPage() {
    const container = document.getElementById('timeslot-list');
    if (!container) return;

    if (!slotTemplate.length) {
      container.innerHTML = '<div class="empty-state"><p>No time slots defined. Add slots below.</p></div>';
      return;
    }

    container.innerHTML = slotTemplate.map((slot, i) => {
      const isBreak = slot.slot_type !== 'Class Period';
      return `
        <div class="slot-row" data-index="${i}">
          <span class="slot-order">${i + 1}</span>
          <input type="time" value="${slot.start_time}" onchange="updateSlot(${i}, 'start_time', this.value)">
          <span style="color:var(--text-secondary);">to</span>
          <input type="time" value="${slot.end_time}" onchange="updateSlot(${i}, 'end_time', this.value)">
          <div class="slot-type-group">
            <select class="slot-type-select" onchange="toggleSlotType(${i}, this.value)">
              <option value="Class Period" ${!isBreak ? 'selected' : ''}>Class Period</option>
              <option value="break" ${isBreak ? 'selected' : ''}>Break</option>
            </select>
            ${isBreak ? `<input type="text" class="slot-break-label" value="${slot.slot_type}" placeholder="e.g. Lunch, Recess" onchange="updateSlot(${i}, 'slot_type', this.value)">` : ''}
          </div>
          <div class="slot-actions">
            <button onclick="moveSlot(${i}, -1)" ${i === 0 ? 'disabled' : ''} title="Move up">&#9650;</button>
            <button onclick="moveSlot(${i}, 1)" ${i === slotTemplate.length - 1 ? 'disabled' : ''} title="Move down">&#9660;</button>
            <button class="slot-delete" onclick="removeSlot(${i})" title="Delete">&times;</button>
          </div>
        </div>`;
    }).join('');
  }
```

- [ ] **Step 5: Add slot manipulation functions**

Add after `renderTimeSlotsPage`:

```javascript
  function updateSlot(index, field, value) {
    slotTemplate[index][field] = value;
  }

  function toggleSlotType(index, value) {
    if (value === 'Class Period') {
      slotTemplate[index].slot_type = 'Class Period';
    } else {
      slotTemplate[index].slot_type = 'Break';
    }
    renderTimeSlotsPage();
  }

  function addSlotRow() {
    const last = slotTemplate[slotTemplate.length - 1];
    slotTemplate.push({
      start_time: last ? last.end_time : '08:00',
      end_time: last ? incrementTime(last.end_time, 45) : '08:45',
      slot_type: 'Class Period',
      slot_order: slotTemplate.length + 1
    });
    renderTimeSlotsPage();
  }

  function incrementTime(time, minutes) {
    const [h, m] = time.split(':').map(Number);
    const total = h * 60 + m + minutes;
    const nh = Math.floor(total / 60) % 24;
    const nm = total % 60;
    return String(nh).padStart(2, '0') + ':' + String(nm).padStart(2, '0');
  }

  function removeSlot(index) {
    if (slotTemplate.length <= 1) {
      showToast('Must have at least one time slot.', true);
      return;
    }
    slotTemplate.splice(index, 1);
    renderTimeSlotsPage();
  }

  function moveSlot(index, direction) {
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= slotTemplate.length) return;
    const temp = slotTemplate[index];
    slotTemplate[index] = slotTemplate[newIndex];
    slotTemplate[newIndex] = temp;
    renderTimeSlotsPage();
  }
```

- [ ] **Step 6: Add save and warning modal functions**

Add after the slot manipulation functions:

```javascript
  async function saveTemplate() {
    if (!slotTemplate.length) {
      showToast('Add at least one time slot.', true);
      return;
    }

    // Check if assignments exist
    const res = await fetch('/api/assignments/exists');
    const data = await res.json();

    if (data.exists) {
      document.getElementById('timeslot-warning-overlay').classList.add('show');
    } else {
      doSaveTemplate(false);
    }
  }

  function closeTimeslotWarning() {
    document.getElementById('timeslot-warning-overlay').classList.remove('show');
  }

  async function confirmSaveTemplate() {
    closeTimeslotWarning();
    await doSaveTemplate(true);
  }

  async function doSaveTemplate(clearAssignments) {
    const slots = slotTemplate.map(s => ({
      start_time: s.start_time,
      end_time: s.end_time,
      slot_type: s.slot_type
    }));

    const res = await fetch('/api/timeslots/template', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slots, clear_assignments: clearAssignments })
    });
    const data = await res.json();

    if (data.error) {
      showToast(data.error, true);
    } else {
      await Promise.all([fetchTimeSlots(), fetchTemplate(), fetchSchedule()]);
      renderSchedule();
      showToast(data.message);
    }
  }
```

- [ ] **Step 7: Update the `showPage` function for timeslots tab matching**

Replace the existing `showPage` function with:

```javascript
  function showPage(page) {
    currentPage = page;
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');
    document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('nav button').forEach(b => {
      const text = b.textContent.toLowerCase().replace(/\s+/g, '');
      const pageKey = page.toLowerCase().replace(/\s+/g, '');
      if (text.includes(pageKey)) b.classList.add('active');
    });
  }
```

- [ ] **Step 8: Commit**

```bash
git add tools/web/index.html
git commit -m "feat: add Time Slots tab JavaScript — template editor with save/warning flow"
```

---

### Task 8: Update schedule grid to show slot_type labels for breaks

**Files:**
- Modify: `tools/web/index.html` (renderClassroomView and renderTeacherView functions)

- [ ] **Step 1: Update renderClassroomView break cell**

In the `renderClassroomView` function, find the break slot rendering line:

```javascript
          html += `<div class="grid-cell break-slot">Break</div>`;
```

Replace with:

```javascript
          html += `<div class="grid-cell break-slot">${slot.slot_type || 'Break'}</div>`;
```

- [ ] **Step 2: Update renderTeacherView break cell**

In the `renderTeacherView` function, find the same break slot line:

```javascript
            html += `<div class="grid-cell break-slot">Break</div>`;
```

Replace with:

```javascript
            html += `<div class="grid-cell break-slot">${slot.slot_type || 'Break'}</div>`;
```

- [ ] **Step 3: Update the `get_time_slots` query to return `slot_type`**

The `get_time_slots` function in `scheduler_db.py` already uses `SELECT *`, so `slot_type` is already included in the response. No change needed.

Verify by checking that the `/api/timeslots` response includes `slot_type`:
```bash
python tools/app.py &
sleep 2
curl -s http://localhost:5000/api/timeslots | python -m json.tool | head -15
```
Expected: Each slot object includes `"slot_type": "Class Period"` or `"slot_type": "Lunch"`.

Stop the server after testing.

- [ ] **Step 4: Commit**

```bash
git add tools/web/index.html
git commit -m "feat: display slot_type labels in schedule grid break cells"
```

---

### Task 9: End-to-end manual test

**Files:** None (testing only)

- [ ] **Step 1: Delete database and start fresh**

```bash
rm -f .tmp/scheduler.db
python tools/app.py
```

- [ ] **Step 2: Verify Time Slots tab**

Open `http://localhost:5000` in browser:
1. Click "Time Slots" tab — should show 8 default slots
2. Slot 5 should show "Lunch" as break type
3. All others should show "Class Period"

- [ ] **Step 3: Edit the template**

1. Change slot 5 type to "Break" and label to "Recess"
2. Add a new slot at the end
3. Move the new slot up one position
4. Click "Save Time Slots" — should save without warning (no assignments yet)
5. Verify the schedule grid reflects new time columns

- [ ] **Step 4: Test warning dialog**

1. Add some teachers and classrooms, then generate a schedule
2. Go to Time Slots tab and click "Save Time Slots"
3. Warning modal should appear
4. Click "Cancel" — nothing should change
5. Click "Save Time Slots" again, then "Clear & Save" — assignments should be cleared

- [ ] **Step 5: Verify schedule still works after template change**

1. Generate a new schedule — should work with the updated time slots
2. Check that break slots show correct labels in the grid

- [ ] **Step 6: Commit all remaining changes (if any)**

```bash
git add -A
git commit -m "chore: end-to-end verification of configurable time slots"
```
