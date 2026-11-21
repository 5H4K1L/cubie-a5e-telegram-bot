"""Tests for advanced router controls."""
import unittest
from unittest.mock import patch
from modules.advanced import RESTARTABLE_SERVICES, restart_service

class AdvancedControlsTests(unittest.TestCase):
    def test_only_fixed_services_are_allow_listed(self):
        self.assertEqual(set(RESTARTABLE_SERVICES), {"dnsmasq", "firewall", "network", "wireguard", "openvpn"})

    def test_unknown_service_is_rejected_without_execution(self):
        with patch("modules.advanced.subprocess.run") as run:
            ok, message = restart_service("sh")
        self.assertFalse(ok)
        self.assertIn("allow-list", message)
        run.assert_not_called()

    def test_missing_init_script_is_reported(self):
        with patch("modules.advanced.Path.is_file", return_value=False), patch("modules.advanced.subprocess.run") as run:
            ok, message = restart_service("wireguard")
        self.assertFalse(ok)
        self.assertIn("not installed", message)
        run.assert_not_called()

if __name__ == "__main__":
    unittest.main()
