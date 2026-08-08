"""OctoPrint plugin: monitor the print with Print Doctor and alert/pause
when a defect is detected.

The plugin reuses the Print Doctor ML classifier. On a detected defect it:
  - pushes a notification to OctoPrint UI
  - saves an evidence screenshot
  - optionally pauses the print (configurable)

Installation: `pip install .` inside octoprint-print-doctor/, then enable
under Settings -> Plugin Manager.
"""
import threading
import time

import octoprint.plugin
import octoprint.util

from print_doctor.monitor import PrintMonitor
from print_doctor.vision_ml import DefectClassifier


class PrintDoctorPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.TemplatePlugin,
):

    def __init__(self):
        self._monitor = None
        self._thread = None
        self._stop = threading.Event()

    # -- Settings ---------------------------------------------------------
    def get_settings_defaults(self):
        return {
            "snapshot_url": "",          # webcam snapshot URL (snapshot option)
            "interval": 5.0,
            "cooldown": 60.0,
            "evidence_dir": "print_doctor_evidence",
            "pause_on_defect": False,
            "confidence_threshold": 0.5,
        }

    # -- Startup ----------------------------------------------------------
    def on_after_startup(self):
        self._logger.info("Print Doctor plugin started")

    # -- Events -----------------------------------------------------------
    def on_event(self, event, payload):
        if event == "PrintStarted":
            self._start_monitoring()
        elif event in ("PrintDone", "PrintFailed", "PrintCancelled"):
            self._stop_monitoring()

    # -- Monitoring -------------------------------------------------------
    def _snapshot_provider(self):
        """Fetch a frame from the configured webcam snapshot URL."""
        import cv2
        import numpy as np
        import urllib.request

        url = self._settings.get(["snapshot_url"])
        if not url:
            return None
        try:
            data = urllib.request.urlopen(url, timeout=10).read()
            return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        except Exception as e:
            self._logger.warning("snapshot fetch failed: %s", e)
            return None

    def _start_monitoring(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop, name="print-doctor-monitor", daemon=True
        )
        self._thread.start()
        self._logger.info("Print Doctor monitoring started")

    def _stop_monitoring(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        self._logger.info("Print Doctor monitoring stopped")

    def _monitor_loop(self):
        try:
            classifier = DefectClassifier()
        except FileNotFoundError as e:
            self._logger.error("Print Doctor model missing: %s", e)
            return

        monitor = PrintMonitor(
            classifier=classifier,
            interval_seconds=float(self._settings.get(["interval"])),
            evidence_dir=self._settings.get(["evidence_dir"]),
            cooldown_seconds=float(self._settings.get(["cooldown"])),
        )

        while not self._stop.is_set():
            frame = self._snapshot_provider()
            if frame is not None:
                defects = monitor.check_frame(frame)
                if defects:
                    self._on_defect(defects)
            self._stop.wait(monitor.interval)

    def _on_defect(self, defects):
        names = ", ".join(f"{d.type.value}" for d in defects)
        self._logger.warning("Print defect detected: %s", names)
        self._plugin_manager.send_plugin_message(
            self._identifier,
            {"type": "defect", "message": f"Defect: {names}", "time": time.time()},
        )
        if self._settings.get(["pause_on_defect"]):
            self._printer.pause_print()
            self._logger.info("Print paused due to detected defect")

    # -- Assets / templates ----------------------------------------------
    def get_assets(self):
        return {"js": ["js/printdoctor.js"]}

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False),
            dict(type="tab", name="Print Doctor", custom_bindings=False),
        ]


__plugin_name__ = "Print Doctor"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = PrintDoctorPlugin()
