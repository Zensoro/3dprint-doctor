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
    ):
        if classifier is None:
            classifier = DefectClassifier()
        self.classifier = classifier
        self.interval = interval_seconds
        self.evidence_dir = Path(evidence_dir)
        self.cooldown = cooldown_seconds
        self.webhook = webhook
        self._last_alert: float = 0.0

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
                        print(f"[new frame] {p.name}")
                        self.check_frame(frame)
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
