"""
Database layer for the Teacher Scheduling system.
Handles schema creation, CRUD operations, and schedule queries.
"""

import sqlite3
import os
import sys

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), '..', '.tmp', 'scheduler.db')

TEACHER_COLORS = [
    '#4A90D9', '#E74C3C', '#2ECC71', '#F39C12', '#9B59B6',
    '#1ABC9C', '#E67E22', '#3498DB', '#E91E63', '#00BCD4',
    '#8BC34A', '#FF5722'
]

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


def get_db(db_path=None):
    db_path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None):
    conn = get_db(db_path)
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT DEFAULT '',
            color TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS classrooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            capacity INTEGER DEFAULT 30
        );

        CREATE TABLE IF NOT EXISTS time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            is_break INTEGER DEFAULT 0,
            slot_type TEXT NOT NULL DEFAULT 'Class Period',
            slot_order INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            classroom_id INTEGER NOT NULL,
            time_slot_id INTEGER NOT NULL,
            subject TEXT DEFAULT '',
            is_manual INTEGER DEFAULT 0,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
            FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE,
            FOREIGN KEY (time_slot_id) REFERENCES time_slots(id) ON DELETE CASCADE,
            UNIQUE (classroom_id, time_slot_id)
        );

        CREATE TABLE IF NOT EXISTS teacher_constraints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            time_slot_id INTEGER NOT NULL,
            constraint_type TEXT NOT NULL DEFAULT 'unavailable',
            FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
            FOREIGN KEY (time_slot_id) REFERENCES time_slots(id) ON DELETE CASCADE,
            UNIQUE (teacher_id, time_slot_id)
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS teacher_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            UNIQUE (teacher_id, subject_id)
        );

        CREATE TABLE IF NOT EXISTS grade_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS teacher_grade_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            grade_level_id INTEGER NOT NULL,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
            FOREIGN KEY (grade_level_id) REFERENCES grade_levels(id) ON DELETE CASCADE,
            UNIQUE (teacher_id, grade_level_id)
        );
    """)

    # Seed default subjects if empty
    existing_subjects = c.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
    if existing_subjects == 0:
        default_subjects = ['PE', 'Music', 'Chinese', 'Design', 'Computer Science', 'Art', 'SEL', 'Thai']
        c.executemany("INSERT INTO subjects (name) VALUES (?)", [(s,) for s in default_subjects])

    # Seed default grade levels if empty
    existing_grades = c.execute("SELECT COUNT(*) FROM grade_levels").fetchone()[0]
    if existing_grades == 0:
        default_grades = ['G1', 'G2', 'G3', 'G4', 'G5']
        c.executemany("INSERT INTO grade_levels (name) VALUES (?)", [(g,) for g in default_grades])

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

    conn.commit()
    conn.close()


# --- Teachers ---

def add_teacher(name, email='', color=None, db_path=None):
    conn = get_db(db_path)
    if not color:
        count = conn.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]
        color = TEACHER_COLORS[count % len(TEACHER_COLORS)]
    c = conn.execute(
        "INSERT INTO teachers (name, email, color) VALUES (?, ?, ?)",
        (name, email, color)
    )
    conn.commit()
    teacher_id = c.lastrowid
    conn.close()
    return teacher_id


def get_teachers(db_path=None):
    conn = get_db(db_path)
    rows = conn.execute("SELECT * FROM teachers ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_teacher(teacher_id, name=None, email=None, color=None, db_path=None):
    conn = get_db(db_path)
    fields = []
    values = []
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if email is not None:
        fields.append("email = ?")
        values.append(email)
    if color is not None:
        fields.append("color = ?")
        values.append(color)
    if fields:
        values.append(teacher_id)
        conn.execute(f"UPDATE teachers SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()


def delete_teacher(teacher_id, db_path=None):
    conn = get_db(db_path)
    conn.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))
    conn.commit()
    conn.close()


# --- Classrooms ---

def add_classroom(name, capacity=30, db_path=None):
    conn = get_db(db_path)
    c = conn.execute(
        "INSERT INTO classrooms (name, capacity) VALUES (?, ?)",
        (name, capacity)
    )
    conn.commit()
    classroom_id = c.lastrowid
    conn.close()
    return classroom_id


def get_classrooms(db_path=None):
    conn = get_db(db_path)
    rows = conn.execute("SELECT * FROM classrooms ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_classroom(classroom_id, db_path=None):
    conn = get_db(db_path)
    conn.execute("DELETE FROM classrooms WHERE id = ?", (classroom_id,))
    conn.commit()
    conn.close()


# --- Time Slots ---

def get_time_slots(db_path=None):
    conn = get_db(db_path)
    rows = conn.execute(
        "SELECT * FROM time_slots ORDER BY CASE day "
        "WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 "
        "WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 END, start_time"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_time_slot_template(db_path=None):
    """Returns the unique slot template from Monday (since all days are identical)."""
    conn = get_db(db_path)
    rows = conn.execute(
        "SELECT slot_order, start_time, end_time, slot_type, is_break "
        "FROM time_slots WHERE day = 'Monday' ORDER BY slot_order"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


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


def has_assignments(db_path=None):
    conn = get_db(db_path)
    count = conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
    conn.close()
    return count > 0


# --- Constraints ---

def add_constraint(teacher_id, time_slot_id, constraint_type='unavailable', db_path=None):
    conn = get_db(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO teacher_constraints (teacher_id, time_slot_id, constraint_type) "
        "VALUES (?, ?, ?)",
        (teacher_id, time_slot_id, constraint_type)
    )
    conn.commit()
    conn.close()


def get_constraints(teacher_id=None, db_path=None):
    conn = get_db(db_path)
    if teacher_id:
        rows = conn.execute(
            "SELECT tc.*, ts.day, ts.start_time, ts.end_time "
            "FROM teacher_constraints tc JOIN time_slots ts ON tc.time_slot_id = ts.id "
            "WHERE tc.teacher_id = ?", (teacher_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT tc.*, ts.day, ts.start_time, ts.end_time "
            "FROM teacher_constraints tc JOIN time_slots ts ON tc.time_slot_id = ts.id"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_constraint(constraint_id, db_path=None):
    conn = get_db(db_path)
    conn.execute("DELETE FROM teacher_constraints WHERE id = ?", (constraint_id,))
    conn.commit()
    conn.close()


# --- Subjects ---

def get_subjects(db_path=None):
    conn = get_db(db_path)
    rows = conn.execute("SELECT * FROM subjects ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_subject(name, db_path=None):
    conn = get_db(db_path)
    try:
        c = conn.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
        conn.commit()
        subject_id = c.lastrowid
        conn.close()
        return subject_id, None
    except sqlite3.IntegrityError:
        conn.close()
        return None, f'Subject "{name}" already exists'


def delete_subject(subject_id, db_path=None):
    conn = get_db(db_path)
    conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    conn.commit()
    conn.close()


# --- Teacher-Subject Mapping ---

def assign_subject_to_teacher(teacher_id, subject_id, db_path=None):
    conn = get_db(db_path)
    try:
        conn.execute(
            "INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)",
            (teacher_id, subject_id)
        )
        conn.commit()
        conn.close()
        return True, None
    except sqlite3.IntegrityError:
        conn.close()
        return False, 'Subject already assigned to this teacher'


def remove_subject_from_teacher(teacher_id, subject_id, db_path=None):
    conn = get_db(db_path)
    conn.execute(
        "DELETE FROM teacher_subjects WHERE teacher_id = ? AND subject_id = ?",
        (teacher_id, subject_id)
    )
    conn.commit()
    conn.close()


def get_teacher_subjects(teacher_id, db_path=None):
    conn = get_db(db_path)
    rows = conn.execute(
        "SELECT s.* FROM subjects s "
        "JOIN teacher_subjects ts ON s.id = ts.subject_id "
        "WHERE ts.teacher_id = ? ORDER BY s.name",
        (teacher_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_teachers_with_subjects(db_path=None):
    conn = get_db(db_path)
    teachers_rows = conn.execute("SELECT * FROM teachers ORDER BY name").fetchall()
    result = []
    for t in teachers_rows:
        teacher = dict(t)
        subs = conn.execute(
            "SELECT s.id, s.name FROM subjects s "
            "JOIN teacher_subjects ts ON s.id = ts.subject_id "
            "WHERE ts.teacher_id = ? ORDER BY s.name",
            (teacher['id'],)
        ).fetchall()
        teacher['subjects'] = [dict(s) for s in subs]
        grades = conn.execute(
            "SELECT g.id, g.name FROM grade_levels g "
            "JOIN teacher_grade_levels tg ON g.id = tg.grade_level_id "
            "WHERE tg.teacher_id = ? ORDER BY g.name",
            (teacher['id'],)
        ).fetchall()
        teacher['grade_levels'] = [dict(g) for g in grades]
        result.append(teacher)
    conn.close()
    return result


# --- Grade Levels ---

def get_grade_levels(db_path=None):
    conn = get_db(db_path)
    rows = conn.execute("SELECT * FROM grade_levels ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def assign_grade_to_teacher(teacher_id, grade_level_id, db_path=None):
    conn = get_db(db_path)
    try:
        conn.execute(
            "INSERT INTO teacher_grade_levels (teacher_id, grade_level_id) VALUES (?, ?)",
            (teacher_id, grade_level_id)
        )
        conn.commit()
        conn.close()
        return True, None
    except sqlite3.IntegrityError:
        conn.close()
        return False, 'Grade level already assigned to this teacher'


def remove_grade_from_teacher(teacher_id, grade_level_id, db_path=None):
    conn = get_db(db_path)
    conn.execute(
        "DELETE FROM teacher_grade_levels WHERE teacher_id = ? AND grade_level_id = ?",
        (teacher_id, grade_level_id)
    )
    conn.commit()
    conn.close()


# --- Assignments ---

def create_assignment(teacher_id, classroom_id, time_slot_id, subject='', is_manual=0, db_path=None):
    conn = get_db(db_path)
    # Check teacher not already assigned at this time slot
    conflict = conn.execute(
        "SELECT a.id, c.name as classroom, t.name as teacher "
        "FROM assignments a "
        "JOIN classrooms c ON a.classroom_id = c.id "
        "JOIN teachers t ON a.teacher_id = t.id "
        "WHERE a.teacher_id = ? AND a.time_slot_id = ?",
        (teacher_id, time_slot_id)
    ).fetchone()
    if conflict:
        conn.close()
        return None, f"Teacher already assigned to {conflict['classroom']} at this time"

    try:
        c = conn.execute(
            "INSERT INTO assignments (teacher_id, classroom_id, time_slot_id, subject, is_manual) "
            "VALUES (?, ?, ?, ?, ?)",
            (teacher_id, classroom_id, time_slot_id, subject, is_manual)
        )
        conn.commit()
        assignment_id = c.lastrowid
        conn.close()
        return assignment_id, None
    except sqlite3.IntegrityError:
        conn.close()
        return None, "Classroom already has a teacher assigned at this time slot"


def delete_assignment(assignment_id, db_path=None):
    conn = get_db(db_path)
    conn.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
    conn.commit()
    conn.close()


def get_full_schedule(db_path=None):
    conn = get_db(db_path)
    rows = conn.execute(
        "SELECT a.id, a.subject, a.is_manual, "
        "t.id as teacher_id, t.name as teacher_name, t.color as teacher_color, "
        "c.id as classroom_id, c.name as classroom_name, "
        "ts.id as time_slot_id, ts.day, ts.start_time, ts.end_time, ts.is_break "
        "FROM assignments a "
        "JOIN teachers t ON a.teacher_id = t.id "
        "JOIN classrooms c ON a.classroom_id = c.id "
        "JOIN time_slots ts ON a.time_slot_id = ts.id "
        "ORDER BY ts.day, ts.start_time, c.name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_schedule_for_teacher(teacher_id, db_path=None):
    conn = get_db(db_path)
    rows = conn.execute(
        "SELECT a.id, a.subject, a.is_manual, "
        "c.id as classroom_id, c.name as classroom_name, "
        "ts.id as time_slot_id, ts.day, ts.start_time, ts.end_time, ts.is_break "
        "FROM assignments a "
        "JOIN classrooms c ON a.classroom_id = c.id "
        "JOIN time_slots ts ON a.time_slot_id = ts.id "
        "WHERE a.teacher_id = ? "
        "ORDER BY ts.day, ts.start_time",
        (teacher_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_schedule_for_classroom(classroom_id, db_path=None):
    conn = get_db(db_path)
    rows = conn.execute(
        "SELECT a.id, a.subject, a.is_manual, "
        "t.id as teacher_id, t.name as teacher_name, t.color as teacher_color, "
        "ts.id as time_slot_id, ts.day, ts.start_time, ts.end_time, ts.is_break "
        "FROM assignments a "
        "JOIN teachers t ON a.teacher_id = t.id "
        "JOIN time_slots ts ON a.time_slot_id = ts.id "
        "WHERE a.classroom_id = ? "
        "ORDER BY ts.day, ts.start_time",
        (classroom_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def detect_conflicts(db_path=None):
    conn = get_db(db_path)
    # Find teachers assigned to multiple classrooms in the same time slot
    rows = conn.execute(
        "SELECT t.name as teacher_name, ts.day, ts.start_time, ts.end_time, "
        "GROUP_CONCAT(c.name) as classrooms, COUNT(*) as count "
        "FROM assignments a "
        "JOIN teachers t ON a.teacher_id = t.id "
        "JOIN classrooms c ON a.classroom_id = c.id "
        "JOIN time_slots ts ON a.time_slot_id = ts.id "
        "GROUP BY a.teacher_id, a.time_slot_id "
        "HAVING COUNT(*) > 1"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_auto_assignments(db_path=None):
    conn = get_db(db_path)
    conn.execute("DELETE FROM assignments WHERE is_manual = 0")
    conn.commit()
    conn.close()


# --- Seed sample data ---

def seed_sample_data(db_path=None):
    teachers = [
        ('Ms. Johnson', 'johnson@school.edu'),
        ('Mr. Smith', 'smith@school.edu'),
        ('Dr. Williams', 'williams@school.edu'),
        ('Mrs. Davis', 'davis@school.edu'),
        ('Mr. Garcia', 'garcia@school.edu'),
    ]
    classrooms = [
        ('Room 101', 30),
        ('Room 102', 25),
        ('Room 201', 35),
        ('Room 202', 20),
    ]

    for name, email in teachers:
        add_teacher(name, email, db_path=db_path)
    for name, cap in classrooms:
        add_classroom(name, cap, db_path=db_path)

    # Assign subjects to teachers
    subjects = get_subjects(db_path)
    sub_map = {s['name']: s['id'] for s in subjects}
    teacher_subject_assignments = {
        1: ['PE', 'SEL'],
        2: ['Music', 'Art'],
        3: ['Computer Science', 'Design'],
        4: ['Chinese', 'Thai'],
        5: ['PE', 'Music', 'Art'],
    }
    for tid, subs in teacher_subject_assignments.items():
        for s in subs:
            if s in sub_map:
                assign_subject_to_teacher(tid, sub_map[s], db_path=db_path)

    # Assign grade levels to teachers
    grades = get_grade_levels(db_path)
    grade_map = {g['name']: g['id'] for g in grades}
    teacher_grade_assignments = {
        1: ['G1', 'G2'],
        2: ['G2', 'G3'],
        3: ['G3', 'G4', 'G5'],
        4: ['G1', 'G4'],
        5: ['G1', 'G2', 'G3'],
    }
    for tid, glevels in teacher_grade_assignments.items():
        for g in glevels:
            if g in grade_map:
                assign_grade_to_teacher(tid, grade_map[g], db_path=db_path)

    print(f"Seeded {len(teachers)} teachers, {len(classrooms)} classrooms, subjects, and grade levels.")


if __name__ == '__main__':
    init_db()
    if '--seed' in sys.argv:
        seed_sample_data()
        print("Sample data seeded successfully.")
    else:
        print("Database initialized successfully.")
