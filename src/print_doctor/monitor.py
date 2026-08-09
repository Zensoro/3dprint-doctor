"""Real-time print monitoring: watch a camera or directory and alert
when a defect is detected.

Uses the trained ML classifier on sampled frames, with cooldown to
avoid alert spam. On a defect it saves an evidence screenshot, prints
a message and optionally POSTs a webhook.
"""
import os
import time
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from print_doctor.models import Defect
from print_doctor.vision_ml import DefectClassifier, classify_photo


class PrintMonitor:
    """Continuously samples frames and alerts on detected defects."""

    def __init__(
        self,
        classifier: Optional[DefectClassifier] = None,
        interval_seconds: float = 5.0,
        evidence_dir: str = "evidence",
        cooldown_seconds: float = 60.0,
        webhook: Optional[str] = None,
        gcode_path: Optional[str] = None,
        progress_provider=None,
    ):
        if classifier is None:
            classifier = DefectClassifier()
        self.classifier = classifier
        self.interval = interval_seconds
        self.evidence_dir = Path(evidence_dir)
        self.cooldown = cooldown_seconds
        self.webhook = webhook
        self._last_alert: float = 0.0

        # G-code progress context (optional)
        self.gcode = None
        if gcode_path:
            from print_doctor.gcode import parse_gcode_file
            self.gcode = parse_gcode_file(gcode_path)
        self.progress_provider = progress_provider

    def _progress_context(self) -> str:
        """Return a short progress string (layer / percent) for display."""
        if self.gcode is None:
            return ""
        if self.progress_provider is None:
            return f"layers: {self.gcode.layer_count}, max Z: {self.gcode.max_z:.1f}mm"
        try:
            progress = float(self.progress_provider())
        except Exception:
            return ""
        if progress is None:
            return ""
        # throttle: only report when changed by >= 1%
        if abs(progress - getattr(self, "_last_progress", -1.0)) < 0.01:
            return ""
        self._last_progress = progress
        layer = self.gcode.layer_at(progress * self.gcode.total_extruded) \
            if self.gcode.total_extruded > 0 else None
        layer_txt = f"layer {layer.number}" if layer is not None else "?"
        return f"[{progress * 100:.0f}% · {layer_txt}]"

    # ------------------------------------------------------------------
    def check_frame(
        self, frame: np.ndarray, timestamp: Optional[float] = None
    ) -> List[Defect]:
        """Classify a single frame, alerting (and saving evidence) on defects.

        Args:
            frame: BGR image
            timestamp: Optional time (defaults to time.time())

        Returns:
            Detected defects (empty if healthy)
        """
        timestamp = timestamp or time.time()
        defects = classify_photo(frame, classifier=self.classifier)
        if defects:
            self._alert(defects, frame, timestamp)
        return defects

    # ------------------------------------------------------------------
    def run_camera(self, camera_index: int = 0, stop_after: Optional[float] = None):
        """Monitor a camera feed, alerting on defects until interrupted."""
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open camera index {camera_index}")

        print(f"Monitoring camera {camera_index} every {self.interval}s "
              f"(Ctrl+C to stop)")
        start = time.time()
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    print("Camera frame read failed")
                    break
                ctx = self._progress_context()
                if ctx:
                    print(f"  {ctx}")
                self.check_frame(frame)
                if stop_after and (time.time() - start) > stop_after:
                    break
                time.sleep(self.interval)
        finally:
            cap.release()

    def run_url(
        self, url: str, stop_after: Optional[float] = None,
        auth: Optional[tuple] = None,
    ):
        """Poll a snapshot URL (e.g. OctoPrint/Moonraker webcam) for defects.

        Args:
            url: HTTP(S) URL returning a JPEG image (webcam snapshot)
            auth: Optional (user, password) basic auth tuple
            stop_after: Stop after N seconds (testing)
        """
        import urllib.request

        print(f"Monitoring {url} every {self.interval}s (Ctrl+C to stop)")
        start = time.time()
        opener = urllib.request.build_opener()
        if auth:
            import base64
            token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
            opener.addheaders = [("Authorization", f"Basic {token}")]

        try:
            while True:
                try:
                    data = opener.open(url, timeout=15).read()
                    frame = cv2.imdecode(
                        np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR
                    )
                    if frame is not None:
                        ctx = self._progress_context()
                        if ctx:
                            print(f"  {ctx}")
                        self.check_frame(frame)
                except Exception as e:
                    print(f"Snapshot fetch failed: {e}")
                if stop_after and (time.time() - start) > stop_after:
                    break
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\nStopped.")

    def run_directory(
        self, watch_dir: str, stop_after: Optional[float] = None
    ):
        """Monitor a directory for new images, alerting on defects.

        Useful for testing and for setups where a camera saves periodic
        snapshots (e.g. OctoPrint timelapse snapshots).
        """
        watch = Path(watch_dir)
        watch.mkdir(parents=True, exist_ok=True)
        seen = {p.name for p in watch.glob("*.jpg")}
        print(f"Watching {watch} every {self.interval}s (Ctrl+C to stop)")
        start = time.time()
        try:
            while True:
                for p in sorted(watch.glob("*.jpg")):
                    if p.name in seen:
                        continue
                    seen.add(p.name)
                    frame = cv2.imread(str(p))
                    if frame is not None:
                        ctx = self._progress_context()
                        print(f"[new frame] {p.name}{(' · ' + ctx) if ctx else ''}")
                        self.check_frame(frame)
                else:
                    # existing frame: still refresh progress context
                    ctx = self._progress_context()
                    if ctx:
                        print(f"  {ctx}")
                if stop_after and (time.time() - start) > stop_after:
                    break
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\nStopped.")

    # ------------------------------------------------------------------
    def _alert(self, defects: List[Defect], frame: np.ndarray, timestamp: float):
        """Fire an alert if past cooldown; save evidence screenshot."""
        now = time.time()
        if now - self._last_alert < self.cooldown:
            return
        self._last_alert = now

        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(timestamp))
        names = ", ".join(f"{d.type.value} ({d.confidence:.2f})" for d in defects)
        print(f"\n[ALERT {ts}] Defect detected: {names}")

        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        shot = self.evidence_dir / f"defect_{ts}.jpg"
        cv2.imwrite(str(shot), frame)
        print(f"Evidence saved: {shot}")

        if self.webhook:
            self._post_webhook(defects, ts, str(shot))

    def _post_webhook(self, defects: List[Defect], ts: str, shot: str):
        """POST a JSON alert to a webhook URL (fire-and-forget)."""
        import json
        import threading
        import urllib.request

        payload = json.dumps({
            "event": "print_defect",
            "time": ts,
            "defects": [
                {"type": d.type.value, "confidence": round(d.confidence, 3),
                 "evidence": d.evidence}
                for d in defects
            ],
            "evidence_image": shot,
        }).encode()

        def _send():
            try:
                req = urllib.request.Request(
                    self.webhook, data=payload,
                    headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=10)
            except Exception as e:
                print(f"Webhook failed: {e}")

        threading.Thread(target=_send, daemon=True).start()


def moonraker_progress_provider(url: str, api_key: str = "", timeout: float = 8.0):
    """Build a progress provider that polls a Moonraker printer API.

    Returns a callable returning progress 0-1, or None when unknown /
    unavailable. Moonraker's ``print_stats`` exposes ``print_duration``
    (elapsed) and ``total_duration`` (estimated total), so progress =
    elapsed / total.

    URL example: http://printer:7125
    """
    import json
    import urllib.request

    def _get_progress() -> float:
        try:
            req = urllib.request.Request(
                f"{url.rstrip('/')}/printer/objects/query"
                "?print_stats=print_duration&print_stats=total_duration",
                headers={"X-Api-Key": api_key} if api_key else {},
            )
            data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
            result = data.get("result", {}).get("status", {}).get("print_stats", {})
            elapsed = result.get("print_duration", 0)
            total = result.get("total_duration", 0)
            if not total or total <= 0:
                return None
            return min(1.0, max(0.0, elapsed / total))
        except Exception:
            return None

    return _get_progress
