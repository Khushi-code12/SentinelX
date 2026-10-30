import os
import json
import time
import threading
from datetime import datetime

import cv2
from ultralytics import YOLO

from telegram_alerts import send_alert
from models import db, Alert

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# YOLO11n model: mAP50 0.86 vs 0.63 for the older YOLOv8s model in my_model/
MODEL_PATH = os.environ.get('SENTINELX_MODEL', os.path.join(BASE_DIR, 'sx_model', 'my_model.pt'))
# Camera index ("0") or a video file / stream URL
CAMERA_SOURCE = os.environ.get('SENTINELX_CAMERA', '0')

ALERT_DIR = os.path.join('static', 'alerts')
CAPTURE_DIR = os.path.join('static', 'captures')
SETTINGS_PATH = os.path.join(BASE_DIR, 'instance', 'settings.json')

# Classes that are detected and shown, but never raise an alert
SAFE_CLASSES = {'NonViolence'}

DEFAULT_SETTINGS = {
    'confidence': 0.5,       # 0.1 - 0.9
    'cooldown': 10,          # seconds between alerts, 5 - 60
    'telegram_enabled': True,
}


def _load_settings():
    settings = dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH) as f:
            settings.update({k: v for k, v in json.load(f).items() if k in DEFAULT_SETTINGS})
    except (OSError, ValueError):
        pass
    return settings


def _timestamped_path(folder, prefix):
    """Return (relative_path, absolute_path) for a new timestamped snapshot."""
    ts_safe = datetime.now().isoformat().replace(':', '-')
    rel = os.path.join(folder, f"{prefix}_{ts_safe}.jpg")
    abs_path = os.path.join(BASE_DIR, rel)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    return rel.replace('\\', '/'), abs_path


class Detector:
    """Owns the camera and the model. A single background thread captures and
    runs inference; every /video_feed client reads the latest annotated frame."""

    def __init__(self, app):
        self.app = app
        self.settings = _load_settings()
        self._settings_lock = threading.Lock()
        self._frame_cond = threading.Condition()
        self._jpeg = None
        self._frame = None
        self._frame_id = 0
        self._detections = []
        self._scores = {}           # class name -> highest confidence in the latest frame
        self._last_frame_time = 0
        self._fps = 0.0
        self._class_names = []
        self._last_alert_time = 0
        self._thread = None
        self._start_lock = threading.Lock()

    # ---- lifecycle ---------------------------------------------------------

    def start(self):
        """Start the capture thread once. Safe to call on every request."""
        with self._start_lock:
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, daemon=True, name='detector')
                self._thread.start()

    def _open_capture(self):
        source = int(CAMERA_SOURCE) if CAMERA_SOURCE.isdigit() else CAMERA_SOURCE
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            cap.release()
            return None
        return cap

    def _run(self):
        model = YOLO(MODEL_PATH)
        self._class_names = [model.names[i] for i in sorted(model.names)]
        cap = None
        while True:
            if cap is None:
                cap = self._open_capture()
                if cap is None:
                    print(f"[WARN] Cannot open camera source {CAMERA_SOURCE!r}, retrying in 2s")
                    time.sleep(2)
                    continue

            ret, frame = cap.read()
            if not ret:
                # Camera unplugged or video file ended: reopen instead of dying
                cap.release()
                cap = None
                time.sleep(1)
                continue

            try:
                self._process(model, frame)
            except Exception as e:
                print("[ERROR] Frame processing failed:", e)

    # ---- per-frame work ----------------------------------------------------

    def _process(self, model, frame):
        settings = self.get_settings()
        result = model(frame, imgsz=640, conf=settings['confidence'], verbose=False)[0]
        annotated = result.plot()

        scores = {}
        for c, s in zip(result.boxes.cls.tolist(), result.boxes.conf.tolist()):
            name = result.names[int(c)]
            scores[name] = max(scores.get(name, 0.0), float(s))
        # Unique class names in detection order
        detected = list(scores)
        alert_classes = [c for c in detected if c not in SAFE_CLASSES]

        ok, buffer = cv2.imencode('.jpg', annotated)
        now = time.time()
        with self._frame_cond:
            if self._last_frame_time:
                # Exponential moving average of the processing rate
                self._fps = 0.9 * self._fps + 0.1 / max(now - self._last_frame_time, 1e-3)
            self._last_frame_time = now
            self._detections = detected
            self._scores = scores
            self._frame = annotated
            if ok:
                self._jpeg = buffer.tobytes()
                self._frame_id += 1
            self._frame_cond.notify_all()

        if alert_classes and time.time() - self._last_alert_time > settings['cooldown']:
            self._last_alert_time = time.time()
            self._raise_alert(alert_classes, annotated, settings['telegram_enabled'])

    def _raise_alert(self, classes, frame, telegram_enabled):
        rel_path, abs_path = _timestamped_path(ALERT_DIR, 'alert')
        cv2.imwrite(abs_path, frame)

        now = datetime.now()
        msg = f"Suspicious activity: {', '.join(classes)} at {now.isoformat(timespec='seconds')}"
        with self.app.app_context():
            db.session.add(Alert(timestamp=now, message=msg, snapshot_path=rel_path))
            db.session.commit()

        print("[ALERT]", classes, rel_path)
        if telegram_enabled:
            threading.Thread(target=send_alert, args=(msg, abs_path), daemon=True).start()

    # ---- public API --------------------------------------------------------

    def frames(self):
        """MJPEG generator for /video_feed."""
        self.start()
        last_id = 0  # frame ids start at 1, so this waits for the first real frame
        while True:
            with self._frame_cond:
                self._frame_cond.wait_for(lambda: self._frame_id != last_id, timeout=5)
                if self._frame_id == last_id:
                    continue  # no new frame yet (camera reconnecting)
                last_id, jpeg = self._frame_id, self._jpeg
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')

    def get_current_detections(self):
        with self._frame_cond:
            return list(self._detections)

    def get_status(self):
        with self._frame_cond:
            return {
                # No frame for 3s means the camera is down or reconnecting
                'camera_online': time.time() - self._last_frame_time < 3,
                'fps': round(self._fps, 1),
                'scores': {k: round(v, 2) for k, v in self._scores.items()},
                'classes': list(self._class_names),
                'safe_classes': sorted(SAFE_CLASSES),
                'model': os.path.relpath(MODEL_PATH, BASE_DIR).replace('\\', '/'),
            }

    def capture(self):
        """Save the latest annotated frame; returns its relative path or None."""
        with self._frame_cond:
            frame = None if self._frame is None else self._frame.copy()
        if frame is None:
            return None
        rel_path, abs_path = _timestamped_path(CAPTURE_DIR, 'capture')
        cv2.imwrite(abs_path, frame)
        return rel_path

    def get_settings(self):
        with self._settings_lock:
            return dict(self.settings)

    def update_settings(self, new):
        with self._settings_lock:
            self.settings.update(new)
            os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
            with open(SETTINGS_PATH, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return dict(self.settings)
