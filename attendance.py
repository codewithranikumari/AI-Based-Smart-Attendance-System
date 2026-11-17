from datetime import date, datetime

import pandas as pd

from database import get_connection


def mark_attendance(roll_no, marked_at=None):
    marked_at = marked_at or datetime.now()
    attendance_date = marked_at.date().isoformat()
    attendance_time = marked_at.strftime("%H:%M:%S")

    with get_connection() as connection:
        student = connection.execute(
            "SELECT id FROM students WHERE roll_no = ?",
            (str(roll_no).strip(),),
        ).fetchone()
        if student is None:
            return "Student not found."

        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO attendance
                (student_id, attendance_date, attendance_time, status)
            VALUES (?, ?, ?, 'Present')
            """,
            (student["id"], attendance_date, attendance_time),
        )
        if cursor.rowcount == 0:
            return "Attendance was already marked today."

    return "Attendance marked successfully."


def attendance_records(start_date=None, end_date=None, class_name=None):
    conditions = []
    parameters = []
    if start_date:
        conditions.append("attendance.attendance_date >= ?")
        parameters.append(str(start_date))
    if end_date:
        conditions.append("attendance.attendance_date <= ?")
        parameters.append(str(end_date))
    if class_name and class_name != "All classes":
        conditions.append("students.class_name = ?")
        parameters.append(class_name)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT students.name AS Name,
                   students.roll_no AS Roll,
                   students.class_name AS Class,
                   attendance.attendance_date AS Date,
                   attendance.attendance_time AS Time,
                   attendance.status AS Status
            FROM attendance
            JOIN students ON students.id = attendance.student_id
            {where_clause}
            ORDER BY attendance.attendance_date DESC,
                     attendance.attendance_time DESC
            """,
            parameters,
        ).fetchall()
    return [dict(row) for row in rows]


def daily_attendance(day=None):
    day = day or date.today()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT students.id, students.name, students.roll_no, students.class_name,
                   CASE WHEN attendance.id IS NULL THEN 'Absent' ELSE 'Present' END AS status,
                   attendance.attendance_time
            FROM students
            LEFT JOIN attendance
              ON attendance.student_id = students.id
             AND attendance.attendance_date = ?
            ORDER BY students.class_name, students.name
            """,
            (day.isoformat(),),
        ).fetchall()
    return [dict(row) for row in rows]


def attendance_analysis():
    with get_connection() as connection:
        total_days = connection.execute(
            "SELECT COUNT(DISTINCT attendance_date) FROM attendance"
        ).fetchone()[0]
        rows = connection.execute(
            """
            SELECT students.name, students.roll_no, students.class_name,
                   COUNT(attendance.id) AS present_days
            FROM students
            LEFT JOIN attendance ON attendance.student_id = students.id
            GROUP BY students.id
            ORDER BY students.class_name, students.name
            """
        ).fetchall()

    analysis = []
    for row in rows:
        percentage = (
            100 * row["present_days"] / total_days if total_days else 0
        )
        analysis.append(
            {
                "Name": row["name"],
                "Roll number": row["roll_no"],
                "Class": row["class_name"],
                "Present days": row["present_days"],
                "Recorded days": total_days,
                "Attendance %": round(percentage, 1),
                "Status": "Needs attention" if percentage < 75 else "On track",
            }
        )
    return pd.DataFrame(analysis)


def student_attendance_summary(student_id):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(attendance.id) AS present_days
            FROM attendance
            WHERE student_id = ?
            """,
            (student_id,),
        ).fetchone()
        total_days = connection.execute(
            "SELECT COUNT(DISTINCT attendance_date) FROM attendance"
        ).fetchone()[0]

    present_days = row["present_days"]
    percentage = 100 * present_days / total_days if total_days else 0
    return {
        "present_days": present_days,
        "recorded_days": total_days,
        "percentage": round(percentage, 1),
    }


def view_attendance():
    return pd.DataFrame(attendance_records())
