# Sections — Design Spec

## Overview

Add sections as subdivisions of grade levels. Each grade level can have a configurable number of sections (e.g., G1 has 3 sections). Each section has an assigned homeroom teacher and homeroom classroom, both enforced as one-to-one relationships. This is the foundation for scheduling subjects per section and distinguishing homeroom vs specialist teachers in later phases.

## Data Model

### New `sections` table

```sql
CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grade_level_id INTEGER NOT NULL,
    section_number INTEGER NOT NULL,
    homeroom_teacher_id INTEGER UNIQUE,
    classroom_id INTEGER UNIQUE,
    FOREIGN KEY (grade_level_id) REFERENCES grade_levels(id) ON DELETE CASCADE,
    FOREIGN KEY (homeroom_teacher_id) REFERENCES teachers(id) ON DELETE SET NULL,
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE SET NULL,
    UNIQUE(grade_level_id, section_number)
);
```

- `section_number`: 1-based, auto-generated (Section 1, Section 2, etc.)
- `homeroom_teacher_id`: UNIQUE across entire table — one teacher can only be homeroom for one section
- `classroom_id`: UNIQUE across entire table — one classroom can only belong to one section
- Both nullable so sections can exist without assignments initially

### No changes to existing tables

`grade_levels`, `teachers`, `classrooms` remain unchanged.

### Seed Data

On `init_db`, if `sections` table is empty and grade levels exist:
- Create 3 sections per grade level (G1-G5 = 15 sections total)
- Create 15 classrooms named "G1-1 Homeroom" through "G5-3 Homeroom"
- Assign each classroom to its corresponding section
- Homeroom teachers left unassigned (user assigns manually)

## Backend

### New Functions in `scheduler_db.py`

**`get_sections(grade_level_id=None, db_path=None)`**
Returns all sections with joined info. Each row includes: `id`, `grade_level_id`, `grade_name`, `section_number`, `homeroom_teacher_id`, `teacher_name`, `classroom_id`, `classroom_name`. Optional filter by `grade_level_id`.

**`set_section_count(grade_level_id, count, db_path=None)`**
Sets the number of sections for a grade level.
- If `count` > current: adds new sections with incrementing `section_number`
- If `count` < current: removes the highest-numbered sections (CASCADE handles related data)
- If `count` == current: no-op
- Minimum count: 0 (grade can have no sections)

**`assign_homeroom_teacher(section_id, teacher_id, db_path=None)`**
Assigns a teacher as homeroom for a section.
- First clears any existing section assignment for that teacher (enforces one-to-one)
- If `teacher_id` is None, just clears the current assignment
- Returns `(True, None)` on success or `(False, error_message)` on failure

**`assign_section_classroom(section_id, classroom_id, db_path=None)`**
Assigns a classroom to a section.
- First clears any existing section assignment for that classroom (enforces one-to-one)
- If `classroom_id` is None, just clears the current assignment
- Returns `(True, None)` on success or `(False, error_message)` on failure

### New API Endpoints in `app.py`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sections` | All sections with grade/teacher/classroom info. Optional `?grade_level_id=N` filter |
| PUT | `/api/gradelevels/<id>/sections` | Set section count `{"count": N}` |
| PUT | `/api/sections/<id>/teacher` | Assign homeroom teacher `{"teacher_id": N}` (null to clear) |
| PUT | `/api/sections/<id>/classroom` | Assign classroom `{"classroom_id": N}` (null to clear) |

## Frontend

### New "Grades & Sections" Tab

**Nav update:** Add "Grades & Sections" button to nav bar. Order: Schedule | Teachers | Classrooms | Time Slots | Grades & Sections

**Page layout:** One card per grade level, each containing:

1. **Header row:** Grade name + section count input + "Update" button
2. **Section table** with columns:
   - `#` (section number)
   - Homeroom Teacher (dropdown — only shows teachers not already assigned as homeroom elsewhere)
   - Classroom (dropdown — only shows classrooms not already assigned to another section)

**Behavior:**
- On page load, fetch `/api/sections` and `/api/gradelevels`
- Section count change: calls `PUT /api/gradelevels/<id>/sections`, then refreshes
- Teacher dropdown change: calls `PUT /api/sections/<id>/teacher`, then refreshes
- Classroom dropdown change: calls `PUT /api/sections/<id>/classroom`, then refreshes
- Dropdowns include a blank "— Select —" option to allow clearing assignments

### Existing Grade Level References

The teacher edit modal currently shows grade level tags. This continues to work as-is — grade level assignments on teachers are a separate concept from homeroom section assignments. A teacher can be tagged with G1 (meaning they can teach G1) without being the homeroom teacher for a G1 section.

## Edge Cases

- **Grade level deleted:** Sections cascade-delete via FK.
- **Teacher deleted:** `homeroom_teacher_id` set to NULL via FK ON DELETE SET NULL.
- **Classroom deleted:** `classroom_id` set to NULL via FK ON DELETE SET NULL.
- **Section count reduced:** Highest-numbered sections removed. If they had homeroom teachers/classrooms assigned, those become available again.
- **Section count set to 0:** All sections for that grade removed.
- **Duplicate assignment attempt:** The UNIQUE constraint on `homeroom_teacher_id` and `classroom_id` prevents duplicates. The backend clears previous assignments before setting new ones.
