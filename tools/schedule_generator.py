"""
Schedule generation algorithm for the Teacher Scheduling system.
Uses a greedy approach with load balancing to assign teachers to classroom time slots.
Generates a uniform schedule for Monday, then replicates across all weekdays.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from scheduler_db import (
    get_db, get_teachers, get_classrooms, get_time_slots,
    get_constraints, get_full_schedule, create_assignment,
    clear_auto_assignments, detect_conflicts, DEFAULT_DB_PATH,
    get_teachers_with_subjects, get_sections, DAYS
)


def generate_schedule(db_path=None):
    db_path = db_path or DEFAULT_DB_PATH

    # Clear previous auto-generated assignments (keep manual ones)
    clear_auto_assignments(db_path)

    teachers = get_teachers_with_subjects(db_path)
    classrooms = get_classrooms(db_path)
    time_slots = get_time_slots(db_path)
    all_constraints = get_constraints(db_path=db_path)
    sections = get_sections(db_path=db_path)

    if not teachers or not classrooms:
        return {
            'assigned': 0,
            'unassigned': 0,
            'skipped_breaks': 0,
            'conflicts': [],
            'homeroom_assigned': 0,
            'message': 'Need at least one teacher and one classroom to generate a schedule.'
        }

    # Build constraint lookup
    unavailable = set()
    preferred = set()
    for c in all_constraints:
        if c['constraint_type'] == 'unavailable':
            unavailable.add((c['teacher_id'], c['time_slot_id']))
        elif c['constraint_type'] == 'preferred':
            preferred.add((c['teacher_id'], c['time_slot_id']))

    # Get existing manual assignments
    existing = get_full_schedule(db_path)
    teacher_slot_taken = set()
    classroom_slot_taken = set()
    for a in existing:
        teacher_slot_taken.add((a['teacher_id'], a['time_slot_id']))
        classroom_slot_taken.add((a['classroom_id'], a['time_slot_id']))

    teacher_load = {t['id']: 0 for t in teachers}
    for a in existing:
        teacher_load[a['teacher_id']] = teacher_load.get(a['teacher_id'], 0) + 1

    assigned = 0
    unassigned = 0
    skipped_breaks = 0
    homeroom_assigned = 0

    # Build slot lookup by day for replication later
    slots_by_day = {}
    for slot in time_slots:
        slots_by_day.setdefault(slot['day'], []).append(slot)

    # Use Monday as the template day
    monday_slots = [s for s in time_slots if s['day'] == 'Monday']
    if not monday_slots:
        return {
            'assigned': 0, 'unassigned': 0, 'skipped_breaks': 0,
            'conflicts': [], 'homeroom_assigned': 0,
            'message': 'No Monday time slots found.'
        }

    # Phase 1: Assign homeroom sessions for the first period (Monday only)
    first_slot = None
    for slot in monday_slots:
        if not slot['is_break']:
            first_slot = slot
            break

    monday_plan = []  # List of (teacher_id, classroom_id, slot_order, subject) for replication

    if first_slot:
        for section in sections:
            teacher_id = section['homeroom_teacher_id']
            classroom_id = section['classroom_id']
            if not teacher_id or not classroom_id:
                continue

            if (teacher_id, first_slot['id']) in teacher_slot_taken:
                continue
            if (classroom_id, first_slot['id']) in classroom_slot_taken:
                continue

            result, error = create_assignment(
                teacher_id, classroom_id, first_slot['id'],
                subject='Homeroom', is_manual=0, db_path=db_path
            )
            if result:
                homeroom_assigned += 1
                assigned += 1
                teacher_slot_taken.add((teacher_id, first_slot['id']))
                classroom_slot_taken.add((classroom_id, first_slot['id']))
                teacher_load[teacher_id] = teacher_load.get(teacher_id, 0) + 1
                monday_plan.append((teacher_id, classroom_id, first_slot['slot_order'], 'Homeroom'))

    # Phase 2: Fill remaining Monday slots with greedy assignment
    # Track which classroom each teacher was last assigned to (for variety)
    teacher_last_classroom = {}

    for slot in monday_slots:
        if slot['is_break']:
            skipped_breaks += len(classrooms)
            continue

        for classroom in classrooms:
            if (classroom['id'], slot['id']) in classroom_slot_taken:
                continue

            candidates = []
            for teacher in teachers:
                tid = teacher['id']
                if (tid, slot['id']) in unavailable:
                    continue
                if (tid, slot['id']) in teacher_slot_taken:
                    continue
                candidates.append(teacher)

            if not candidates:
                unassigned += 1
                continue

            # Sort by: preferred first, then avoid same classroom as last assignment, then least loaded
            def sort_key(t, _slot=slot, _classroom=classroom):
                is_preferred = 0 if (t['id'], _slot['id']) in preferred else 1
                # Penalize assigning to same classroom as last time
                same_classroom = 1 if teacher_last_classroom.get(t['id']) == _classroom['id'] else 0
                load = teacher_load.get(t['id'], 0)
                return (is_preferred, same_classroom, load)

            candidates.sort(key=sort_key)
            chosen = candidates[0]

            # Pick subject from teacher's assigned subjects (round-robin by load)
            subject = ''
            if chosen.get('subjects'):
                subject_index = teacher_load.get(chosen['id'], 0) % len(chosen['subjects'])
                subject = chosen['subjects'][subject_index]['name']

            result, error = create_assignment(
                chosen['id'], classroom['id'], slot['id'],
                subject=subject, is_manual=0, db_path=db_path
            )

            if result:
                assigned += 1
                teacher_slot_taken.add((chosen['id'], slot['id']))
                classroom_slot_taken.add((classroom['id'], slot['id']))
                teacher_load[chosen['id']] = teacher_load.get(chosen['id'], 0) + 1
                teacher_last_classroom[chosen['id']] = classroom['id']
                monday_plan.append((chosen['id'], classroom['id'], slot['slot_order'], subject))
            else:
                unassigned += 1

    # Phase 3: Replicate Monday's schedule to Tuesday-Friday
    other_days = [d for d in DAYS if d != 'Monday']
    for day in other_days:
        day_slots = slots_by_day.get(day, [])
        # Build slot_order -> slot mapping for this day
        order_to_slot = {s['slot_order']: s for s in day_slots}

        for teacher_id, classroom_id, slot_order, subject in monday_plan:
            target_slot = order_to_slot.get(slot_order)
            if not target_slot:
                continue
            if target_slot['is_break']:
                continue
            if (teacher_id, target_slot['id']) in teacher_slot_taken:
                continue
            if (classroom_id, target_slot['id']) in classroom_slot_taken:
                continue

            result, error = create_assignment(
                teacher_id, classroom_id, target_slot['id'],
                subject=subject, is_manual=0, db_path=db_path
            )
            if result:
                assigned += 1
                teacher_slot_taken.add((teacher_id, target_slot['id']))
                classroom_slot_taken.add((classroom_id, target_slot['id']))
                if subject == 'Homeroom':
                    homeroom_assigned += 1

    # Run conflict detection
    conflicts = detect_conflicts(db_path)

    return {
        'assigned': assigned,
        'unassigned': unassigned,
        'skipped_breaks': skipped_breaks,
        'conflicts': conflicts,
        'homeroom_assigned': homeroom_assigned,
        'message': f'Schedule generated: {assigned} assigned ({homeroom_assigned} homeroom), {unassigned} unassigned, {len(conflicts)} conflicts.'
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
