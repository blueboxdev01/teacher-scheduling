"""
Flask server for the Teacher Scheduling system.
Serves the web UI and exposes REST API endpoints.
"""

import os
import sys
import io
import csv

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify, send_from_directory, Response
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
from schedule_generator import generate_schedule, validate_schedule

app = Flask(__name__)

WEB_DIR = os.path.join(os.path.dirname(__file__), 'web')


# --- Static ---

@app.route('/')
def index():
    return send_from_directory(WEB_DIR, 'index.html')


@app.route('/teacher/<int:teacher_id>')
def teacher_dashboard(teacher_id):
    return send_from_directory(WEB_DIR, 'teacher.html')


# --- Teachers ---

@app.route('/api/teachers', methods=['GET'])
def api_get_teachers():
    return jsonify(get_teachers_with_subjects())


@app.route('/api/teachers', methods=['POST'])
def api_add_teacher():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    teacher_id = add_teacher(name, data.get('email', ''), data.get('color'))
    return jsonify({'id': teacher_id, 'message': f'Teacher "{name}" added.'})


@app.route('/api/teachers/<int:teacher_id>', methods=['PUT'])
def api_update_teacher(teacher_id):
    data = request.get_json()
    update_teacher(
        teacher_id,
        name=data.get('name'),
        email=data.get('email'),
        color=data.get('color')
    )
    return jsonify({'message': 'Teacher updated.'})


@app.route('/api/teachers/<int:teacher_id>', methods=['DELETE'])
def api_delete_teacher(teacher_id):
    delete_teacher(teacher_id)
    return jsonify({'message': 'Teacher deleted.'})


# --- Teacher Subjects ---

@app.route('/api/teachers/<int:teacher_id>/subjects', methods=['GET'])
def api_get_teacher_subjects(teacher_id):
    return jsonify(get_teacher_subjects(teacher_id))


@app.route('/api/teachers/<int:teacher_id>/subjects', methods=['POST'])
def api_assign_subject(teacher_id):
    data = request.get_json()
    subject_id = data.get('subject_id')
    if not subject_id:
        return jsonify({'error': 'subject_id is required'}), 400
    ok, error = assign_subject_to_teacher(teacher_id, subject_id)
    if error:
        return jsonify({'error': error}), 409
    return jsonify({'message': 'Subject assigned to teacher.'})


@app.route('/api/teachers/<int:teacher_id>/subjects/<int:subject_id>', methods=['DELETE'])
def api_remove_subject(teacher_id, subject_id):
    remove_subject_from_teacher(teacher_id, subject_id)
    return jsonify({'message': 'Subject removed from teacher.'})


# --- Subjects ---

@app.route('/api/subjects', methods=['GET'])
def api_get_subjects():
    return jsonify(get_subjects())


@app.route('/api/subjects', methods=['POST'])
def api_add_subject():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    subject_id, error = add_subject(name)
    if error:
        return jsonify({'error': error}), 409
    return jsonify({'id': subject_id, 'message': f'Subject "{name}" added.'})


@app.route('/api/subjects/<int:subject_id>', methods=['DELETE'])
def api_delete_subject(subject_id):
    delete_subject(subject_id)
    return jsonify({'message': 'Subject deleted.'})


# --- Grade Levels ---

@app.route('/api/gradelevels', methods=['GET'])
def api_get_grade_levels():
    return jsonify(get_grade_levels())


# --- Teacher Grade Levels ---

@app.route('/api/teachers/<int:teacher_id>/gradelevels', methods=['POST'])
def api_assign_grade(teacher_id):
    data = request.get_json()
    grade_level_id = data.get('grade_level_id')
    if not grade_level_id:
        return jsonify({'error': 'grade_level_id is required'}), 400
    ok, error = assign_grade_to_teacher(teacher_id, grade_level_id)
    if error:
        return jsonify({'error': error}), 409
    return jsonify({'message': 'Grade level assigned to teacher.'})


@app.route('/api/teachers/<int:teacher_id>/gradelevels/<int:grade_level_id>', methods=['DELETE'])
def api_remove_grade(teacher_id, grade_level_id):
    remove_grade_from_teacher(teacher_id, grade_level_id)
    return jsonify({'message': 'Grade level removed from teacher.'})


# --- Classrooms ---

@app.route('/api/classrooms', methods=['GET'])
def api_get_classrooms():
    return jsonify(get_classrooms())


@app.route('/api/classrooms', methods=['POST'])
def api_add_classroom():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    classroom_id = add_classroom(name, data.get('capacity', 30))
    return jsonify({'id': classroom_id, 'message': f'Classroom "{name}" added.'})


@app.route('/api/classrooms/<int:classroom_id>', methods=['DELETE'])
def api_delete_classroom(classroom_id):
    delete_classroom(classroom_id)
    return jsonify({'message': 'Classroom deleted.'})


# --- Time Slots ---

@app.route('/api/timeslots/template', methods=['GET'])
def api_get_template():
    return jsonify(get_time_slot_template())


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


@app.route('/api/assignments/exists', methods=['GET'])
def api_assignments_exist():
    return jsonify({'exists': has_assignments()})


@app.route('/api/timeslots', methods=['GET'])
def api_get_timeslots():
    return jsonify(get_time_slots())


# --- Constraints ---

@app.route('/api/constraints', methods=['POST'])
def api_add_constraint():
    data = request.get_json()
    teacher_id = data.get('teacher_id')
    time_slot_id = data.get('time_slot_id')
    constraint_type = data.get('constraint_type', 'unavailable')
    if not teacher_id or not time_slot_id:
        return jsonify({'error': 'teacher_id and time_slot_id are required'}), 400
    add_constraint(teacher_id, time_slot_id, constraint_type)
    return jsonify({'message': 'Constraint added.'})


@app.route('/api/constraints/<int:teacher_id>', methods=['GET'])
def api_get_constraints(teacher_id):
    return jsonify(get_constraints(teacher_id))


@app.route('/api/constraints/<int:constraint_id>', methods=['DELETE'])
def api_delete_constraint(constraint_id):
    delete_constraint(constraint_id)
    return jsonify({'message': 'Constraint deleted.'})


# --- Schedule ---

@app.route('/api/schedule', methods=['GET'])
def api_get_schedule():
    teacher_id = request.args.get('teacher_id', type=int)
    classroom_id = request.args.get('classroom_id', type=int)

    if teacher_id:
        return jsonify(get_schedule_for_teacher(teacher_id))
    elif classroom_id:
        return jsonify(get_schedule_for_classroom(classroom_id))
    else:
        return jsonify(get_full_schedule())


@app.route('/api/schedule/generate', methods=['POST'])
def api_generate_schedule():
    result = generate_schedule()
    return jsonify(result)


# --- Assignments ---

@app.route('/api/assignments', methods=['POST'])
def api_create_assignment():
    data = request.get_json()
    teacher_id = data.get('teacher_id')
    classroom_id = data.get('classroom_id')
    time_slot_id = data.get('time_slot_id')
    subject = data.get('subject', '')

    if not all([teacher_id, classroom_id, time_slot_id]):
        return jsonify({'error': 'teacher_id, classroom_id, and time_slot_id are required'}), 400

    assignment_id, error = create_assignment(
        teacher_id, classroom_id, time_slot_id, subject, is_manual=1
    )

    if error:
        return jsonify({'error': error}), 409
    return jsonify({'id': assignment_id, 'message': 'Assignment created.'})


@app.route('/api/assignments/<int:assignment_id>', methods=['DELETE'])
def api_delete_assignment(assignment_id):
    delete_assignment(assignment_id)
    return jsonify({'message': 'Assignment deleted.'})


# --- Conflicts ---

@app.route('/api/conflicts', methods=['GET'])
def api_get_conflicts():
    conflicts = detect_conflicts()
    return jsonify({
        'valid': len(conflicts) == 0,
        'conflicts': conflicts
    })


# --- Export ---

@app.route('/api/export/csv', methods=['GET'])
def api_export_csv():
    schedule = get_full_schedule()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Day', 'Start', 'End', 'Teacher', 'Classroom', 'Subject', 'Manual Override'])

    for row in schedule:
        writer.writerow([
            row['day'], row['start_time'], row['end_time'],
            row['teacher_name'], row['classroom_name'],
            row['subject'], 'Yes' if row['is_manual'] else 'No'
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=schedule.csv'}
    )


if __name__ == '__main__':
    init_db()
    print("Server starting at http://localhost:5000")
    app.run(debug=True, port=5000)
