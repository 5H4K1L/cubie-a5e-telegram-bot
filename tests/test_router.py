import tempfile
import unittest
from pathlib import Path
from modules.router import memory, interface_counters

class RouterTests(unittest.TestCase):
    def test_memory_returns_nonnegative_values(self):
        result = memory()
        self.assertGreaterEqual(result["total"], 0)
        self.assertGreaterEqual(result["used"], 0)
        self.assertGreaterEqual(result["percent"], 0)

    def test_interface_counter_rejects_bad_name(self):
        self.assertIsNone(interface_counters("../../etc/passwd"))

if __name__ == "__main__":
    unittest.main()
