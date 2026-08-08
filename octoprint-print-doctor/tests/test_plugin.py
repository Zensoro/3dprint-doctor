"""Unit tests for the OctoPrint plugin (no OctoPrint runtime required).

We import the plugin module with a fake `octoprint` package injected so
the class definitions load, then exercise the event/monitor logic with
mocks.
"""
import sys
import types
import unittest

# --- Fake octoprint package so imports succeed without OctoPrint ---
octoprint = types.ModuleType("octoprint")
plugin_mod = types.ModuleType("octoprint.plugin")
octoprint.plugin = plugin_mod


class BasePlugin:
    def __init__(self):
        self._logger = types.SimpleNamespace(
            info=lambda *a, **k: None,
            warning=lambda *a, **k: None,
            error=lambda *a, **k: None,
        )
        self._settings = types.SimpleNamespace(get=lambda k, d=None: None)
        self._plugin_manager = types.SimpleNamespace(
            send_plugin_message=lambda *a, **k: None
        )
        self._printer = None
        self._identifier = "print_doctor"


class SettingsPlugin(BasePlugin):
    pass


class AssetPlugin(BasePlugin):
    pass


class StartupPlugin(BasePlugin):
    pass


class EventHandlerPlugin(BasePlugin):
    pass


class TemplatePlugin(BasePlugin):
    pass


for name in ["SettingsPlugin", "AssetPlugin", "StartupPlugin",
             "EventHandlerPlugin", "TemplatePlugin"]:
    setattr(plugin_mod, name, globals()[name])

octoprint.util = types.ModuleType("octoprint.util")
sys.modules["octoprint"] = octoprint
sys.modules["octoprint.plugin"] = plugin_mod
sys.modules["octoprint.util"] = octoprint.util

# --- Now import the real plugin ---
sys.path.insert(0, "octoprint-print-doctor")
from octoprint_print_doctor import PrintDoctorPlugin  # noqa: E402


class FakePrinter:
    def __init__(self):
        self.paused = False

    def pause_print(self):
        self.paused = True


class FakeSettings:
    def __init__(self, **values):
        self._v = {
            "snapshot_url": "",
            "interval": 5.0,
            "cooldown": 60.0,
            "evidence_dir": "evidence",
            "pause_on_defect": False,
            "confidence_threshold": 0.5,
        }
        self._v.update(values)

    def get(self, key, default=None):
        # OctoPrint settings.get accepts a path list like ["snapshot_url"]
        if isinstance(key, (list, tuple)):
            key = key[0]
        return self._v.get(key, default)


class TestPlugin(unittest.TestCase):
    def make_plugin(self, **settings):
        p = PrintDoctorPlugin()
        p._logger = types.SimpleNamespace(
            info=lambda *a, **k: None,
            warning=lambda *a, **k: None,
            error=lambda *a, **k: None,
        )
        p._settings = FakeSettings(**settings)
        p._printer = FakePrinter()
        p._plugin_manager = types.SimpleNamespace(
            send_plugin_message=lambda *a, **k: None
        )
        p._identifier = "print_doctor"
        return p

    def test_event_print_started_starts_monitor(self):
        import time
        p = self.make_plugin(snapshot_url="http://cam/snapshot")
        p._start_monitoring()
        self.assertIsNotNone(p._thread)
        # thread may take a moment to become alive on a slow CI runner
        for _ in range(50):
            if p._thread.is_alive():
                break
            time.sleep(0.05)
        self.assertTrue(p._thread.is_alive())
        p._stop_monitoring()
        self.assertIsNone(p._thread)

    def test_event_print_done_stops_monitor(self):
        p = self.make_plugin(snapshot_url="http://cam/snapshot")
        p._start_monitoring()
        p._stop_monitoring()
        self.assertIsNone(p._thread)

    def test_snapshot_provider_no_url_returns_none(self):
        p = self.make_plugin(snapshot_url="")
        self.assertIsNone(p._snapshot_provider())

    def test_on_defect_pauses_when_enabled(self):
        from print_doctor.models import Defect, DefectType

        p = self.make_plugin(pause_on_defect=True)
        p._on_defect([
            Defect(type=DefectType.STRINGING, confidence=0.9, evidence="e")
        ])
        self.assertTrue(p._printer.paused)

    def test_on_defect_no_pause_when_disabled(self):
        from print_doctor.models import Defect, DefectType

        p = self.make_plugin(pause_on_defect=False)
        p._on_defect([
            Defect(type=DefectType.STRINGING, confidence=0.9, evidence="e")
        ])
        self.assertFalse(p._printer.paused)


if __name__ == "__main__":
    unittest.main()
