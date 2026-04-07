"""
Schedule generation algorithm for the Teacher Scheduling system.
Uses a greedy approach with load balancing to assign teachers to classroom time slots.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from scheduler_db import (
    get_db, get_teachers, get_classrooms, get_time_slots,
    get_constraints, get_full_schedule, create_assignment,
    clear_auto_assignments, detect_conflicts, DEFAULT_DB_PATH,
    get_teachers_with_subjects
)


def generate_schedule(db_path=None):
    db_path = db_path or DEFAULT_DB_PATH

    # Clear previous auto-generated assignments (keep manual ones)
    clear_auto_assignments(db_path)

    teachers = get_teachers_with_subjects(db_path)
    classrooms = get_classrooms(db_path)
    time_slots = get_time_slots(db_path)
    all_constraints = get_constraints(db_path=db_path)

    if not teachers or not classrooms:
        return {
            'assigned': 0,
            'unassigned': 0,
            'skipped_breaks': 0,
            'conflicts': [],
            'message': 'Need at least one teacher and one classroom to generate a schedule.'
        }

    # Build constraint lookup: set of (teacher_id, time_slot_id) that are unavailable
    unavailable = set()
    for c in all_constraints:
        if c['constraint_type'] == 'unavailable':
            unavailable.add((c['teacher_id'], c['time_slot_id']))

    # Build preferred lookup
    preferred = set()
    for c in all_constraints:
        if c['constraint_type'] == 'preferred':
            preferred.add((c['teacher_id'], c['time_slot_id']))

    # Get existing manual assignments to know what's already taken
    existing = get_full_schedule(db_path)
    teacher_slot_taken = set()  # (teacher_id, time_slot_id) pairs already assigned
    classroom_slot_taken = set()  # (classroom_id, time_slot_id) pairs already assigned

    for a in existing:
        teacher_slot_taken.add((a['teacher_id'], a['time_slot_id']))
        classroom_slot_taken.add((a['classroom_id'], a['time_slot_id']))

    # Track assignment counts for load balancing
    teacher_load = {t['id']: 0 for t in teachers}
    for a in existing:
        teacher_load[a['teacher_id']] = teacher_load.get(a['teacher_id'], 0) + 1

    assigned = 0
    unassigned = 0
    skipped_breaks = 0

    # Iterate over each (classroom, time_slot) pair
    for slot in time_slots:
        if slot['is_break']:
            skipped_breaks += len(classrooms)
            continue

        for classroom in classrooms:
            # Skip if already assigned (manual override)
            if (classroom['id'], slot['id']) in classroom_slot_taken:
                continue

            # Find available teachers for this slot
            candidates = []
            for teacher in teachers:
                tid = teacher['id']
                # Teacher must not be unavailable
                if (tid, slot['id']) in unavailable:
                    continue
                # Teacher must not already be teaching at this time
                if (tid, slot['id']) in teacher_slot_taken:
                    continue
                candidates.append(teacher)

            if not candidates:
                unassigned += 1
                continue

            # Sort by: preferred first, then least loaded
            def sort_key(t):
                is_preferred = 0 if (t['id'], slot['id']) in preferred else 1
                load = teacher_load.get(t['id'], 0)
                return (is_preferred, load)

            candidates.sort(key=sort_key)
            chosen = candidates[0]

            # Pick a subject from teacher's assigned subjects (round-robin)
            subject = ''
            if chosen.get('subjects'):
                subject_index = teacher_load.get(chosen['id'], 0) % len(chosen['subjects'])
                subject = chosen['subjects'][subject_index]['name']

            # Create the assignment
            result, error = create_assignment(
                chosen['id'], classroom['id'], slot['id'],
                subject=subject, is_manual=0, db_path=db_path
            )

            if result:
                assigned += 1
                teacher_slot_taken.add((chosen['id'], slot['id']))
                classroom_slot_taken.add((classroom['id'], slot['id']))
                teacher_load[chosen['id']] = teacher_load.get(chosen['id'], 0) + 1
            else:
                unassigned += 1

    # Run conflict detection
    conflicts = detect_conflicts(db_path)

    return {
        'assigned': assigned,
        'unassigned': unassigned,
        'skipped_breaks': skipped_breaks,
        'conflicts': conflicts,
        'message': f'Schedule generated: {assigned} assigned, {unassigned} unassigned, {len(conflicts)} conflicts.'
    }


def validate_schedule(db_path=None):
    db_path = db_path or DEFAULT_DB_PATH
    conflicts = detect_conflicts(db_path)
    return {
        'valid': len(conflicts) == 0,
        'conflicts': conflicts,
        'message': 'No conflicts found.' if not conflicts else f'{len(conflicts)} conflict(s) detected.'
    }


if __name__ == '__main__':
    result = generate_schedule()
    print(result['message'])
    if result['conflicts']:
        print("Conflicts:")
        for c in result['conflicts']:
            print(f"  {c['teacher_name']} at {c['day']} {c['start_time']}-{c['end_time']}: {c['classrooms']}")
