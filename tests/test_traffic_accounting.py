import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from modules.traffic.accounting import TrafficAccounting, format_bytes

TZ = ZoneInfo("Asia/Dhaka")

class TrafficAccountingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "traffic.sqlite3")
        self.accounting = TrafficAccounting(self.db, max_gap_seconds=600)

    def tearDown(self):
        self.tmp.cleanup()

    def ts(self, value):
        return datetime.fromisoformat(value).replace(tzinfo=TZ).timestamp()

    def test_baseline(self):
        result = self.accounting.record_sample("eth0", 1000, 2000, self.ts("2026-11-01T00:00:00"))
        self.assertTrue(result["baseline"])

    def test_delta_report(self):
        start = self.ts("2026-11-01T00:00:00")
        self.accounting.record_sample("eth0", 1000, 2000, start)
        self.accounting.record_sample("eth0", 5000, 7000, start + 60)
        report = self.accounting.report(datetime.fromtimestamp(start, TZ),
            datetime.fromtimestamp(start + 60, TZ), "test")
        self.assertEqual(report.download_bytes, 4000)
        self.assertEqual(report.upload_bytes, 5000)
        self.assertTrue(report.complete)

    def test_counter_reset(self):
        start = self.ts("2026-11-01T00:00:00")
        self.accounting.record_sample("eth0", 9000, 8000, start)
        result = self.accounting.record_sample("eth0", 100, 200, start + 60)
        self.assertEqual(result["reason"], "counter_reset_or_wrap")

    def test_interface_change(self):
        start = self.ts("2026-11-01T00:00:00")
        self.accounting.record_sample("eth0", 100, 100, start)
        result = self.accounting.record_sample("pppoe-wan", 200, 200, start + 60)
        self.assertEqual(result["reason"], "interface_changed")

    def test_sampling_gap(self):
        start = self.ts("2026-11-01T00:00:00")
        self.accounting.record_sample("eth0", 100, 100, start)
        result = self.accounting.record_sample("eth0", 200, 200, start + 601)
        self.assertEqual(result["reason"], "sampling_gap")

    def test_missing_history_incomplete(self):
        start = self.ts("2026-11-01T00:00:00")
        report = self.accounting.report(datetime.fromtimestamp(start, TZ),
            datetime.fromtimestamp(start + 60, TZ), "test")
        self.assertFalse(report.complete)
        self.assertIn("missing_history_or_sampling_gap", report.warnings)

    def test_format_bytes(self):
        self.assertEqual(format_bytes(1024 * 1024), "1.00 MiB")

if __name__ == "__main__":
    unittest.main()
