import importlib.util
import os
from pathlib import Path
import sys
import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location("schedule", Path(__file__).parents[1] / "lambda/schedule.py")
schedule = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"boto3": Mock()}):
    spec.loader.exec_module(schedule)


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        env = {"INSTANCE_ID": "i-test", "DB_ID": "test-db", "ZONE_ID": "ZTEST",
               "ORIGIN_DOMAIN": "origin.example.com", "HOLIDAY_DATES": '["2026-09-21"]',
               "HOLIDAY_CALENDAR_YEAR": "2026"}
        self.env = patch.dict(os.environ, env)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.ec2, self.rds, self.dns = Mock(), Mock(), Mock()
        self.now = datetime(2026, 9, 11, 10, tzinfo=ZoneInfo("Asia/Tokyo"))

    def states(self, ec2, db):
        self.ec2.describe_instances.return_value = {"Reservations": [{"Instances": [
            {"State": {"Name": ec2}, "PublicIpAddress": "203.0.113.10"}]}]}
        self.rds.describe_db_instances.return_value = {"DBInstances": [{"DBInstanceStatus": db}]}

    def run_step(self):
        return schedule.reconcile(self.now, self.ec2, self.rds, self.dns)

    def test_hours_weekend_and_holiday(self):
        for day, hour, expected in [(11, 9, False), (11, 10, True), (11, 21, True),
                                    (11, 22, False), (12, 12, False), (21, 12, False)]:
            with self.subTest(day=day, hour=hour):
                self.assertEqual(schedule.should_run(self.now.replace(day=day, hour=hour)), expected)

    def test_start_rds_first(self):
        self.states("stopped", "stopped")
        self.run_step()
        self.rds.start_db_instance.assert_called_once()
        self.ec2.start_instances.assert_not_called()

    def test_wait_for_database(self):
        self.states("stopped", "starting")
        self.run_step()
        self.ec2.start_instances.assert_not_called()
        self.rds.start_db_instance.assert_not_called()

    def test_start_ec2_only_after_database_available(self):
        self.states("stopped", "available")
        self.run_step()
        self.ec2.start_instances.assert_called_once()
        self.dns.change_resource_record_sets.assert_not_called()

    def test_stop_order(self):
        self.now = self.now.replace(hour=22)
        for state in ["running", "stopping", "stopped"]:
            self.states(state, "available")
            self.run_step()
            if state != "stopped":
                self.rds.stop_db_instance.assert_not_called()
        self.ec2.stop_instances.assert_called_once()
        self.rds.stop_db_instance.assert_called_once()

    def test_dns_update_and_idempotence(self):
        self.states("running", "available")
        self.dns.list_resource_record_sets.return_value = {"ResourceRecordSets": []}
        self.run_step()
        record = self.dns.change_resource_record_sets.call_args.kwargs["ChangeBatch"]["Changes"][0]["ResourceRecordSet"]
        self.assertEqual(record["ResourceRecords"], [{"Value": "203.0.113.10"}])
        self.dns.list_resource_record_sets.return_value = {"ResourceRecordSets": [record]}
        self.run_step()
        self.dns.change_resource_record_sets.assert_called_once()

    def test_expired_calendar_stops_and_reports(self):
        self.now = self.now.replace(year=2027)
        self.states("running", "available")
        with self.assertRaisesRegex(RuntimeError, "holiday_calendar_year"):
            self.run_step()
        self.ec2.stop_instances.assert_called_once()
        self.ec2.start_instances.assert_not_called()

    def test_api_error_propagates(self):
        self.states("stopped", "stopped")
        self.rds.start_db_instance.side_effect = RuntimeError("unavailable")
        with self.assertRaises(RuntimeError):
            self.run_step()
        self.ec2.start_instances.assert_not_called()


if __name__ == "__main__":
    unittest.main()
