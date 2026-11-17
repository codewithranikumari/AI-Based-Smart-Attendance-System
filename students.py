from database import get_connection


def add_student(name, roll_no, class_name, face_registered=False):
    name = str(name).strip()
    roll_no = str(roll_no).strip()
    class_name = str(class_name).strip()
    if not name or not roll_no or not class_name:
        raise ValueError("Name, roll number, and class are required.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO students (name, roll_no, class_name, face_registered)
            VALUES (?, ?, ?, ?)
            """,
            (name, roll_no, class_name, int(face_registered)),
        )
        return cursor.lastrowid


def list_students():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, roll_no, class_name, face_registered, created_at
            FROM students
            ORDER BY class_name COLLATE NOCASE, name COLLATE NOCASE
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_student_by_roll(roll_no):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name, roll_no, class_name, face_registered
            FROM students
            WHERE roll_no = ?
            """,
            (str(roll_no).strip(),),
        ).fetchone()
    return dict(row) if row else None


def get_student_by_id(student_id):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name, roll_no, class_name, face_registered
            FROM students
            WHERE id = ?
            """,
            (student_id,),
        ).fetchone()
    return dict(row) if row else None


def set_face_registered(student_id, registered):
    with get_connection() as connection:
        connection.execute(
            "UPDATE students SET face_registered = ? WHERE id = ?",
            (int(registered), student_id),
        )


def delete_student(student_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT roll_no FROM students WHERE id = ?",
            (student_id,),
        ).fetchone()
        if row is None:
            return None
        connection.execute("DELETE FROM students WHERE id = ?", (student_id,))
        return row["roll_no"]


def save_performance(student_id, term, marks):
    term = str(term).strip()
    marks = float(marks)
    if not term:
        raise ValueError("Enter a term or exam name.")
    if not 0 <= marks <= 100:
        raise ValueError("Marks must be between 0 and 100.")

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO performance (student_id, term, marks)
            VALUES (?, ?, ?)
            ON CONFLICT(student_id, term) DO UPDATE SET
                marks = excluded.marks,
                recorded_at = CURRENT_TIMESTAMP
            """,
            (student_id, term, marks),
        )


def get_performance(student_id):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT term, marks, recorded_at
            FROM performance
            WHERE student_id = ?
            ORDER BY recorded_at, id
            """,
            (student_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_performance():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT students.name, students.roll_no, students.class_name,
                   performance.term, performance.marks, performance.recorded_at
            FROM performance
            JOIN students ON students.id = performance.student_id
            ORDER BY students.class_name, students.name, performance.recorded_at
            """
        ).fetchall()
    return [dict(row) for row in rows]
