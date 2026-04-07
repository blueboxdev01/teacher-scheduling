"""
Export utility for the Teacher Scheduling system.
Exports schedule data to CSV format.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from scheduler_db import get_full_schedule, DEFAULT_DB_PATH


def export_csv(db_path=None, output_path=None):
    db_path = db_path or DEFAULT_DB_PATH
    output_path = output_path or os.path.join(
        os.path.dirname(__file__), '..', '.tmp', 'schedule.csv'
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    schedule = get_full_schedule(db_path)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Day', 'Start Time', 'End Time', 'Teacher', 'Classroom', 'Subject', 'Manual Override'])

        for row in schedule:
            writer.writerow([
                row['day'],
                row['start_time'],
                row['end_time'],
                row['teacher_name'],
                row['classroom_name'],
                row['subject'],
                'Yes' if row['is_manual'] else 'No'
            ])

    print(f"Exported {len(schedule)} assignments to {output_path}")
    return output_path


if __name__ == '__main__':
    export_csv()
