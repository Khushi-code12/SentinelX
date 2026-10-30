# SentinelX

Real-time violence and weapon detection for a camera feed.

A custom YOLO11 model watches a webcam, phone, CCTV stream or video file. The
web console shows the annotated live feed with a threat level, logs every
detection of violence or a weapon with a snapshot, and sends it to Telegram.

## Features

- **Live detection** of `Violence`, `guns` and `knife` (plus `NonViolence`,
  which is shown but never alerts) with a YOLO11n model
- **Security-ops console**: threat banner (all clear / elevated / critical /
  no signal), per-class live confidence, camera status and FPS
- **Alert log** with snapshot thumbnails, full-size viewer, CSV export
- **Telegram notifications** with the snapshot attached
- **Adjustable** confidence threshold and alert cooldown from the dashboard
- **One shared detector**: any number of viewers, camera auto-reconnects
- Optional **password protection** for remote access
- Any camera source: USB webcam, Android phone (IP Webcam), RTSP/CCTV, video
  file

## Quick start

```bash
git clone https://github.com/Jatin-code16/SentinelX.git
cd SentinelX
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # Linux/macOS: cp .env.example .env
python app.py
```

Open http://127.0.0.1:5002.

To get Telegram alerts, add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to
`.env`. Without them the app still runs and skips the alerts. Check the
setup with `python test_tele.py`.

**To run it 24/7, view it from your phone, share a link or host a public
demo — all free — see [DEPLOYMENT.md](DEPLOYMENT.md).**

## Configuration

Put these in `.env` or in the environment:

| Variable | Default | Meaning |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | — | Telegram alerts (optional) |
| `SENTINELX_CAMERA` | `0` | Camera index, video file, or `http(s)://` / `rtsp://` stream URL |
| `SENTINELX_MODEL` | `sx_model/my_model.pt` | YOLO weights |
| `SENTINELX_PASSWORD` | — | Turns on a login for the whole dashboard |
| `SENTINELX_USER` | `admin` | Login username |
| `DATABASE_URL` | `sqlite:///sentinelx.db` | SQLAlchemy URL (SQLite lives in `instance/`) |
| `HOST` / `PORT` | `127.0.0.1` / `5002` | Bind address for `python app.py` |
| `FLASK_DEBUG` | off | `1` enables the Werkzeug debugger. Never on a reachable host. |

You set the detection confidence, alert cooldown and Telegram on/off in the
dashboard. They are saved to `instance/settings.json`.

## Model

`sx_model/my_model.pt` is a YOLO11n model trained for 50 epochs on a Roboflow
violence & weapon dataset. On that dataset's validation set it scores
precision 0.84, recall 0.82 and mAP50 0.86.

Classes: `NonViolence`, `Violence`, `guns`, `knife`.

The training data is CCTV-style footage, so the model is less sensitive on
close-up webcam video. If it misses things, lower the confidence threshold.
To use other weights, set `SENTINELX_MODEL`.

## Annotate a video offline

```bash
python detect.py -i path/to/video.mp4 -o output/annotated.mp4 -c 0.5
```

## Project structure

```
app.py              Flask app and HTTP routes
camera.py           Detector: camera capture, inference, alerts (one background thread)
models.py           Alert table (SQLAlchemy)
telegram_alerts.py  Telegram text and photo alerts
detect.py           Offline video annotation CLI
test_tele.py        Telegram setup check
templates/          Dashboard HTML
static/             Dashboard CSS, JS and images
sx_model/           YOLO11 weights
Dockerfile          Container for Hugging Face Spaces / any Docker host
DEPLOYMENT.md       Free deployment guide
```

### HTTP routes

| Route | Purpose |
|---|---|
| `/` | Dashboard |
| `/video_feed` | Annotated MJPEG stream |
| `/status` | Camera state, FPS, live per-class confidence |
| `/get_alerts` | Latest 50 alerts and totals |
| `/config` | GET / POST detection settings |
| `/capture` | POST: save the current frame |
| `/clear_alerts` | POST: delete all alerts and their snapshots |
| `/export_alerts` | Download all alerts as CSV |

## Tech stack

Python · Flask · Ultralytics YOLO11 · OpenCV · SQLAlchemy (SQLite) ·
python-telegram-bot · waitress · vanilla JS/CSS
