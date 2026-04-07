# Configurable Time Slots — Design Spec

## Overview

Replace the hardcoded 8-period timeslot structure with a user-configurable template managed through the web UI. One template is shared across all weekdays (Mon-Fri). Each slot can be a "Class Period" or a custom-labeled break (e.g., "Lunch", "Recess", "Snack Break").

## Data Model

### Schema Changes to `time_slots` table

Add two columns:
- `slot_type TEXT NOT NULL DEFAULT 'Class Period'` — either "Class Period" or a custom break label
- `slot_order INTEGER NOT NULL DEFAULT 0` — 1-based ordering within a day

The existing `is_break` column is kept for backward compatibility but derived: `is_break = 1` when `slot_type != 'Class Period'`, `is_break = 0` otherwise. This is set automatically when saving the template.

### Removed Constants

Remove from `scheduler_db.py`:
- `PERIODS` list
- `DEFAULT_TIME_SLOTS` list
- The loop that builds `DEFAULT_TIME_SLOTS`

### Default Seed

On `init_db`, if `time_slots` is empty, seed a default template matching the current structure:

| Order | Start | End   | Type         |
|-------|-------|-------|--------------|
| 1     | 08:00 | 08:45 | Class Period |
| 2     | 08:50 | 09:35 | Class Period |
| 3     | 09:40 | 10:25 | Class Period |
| 4     | 10:30 | 11:15 | Class Period |
| 5     | 11:20 | 12:05 | Lunch        |
| 6     | 12:10 | 12:55 | Class Period |
| 7     | 13:00 | 13:45 | Class Period |
| 8     | 13:50 | 14:35 | Class Period |

Fanned out across Monday-Friday (40 rows total).

## Backend

### New Functions in `scheduler_db.py`

- **`get_time_slot_template(db_path=None)`** — Returns the unique ordered slot list from one day (since all days are identical). Returns list of `{slot_order, start_time, end_time, slot_type}`.

- **`save_time_slot_template(slots, db_path=None)`** — Accepts an ordered list of `{start_time, end_time, slot_type}`. Deletes all existing `time_slots` rows, then inserts new rows fanned out across Mon-Fri with `slot_order` and `is_break` derived from `slot_type`.

- **`has_assignments(db_path=None)`** — Returns `True` if any rows exist in the `assignments` table.

### New/Modified API Endpoints in `app.py`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/timeslots/template` | Returns the current slot template |
| PUT | `/api/timeslots/template` | Saves a new template. Expects JSON: `{slots: [{start_time, end_time, slot_type}], clear_assignments: bool}`. If `clear_assignments` is true, clears all assignments before saving. If false and assignments exist, returns 409. |
| GET | `/api/assignments/exists` | Returns `{exists: true/false}` |

### Schedule Generator Update

In `schedule_generator.py`, change break detection:
- **Before:** `if slot['is_break']:`
- **After:** `if slot['is_break']:` (no change needed — `is_break` is still populated, just derived from `slot_type` now)

## Frontend

### New "Time Slots" Tab

Position: between "Classrooms" and "Schedule" tabs.

**Layout:**
- Ordered list of slot rows, each showing:
  - Auto-numbered order (Period 1, Period 2, ...)
  - Start time input (time picker)
  - End time input (time picker)
  - Type dropdown: "Class Period" option + text input for custom break label
  - Move up / Move down arrows
  - Delete button (trash icon)
- "Add Slot" button at the bottom
- "Save Time Slots" button

**Save Behavior:**
1. On click "Save Time Slots", call `GET /api/assignments/exists`
2. If assignments exist, show a warning modal:
   > "Changing time slots will affect existing schedules. Do you want to clear all assignments, or cancel?"
   > Buttons: [Clear & Save] [Cancel]
3. If "Clear & Save" or no assignments exist, call `PUT /api/timeslots/template` with `clear_assignments: true`
4. If "Cancel", do nothing

### Impact on Schedule Grid

The schedule grid already reads from `time_slots` via `GET /api/timeslots`. After saving a new template, the grid will reflect the new structure on next load. Break rows in the grid should display the `slot_type` label (e.g., "Lunch" instead of generic "Break").

## Edge Cases

- **Empty template:** Prevent saving with zero slots. Show validation error.
- **Overlapping times:** No server-side enforcement (user responsibility), but slots are ordered by `slot_order`, not by time.
- **All breaks, no class periods:** Allowed but schedule generation will assign nothing (all slots skipped).
- **Delete while assignments exist:** Handled by the warning dialog flow described above.
