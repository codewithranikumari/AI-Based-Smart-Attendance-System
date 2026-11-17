import os
import tempfile
import unittest

import database
from database import create_admin, create_tables
from streamlit.testing.v1 import AppTest


class AppSessionStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_database_path = database.DATABASE_PATH
        database.DATABASE_PATH = os.path.join(
            self.temporary_directory.name, "session_test.db"
        )
        create_tables()
        create_admin("teacher", "safe-password")

    def tearDown(self):
        database.DATABASE_PATH = self.original_database_path
        self.temporary_directory.cleanup()

    def test_incomplete_authenticated_session_returns_to_login(self):
        app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
        app = AppTest.from_file(app_path)
        app.session_state["authenticated"] = True
        app.run(timeout=45)

        self.assertFalse(app.exception)
        self.assertFalse(app.session_state["authenticated"])
        self.assertEqual([field.label for field in app.text_input], ["Username", "Password"])


if __name__ == "__main__":
    unittest.main()
