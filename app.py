import os
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

from attendance import (
    attendance_analysis,
    attendance_records,
    daily_attendance,
    mark_attendance,
    student_attendance_summary,
)
from database import create_admin, create_tables, has_admins, list_admins, verify_admin
from face_recognition import (
    FACE_FOLDER,
    delete_face_profile,
    recognize_face,
    register_face_photo,
)
from prediction import predict_performance
from students import (
    add_student,
    delete_student,
    get_performance,
    get_student_by_roll,
    list_students,
    save_performance,
    set_face_registered,
)


PAGE_COLORS = {
    "Dashboard": ("#16A6A1", "Your school at a glance"),
    "Students": ("#F08B52", "Student profiles and face enrollment"),
    "Take attendance": ("#7C6FE8", "Fast, verified daily check-in"),
    "Attendance records": ("#3985D6", "Search and export attendance"),
    "Attendance analysis": ("#D45D8C", "Spot patterns and students needing support"),
    "Performance forecast": ("#57A773", "Review marks and estimate a trend"),
    "Admin settings": ("#D2A43A", "Manage access to the admin panel"),
}


def _apply_theme():
    st.markdown(
        """
        <style>
        .stApp { background: #f5f7fb; }
        [data-testid="stSidebar"] {
            background: linear-gradient(175deg, #16243d 0%, #243852 100%);
        }
        [data-testid="stSidebar"] * { color: #eef4ff; }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e6ebf2;
            border-radius: 14px;
            padding: 14px 16px;
            box-shadow: 0 3px 12px rgba(27, 44, 71, .05);
        }
        div.stButton > button[kind="primary"] {
            border: 0;
            border-radius: 9px;
            font-weight: 650;
        }
        div.stButton > button { border-radius: 9px; }
        .page-banner {
            background: #ffffff;
            border: 1px solid #e6ebf2;
            border-left: 6px solid var(--page-accent);
            border-radius: 13px;
            padding: 18px 22px;
            margin: 4px 0 22px;
        }
        .page-banner h1 { margin: 0; color: #17243b; font-size: 1.8rem; }
        .page-banner p { margin: 5px 0 0; color: #627087; }
        .small-note { color: #627087; font-size: .92rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _page_header(title, description):
    accent, _ = PAGE_COLORS[title]
    st.markdown(
        f"""
        <div class="page-banner" style="--page-accent: {accent}">
            <h1>{title}</h1>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_first_admin_setup():
    st.title("Welcome to Smart Attendance")
    st.write("Create the first admin account to set up your attendance workspace.")
    st.info("Your records are stored locally in `smart_attendance.db`.")

    with st.form("first_admin_form"):
        username = st.text_input("Admin username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create admin account", type="primary")

    if submitted:
        if password != confirm_password:
            st.error("The passwords do not match.")
        else:
            try:
                create_admin(username, password)
            except ValueError as error:
                st.error(str(error))
            except sqlite3.IntegrityError:
                st.error("That username is already in use.")
            else:
                st.session_state["authenticated"] = True
                st.session_state["admin_username"] = username.strip()
                st.rerun()


def _render_login():
    st.title("Smart Attendance")
    st.write("Sign in to open the admin panel.")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")

    if submitted:
        if verify_admin(username, password):
            st.session_state["authenticated"] = True
            st.session_state["admin_username"] = username.strip()
            st.rerun()
        else:
            st.error("Username or password is incorrect.")


def _render_sidebar():
    st.sidebar.markdown("## ✦ Smart Attendance")
    st.sidebar.caption("ADMIN WORKSPACE")
    username = st.session_state.get("admin_username", "Admin")
    st.sidebar.write(f"Signed in as **{username}**")
    page = st.sidebar.radio("Go to", list(PAGE_COLORS))
    st.sidebar.divider()
    st.sidebar.caption(f"Face photos: `{os.path.basename(FACE_FOLDER)}\\`")
    if st.sidebar.button("Log out", width="stretch"):
        st.session_state["authenticated"] = False
        st.session_state.pop("admin_username", None)
        st.rerun()
    return page


def _student_table(students):
    if not students:
        st.info("No students registered yet.")
        return
    table = [
        {
            "Name": student["name"],
            "Roll number": student["roll_no"],
            "Class": student["class_name"],
            "Face enrolled": "Yes" if student["face_registered"] else "No",
        }
        for student in students
    ]
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")
    csv_data = pd.DataFrame(table).to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download student list",
        csv_data,
        file_name="students.csv",
        mime="text/csv",
    )


def _render_dashboard():
    _page_header("Dashboard", PAGE_COLORS["Dashboard"][1])
    students = list_students()
    today_records = daily_attendance()
    present_today = sum(row["status"] == "Present" for row in today_records)
    absent_today = len(today_records) - present_today
    analysis = attendance_analysis()
    average_attendance = (
        float(analysis["Attendance %"].mean()) if not analysis.empty else 0
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Students", len(students))
    col2.metric("Present today", present_today)
    col3.metric("Absent today", absent_today)
    col4.metric("Average attendance", f"{average_attendance:.1f}%")

    st.subheader("Today's roll call")
    if today_records:
        today_table = [
            {
                "Name": row["name"],
                "Roll number": row["roll_no"],
                "Class": row["class_name"],
                "Status": row["status"],
                "Time": row["attendance_time"] or "—",
            }
            for row in today_records
        ]
        st.dataframe(pd.DataFrame(today_table), hide_index=True, width="stretch")
    else:
        st.info("Register students to start taking attendance.")

    st.caption(
        "Attendance percentage is based on days when at least one attendance record was saved."
    )


def _render_students():
    _page_header("Students", PAGE_COLORS["Students"][1])
    st.warning(
        "Face photos are biometric data. Get permission before enrollment. "
        "Photos stay on this computer and are removed when the student is deleted."
    )

    st.subheader("Add a student")
    col1, col2, col3 = st.columns(3)
    name = col1.text_input("Full name", key="new_student_name")
    roll_no = col2.text_input("Roll number", key="new_student_roll")
    class_name = col3.text_input("Class", key="new_student_class")
    enroll_face = st.checkbox("Enroll a face photo now (optional)", key="enroll_face")

    photo = None
    consent = False
    if enroll_face:
        consent = st.checkbox(
            "I have permission to capture and store this face photo.",
            key="face_consent",
        )
        photo = st.camera_input("Take a clear, front-facing photo", key="student_camera")

    if st.button("Add student", type="primary"):
        if not name.strip() or not roll_no.strip() or not class_name.strip():
            st.error("Enter the student's name, roll number, and class.")
        elif get_student_by_roll(roll_no):
            st.error("That roll number is already registered.")
        elif enroll_face and not consent:
            st.error("Confirm permission before enrolling a face photo.")
        elif enroll_face and photo is None:
            st.error("Take a photo, or turn off face enrollment to add the student manually.")
        else:
            face_saved = False
            try:
                if enroll_face:
                    register_face_photo(roll_no, photo)
                    face_saved = True
                add_student(name, roll_no, class_name, face_registered=face_saved)
            except (OSError, RuntimeError, ValueError, sqlite3.IntegrityError) as error:
                if face_saved:
                    delete_face_profile(roll_no)
                st.error(f"Student was not added: {error}")
            else:
                st.success(f"{name.strip()} was added.")
                st.rerun()

    students = list_students()
    st.subheader("Student list")
    _student_table(students)

    without_face = [student for student in students if not student["face_registered"]]
    if without_face:
        st.subheader("Enroll a face for an existing student")
        selected = st.selectbox(
            "Choose student",
            without_face,
            format_func=lambda student: (
                f"{student['name']} — {student['roll_no']}"
            ),
            key="enroll_existing_student",
        )
        existing_consent = st.checkbox(
            "I have permission to capture and store this face photo.",
            key="existing_face_consent",
        )
        existing_photo = st.camera_input(
            "Take a clear, front-facing photo",
            key="existing_student_camera",
        )
        if st.button("Save face photo"):
            if not existing_consent:
                st.error("Confirm permission before enrolling a face photo.")
            elif existing_photo is None:
                st.error("Take a photo before saving.")
            else:
                face_saved = False
                try:
                    register_face_photo(selected["roll_no"], existing_photo)
                    face_saved = True
                    set_face_registered(selected["id"], True)
                except (OSError, RuntimeError, ValueError, sqlite3.Error) as error:
                    if face_saved:
                        delete_face_profile(selected["roll_no"])
                    st.error(str(error))
                else:
                    st.success("Face photo enrolled.")
                    st.rerun()

    if students:
        st.subheader("Remove a student")
        st.caption("Removing a student also deletes their marks, attendance, and face photo.")
        selected_id = st.selectbox(
            "Student to remove",
            [student["id"] for student in students],
            format_func=lambda student_id: next(
                f"{student['name']} — {student['roll_no']}"
                for student in students
                if student["id"] == student_id
            ),
        )
        confirm_delete = st.checkbox("I understand this cannot be undone.")
        if st.button("Remove selected student"):
            if not confirm_delete:
                st.error("Confirm before removing the student.")
            else:
                removed_roll = delete_student(selected_id)
                if removed_roll:
                    delete_face_profile(removed_roll)
                    st.success("Student and related records removed.")
                    st.rerun()


def _render_attendance():
    _page_header("Take attendance", PAGE_COLORS["Take attendance"][1])
    st.caption("OpenCV suggests a student; an admin must visually confirm every match.")
    mode = st.radio(
        "Check-in method",
        ["OpenCV face match", "Choose student manually"],
        horizontal=True,
    )

    students = list_students()
    if not students:
        st.info("Add students before taking attendance.")
        return

    if mode == "OpenCV face match":
        photo = st.camera_input("Take an attendance photo", key="attendance_camera")
        if st.button("Find student", type="primary"):
            st.session_state.pop("attendance_candidate", None)
            try:
                st.session_state["attendance_candidate"] = recognize_face(photo)
            except (OSError, RuntimeError, ValueError) as error:
                st.error(f"Face matching could not run: {error}")

        candidate_roll = st.session_state.get("attendance_candidate")
        if candidate_roll is None:
            st.info("Take a photo and select Find student.")
            return
        student = get_student_by_roll(candidate_roll)
        if student is None:
            st.warning("No registered student matched this photo.")
            return

        st.success(
            f"Possible match: **{student['name']}** — "
            f"{student['roll_no']} ({student['class_name']})"
        )
        verified = st.checkbox("I have checked the person's identity.")
        if st.button("Confirm and mark present", type="primary"):
            if not verified:
                st.error("Please visually verify the person first.")
            else:
                result = mark_attendance(student["roll_no"])
                st.success(result) if result == "Attendance marked successfully." else st.warning(result)
                if result == "Attendance marked successfully.":
                    st.session_state.pop("attendance_candidate", None)
    else:
        student = st.selectbox(
            "Select student",
            students,
            format_func=lambda row: f"{row['name']} — {row['roll_no']} ({row['class_name']})",
        )
        if st.button("Mark selected student present", type="primary"):
            result = mark_attendance(student["roll_no"])
            st.success(result) if result == "Attendance marked successfully." else st.warning(result)


def _render_records():
    _page_header("Attendance records", PAGE_COLORS["Attendance records"][1])
    classes = sorted({student["class_name"] for student in list_students()})
    class_filter = st.selectbox("Class", ["All classes"] + classes)
    col1, col2 = st.columns(2)
    start_day = col1.date_input("From", value=date.today())
    end_day = col2.date_input("To", value=date.today())

    if start_day > end_day:
        st.error("The start date must be on or before the end date.")
        return

    rows = attendance_records(
        start_date=start_day.isoformat(),
        end_date=end_day.isoformat(),
        class_name=class_filter,
    )
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        csv_data = pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Download these records",
            csv_data,
            file_name="attendance_records.csv",
            mime="text/csv",
        )
    else:
        st.info("No attendance records match these filters.")

    st.subheader("Daily status")
    selected_day = st.date_input("Show present and absent students for", value=date.today())
    daily_rows = daily_attendance(selected_day)
    if class_filter != "All classes":
        daily_rows = [row for row in daily_rows if row["class_name"] == class_filter]
    daily_table = [
        {
            "Name": row["name"],
            "Roll number": row["roll_no"],
            "Class": row["class_name"],
            "Status": row["status"],
            "Time": row["attendance_time"] or "—",
        }
        for row in daily_rows
    ]
    st.dataframe(pd.DataFrame(daily_table), hide_index=True, width="stretch")


def _render_analysis():
    _page_header("Attendance analysis", PAGE_COLORS["Attendance analysis"][1])
    analysis = attendance_analysis()
    if analysis.empty:
        st.info("Attendance analysis will appear after the first check-in.")
        return

    classes = ["All classes"] + sorted(analysis["Class"].unique().tolist())
    selected_class = st.selectbox("Class", classes)
    if selected_class != "All classes":
        analysis = analysis[analysis["Class"] == selected_class]

    average = float(analysis["Attendance %"].mean()) if not analysis.empty else 0
    at_risk = int((analysis["Attendance %"] < 75).sum())
    col1, col2, col3 = st.columns(3)
    col1.metric("Students shown", len(analysis))
    col2.metric("Average attendance", f"{average:.1f}%")
    col3.metric("Below 75%", at_risk)

    st.bar_chart(
        analysis.set_index("Roll number")[["Attendance %"]],
        color=PAGE_COLORS["Attendance analysis"][0],
    )
    st.dataframe(analysis, hide_index=True, width="stretch")
    st.caption(
        "Percentages use the number of dates with at least one saved attendance record."
    )


def _render_performance():
    _page_header("Performance forecast", PAGE_COLORS["Performance forecast"][1])
    st.info(
        "This simple, explainable estimate projects a trend from a student's recent marks "
        "and attendance. It is not a trained model or a guarantee of academic results."
    )
    students = list_students()
    if not students:
        st.info("Add students before recording marks.")
        return

    student = st.selectbox(
        "Student",
        students,
        format_func=lambda row: f"{row['name']} — {row['roll_no']}",
    )
    with st.form("record_marks"):
        term = st.text_input("Term or exam name", placeholder="For example: Term 1")
        marks = st.number_input("Marks out of 100", min_value=0.0, max_value=100.0, step=1.0)
        save_marks = st.form_submit_button("Save marks")
    if save_marks:
        try:
            save_performance(student["id"], term, marks)
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("Marks saved. Saving the same term again updates that result.")
            st.rerun()

    history = get_performance(student["id"])
    attendance = student_attendance_summary(student["id"])
    forecast = predict_performance(
        [record["marks"] for record in history],
        attendance["percentage"],
    )
    score_label = (
        f"{forecast['predicted_score']:.1f}/100"
        if forecast["predicted_score"] is not None
        else "Add 2 marks"
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Estimated next mark", score_label)
    col2.metric("Indicator", forecast["status"])
    col3.metric("Attendance", f"{attendance['percentage']:.1f}%")
    st.caption(f"{forecast['confidence']}. {forecast['explanation']}")

    st.subheader("Recorded marks")
    if history:
        chart_data = pd.DataFrame(
            {"Marks": [record["marks"] for record in history]},
            index=[record["term"] for record in history],
        )
        st.line_chart(chart_data, color=PAGE_COLORS["Performance forecast"][0])
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Term": record["term"],
                        "Marks": record["marks"],
                        "Recorded": record["recorded_at"],
                    }
                    for record in history
                ]
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("Record marks for at least two terms to see a forecast.")


def _render_admin_settings():
    _page_header("Admin settings", PAGE_COLORS["Admin settings"][1])
    st.subheader("Admin accounts")
    admins = list_admins()
    st.dataframe(
        pd.DataFrame(
            [
                {"Username": admin["username"], "Created": admin["created_at"]}
                for admin in admins
            ]
        ),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Add another admin")
    with st.form("add_admin_form"):
        username = st.text_input("New username")
        password = st.text_input("New password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create admin")
    if submitted:
        if password != confirm:
            st.error("The passwords do not match.")
        else:
            try:
                create_admin(username, password)
            except ValueError as error:
                st.error(str(error))
            except sqlite3.IntegrityError:
                st.error("That username is already in use.")
            else:
                st.success("Admin account created.")
                st.rerun()

    st.divider()
    st.caption(
        "Database: `smart_attendance.db` · Face photos: `known_faces` · "
        "Keep both private and back them up securely."
    )


def main():
    st.set_page_config(
        page_title="Smart Attendance",
        page_icon="✦",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _apply_theme()
    try:
        create_tables()
    except sqlite3.Error as error:
        st.error(f"Could not open the local attendance database: {error}")
        st.stop()

    st.session_state.setdefault("authenticated", False)
    if st.session_state.get("authenticated") and not st.session_state.get("admin_username"):
        st.session_state["authenticated"] = False
    if not has_admins():
        _render_first_admin_setup()
        st.stop()
    if not st.session_state["authenticated"]:
        _render_login()
        st.stop()

    page = _render_sidebar()
    if page == "Dashboard":
        _render_dashboard()
    elif page == "Students":
        _render_students()
    elif page == "Take attendance":
        _render_attendance()
    elif page == "Attendance records":
        _render_records()
    elif page == "Attendance analysis":
        _render_analysis()
    elif page == "Performance forecast":
        _render_performance()
    else:
        _render_admin_settings()


main()
