import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import database
import face_recognition
import numpy as np
from PIL import Image
from attendance import attendance_analysis, daily_attendance, mark_attendance
from database import create_admin, create_tables, has_admins, verify_admin
from prediction import predict_performance
from students import add_student, delete_student, get_performance, save_performance


class SmartAttendanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_database_path = database.DATABASE_PATH
        database.DATABASE_PATH = os.path.join(
            self.temporary_directory.name, "test_attendance.db"
        )
        create_tables()

    def tearDown(self):
        database.DATABASE_PATH = self.original_database_path
        self.temporary_directory.cleanup()

    def test_admin_password_is_stored_as_a_hash(self):
        self.assertFalse(has_admins())
        create_admin("teacher", "safe-password")
        self.assertTrue(verify_admin("teacher", "safe-password"))
        self.assertFalse(verify_admin("teacher", "wrong-password"))

        with database.get_connection() as connection:
            stored_value = connection.execute(
                "SELECT password_hash FROM admins WHERE username = ?",
                ("teacher",),
            ).fetchone()["password_hash"]
        self.assertNotEqual(stored_value, "safe-password")

    def test_daily_attendance_and_analysis(self):
        add_student("Asha", "A-1", "10A")
        add_student("Ravi", "A-2", "10A")

        first_day = datetime(2026, 1, 5, 9, 0)
        second_day = datetime(2026, 1, 6, 9, 0)
        self.assertEqual(mark_attendance("A-1", first_day), "Attendance marked successfully.")
        self.assertEqual(mark_attendance("A-1", first_day), "Attendance was already marked today.")
        self.assertEqual(mark_attendance("A-2", second_day), "Attendance marked successfully.")

        daily = {row["roll_no"]: row["status"] for row in daily_attendance(first_day.date())}
        self.assertEqual(daily, {"A-1": "Present", "A-2": "Absent"})

        results = attendance_analysis().set_index("Roll number")
        self.assertEqual(results.loc["A-1", "Attendance %"], 50)
        self.assertEqual(results.loc["A-2", "Attendance %"], 50)

    def test_performance_history_and_prediction(self):
        student_id = add_student("Meera", "B-1", "9B")
        save_performance(student_id, "Term 1", 60)
        save_performance(student_id, "Term 2", 70)
        save_performance(student_id, "Term 2", 75)

        history = get_performance(student_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]["marks"], 75)
        result = predict_performance([row["marks"] for row in history], 90)
        self.assertEqual(result["predicted_score"], 90)
        self.assertEqual(result["status"], "On track")

        not_enough_history = predict_performance([60], 90)
        self.assertIsNone(not_enough_history["predicted_score"])

        self.assertEqual(delete_student(student_id), "B-1")
        self.assertEqual(get_performance(student_id), [])

    def test_face_photo_registration_and_match_use_roll_number(self):
        original_folder = face_recognition.FACE_FOLDER
        face_recognition.FACE_FOLDER = self.temporary_directory.name
        prepared_face = np.tile(np.arange(160, dtype=np.uint8), (160, 1))
        try:
            photo = Image.new("RGB", (32, 32), color="white")
            with patch.object(
                face_recognition, "_prepare_face", return_value=prepared_face
            ):
                face_recognition.register_face_photo("C-1", photo)
                self.assertTrue(
                    os.path.isfile(
                        os.path.join(self.temporary_directory.name, "C-1", "face.jpg")
                    )
                )
                self.assertEqual(face_recognition.recognize_face(photo), "C-1")
        finally:
            face_recognition.FACE_FOLDER = original_folder


if __name__ == "__main__":
    unittest.main()
