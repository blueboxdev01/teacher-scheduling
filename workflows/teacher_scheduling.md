# Teacher Scheduling Automation

## Objective
Generate conflict-free teacher-to-classroom schedules and present them via a minimalist web UI. No teacher can be assigned to two classrooms at the same time slot.

## Prerequisites
- Python 3.8+
- Flask (`pip install flask`)

## Input Data Needed
- **Teachers**: Name, email (optional), display color
- **Classrooms**: Name, capacity
- **Constraints** (optional): Teacher unavailability for specific time slots

## System Flow

```
1. Start server → python tools/app.py
2. Open http://localhost:5000
3. Add teachers (Teachers tab) → name, email, color
4. Add classrooms (Classrooms tab) → name, capacity
5. (Optional) Set teacher constraints via API
6. Click "Generate Schedule" → greedy algorithm assigns teachers
7. Review the color-coded grid
8. Click any cell to manually override assignments
9. Click "Check Conflicts" to verify no overlaps
10. Export to CSV or Print to PDF
```

## How the Algorithm Works
- **Greedy with load balancing**: Iterates over each (classroom, time_slot) pair
- Picks the teacher with the fewest assignments who is available
- Respects "unavailable" constraints (hard block) and "preferred" constraints (soft priority)
- Skips break/lunch slots automatically
- Manual overrides (`is_manual=1`) are preserved across regenerations

## Tools Used
| Tool | Purpose |
|---|---|
| `tools/scheduler_db.py` | Database setup, CRUD, queries |
| `tools/schedule_generator.py` | Scheduling algorithm |
| `tools/app.py` | Flask web server (API + UI) |
| `tools/schedule_export.py` | CSV export |
| `tools/web/index.html` | Frontend (single-file) |

## Edge Cases
- **More slots than teachers**: Some classroom-slots remain unassigned (shown as empty cells)
- **Teacher deleted**: Cascade-deletes their assignments; regenerate to fill gaps
- **Classroom deleted**: Cascade-deletes assignments for that room
- **All teachers constrained for a slot**: Slot stays unassigned, visible in grid
- **Manual override conflicts**: The app checks before saving and rejects duplicates

## Data Storage
- SQLite database at `.tmp/scheduler.db` (auto-created, disposable per WAT conventions)
- Tables: `teachers`, `classrooms`, `time_slots`, `assignments`, `teacher_constraints`
- Default: 8 periods/day (Mon-Fri), period 5 is lunch break

## Notes
- The database file is regenerable — delete `.tmp/scheduler.db` to start fresh
- Print-to-PDF uses the browser's print dialog with `@media print` CSS rules
- Colors are assigned automatically from a 12-color palette but can be customized
