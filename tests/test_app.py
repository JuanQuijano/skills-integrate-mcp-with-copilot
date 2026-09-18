import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.app as app_module


class ActivityDashboardTests(unittest.TestCase):
    def setUp(self):
        app_module.sessions.clear()
        app_module.notifications.clear()
        app_module.notification_id = 0
        app_module.activities.clear()
        app_module.activities.update(copy.deepcopy(app_module.DEFAULT_ACTIVITIES))
        app_module.activity_history.clear()
        app_module.activity_history.update(app_module.build_activity_history())
        self.student_user = {"email": "student@mergington.edu", "role": "student"}
        self.staff_user = {"email": "teacher@mergington.edu", "role": "staff"}

    def test_signup_updates_dashboard_history_and_notifications(self):
        signup_response = app_module.signup_for_activity(
            "Chess Club",
            "student@mergington.edu",
            user=self.student_user,
        )

        self.assertEqual(signup_response["seats_remaining"], 9)

        student_notifications = app_module.get_notifications(user=self.student_user)
        self.assertIn(
            "confirmed for Chess Club",
            student_notifications["notifications"][0]["message"],
        )

        dashboard_response = app_module.get_coordinator_dashboard(user=self.staff_user)
        chess_club = next(
            activity
            for activity in dashboard_response["activities"]
            if activity["name"] == "Chess Club"
        )
        self.assertEqual(chess_club["participants_count"], 3)
        self.assertEqual(chess_club["seats_remaining"], 9)
        self.assertEqual(chess_club["history"][-1]["participant_count"], 3)

    def test_full_activity_generates_coordinator_notification(self):
        app_module.activities["Math Club"]["participants"] = [
            f"student{i}@mergington.edu" for i in range(9)
        ]
        app_module.activity_history["Math Club"] = [
            {"timestamp": app_module.current_timestamp(), "participant_count": 9}
        ]

        signup_response = app_module.signup_for_activity(
            "Math Club",
            "student@mergington.edu",
            user=self.student_user,
        )

        self.assertEqual(signup_response["seats_remaining"], 0)

        coordinator_notifications = app_module.get_notifications(user=self.staff_user)
        messages = [
            notification["message"]
            for notification in coordinator_notifications["notifications"]
        ]
        self.assertIn("Math Club is now full.", messages)


if __name__ == "__main__":
    unittest.main()
