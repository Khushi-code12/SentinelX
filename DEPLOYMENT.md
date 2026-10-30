# Deploying SentinelX (free)

Everything in this guide costs nothing: no paid hosting, no paid domain, no
credit card.

## First, the one constraint that decides everything

SentinelX has to **see a camera**. The machine running `app.py` reads the
video stream, runs the YOLO model on every frame and serves the dashboard.
A cloud server cannot see the webcam on your laptop, so:

- For **real monitoring**, run SentinelX on a computer that has the camera
  (or can reach an IP/CCTV camera on your network), then make the dashboard
  reachable from your phone.
- A **cloud host** is only useful as a public demo that runs on a video file
  or a publicly reachable camera stream.

## Pick a setup

| Setup | Cost | Camera | Who can open the dashboard | Use it for |
|---|---|---|---|---|
| [A. Your own PC](#a-run-on-your-own-pc) | Free | USB webcam, phone, CCTV, video | That PC (and your Wi-Fi if you allow it) | Everyday monitoring — **start here** |
| [B. + Tailscale](#b-private-access-from-anywhere-tailscale) | Free (Personal plan) | Same as A | Only your own devices, from anywhere | Checking the feed from your phone when away |
| [C. + Cloudflare Tunnel](#c-public-https-link-cloudflare-tunnel) | Free, no account | Same as A | Anyone with the link **and password** | Showing it to someone quickly |
| [D. Hugging Face Spaces](#d-public-cloud-demo-hugging-face-spaces) | Free (CPU basic) | Demo video or public stream only | Anyone with the link **and password** | Portfolio / project demo |

**Why not Vercel, Netlify, Render, Railway…?** Vercel and Netlify host static
sites and short serverless functions; they can't keep a camera open or a
video stream running. Render's free instance has 512 MB of RAM, which is not
enough for PyTorch, and it sleeps after 15 minutes idle. Railway no longer
has a free tier. Hugging Face Spaces gives 2 vCPU / 16 GB RAM for free, which
is why it's used for the cloud demo.

---

## Before you start (all setups)

### 1. Install

Python 3.10–3.12 is recommended.

```bash
git clone https://github.com/Jatin-code16/SentinelX.git
cd SentinelX
python -m venv venv
venv\Scripts\activate            # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # Linux/macOS: cp .env.example .env
```

`pip` installs the CPU build of PyTorch (~1 GB download). If you have an
NVIDIA GPU, install the CUDA build first from
https://pytorch.org/get-started/locally/ to get much higher FPS.

### 2. Telegram alerts (free, optional)

1. In Telegram, message **@BotFather** → `/newbot` → follow the prompts.
   Copy the token it gives you.
2. Send any message to your new bot.
3. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser
   and copy the number at `"chat":{"id": ...}`.
4. Put both in `.env`:

   ```ini
   TELEGRAM_BOT_TOKEN=123456:ABC...
   TELEGRAM_CHAT_ID=123456789
   ```

5. Check it: `python test_tele.py` — you should get a test message.

Never commit `.env`. If a token ever leaks, send `/revoke` to @BotFather and
replace it.

### 3. Set a dashboard password

The dashboard shows a live camera and can delete alerts. Any time it is
reachable from another device, protect it:

```ini
SENTINELX_PASSWORD=pick-a-long-password
SENTINELX_USER=admin                # optional, default "admin"
```

Your browser will ask for this login once per session.

### 4. Choose the camera

Set `SENTINELX_CAMERA` in `.env`:

| Source | Value |
|---|---|
| Built-in / first USB webcam | `0` (default) |
| Second webcam | `1` |
| Android phone as camera ([IP Webcam](https://play.google.com/store/apps/details?id=com.pas.webcam) app, free) | `http://PHONE_IP:8080/video` |
| CCTV / IP camera (RTSP) | `rtsp://user:pass@CAMERA_IP:554/stream1` (path depends on the camera brand) |
| Video file (testing / demo) | `images/videos/01.mp4` — loops forever |

Only one program can use a webcam at a time — close Zoom/Camera apps first.

---

## A. Run on your own PC

### Start it

`python app.py` is Flask's development server. For anything you leave
running, use **waitress** (installed with the requirements):

```bash
# Only this computer can open it
waitress-serve --threads=16 --listen=127.0.0.1:5002 app:app

# Also reachable from phones/laptops on the same Wi-Fi (set a password first!)
waitress-serve --threads=16 --listen=0.0.0.0:5002 app:app
```

Open http://127.0.0.1:5002 (or `http://<this-PC's-IP>:5002` from another
device; find the IP with `ipconfig` on Windows or `ip a` on Linux). On first
LAN access Windows Firewall asks whether to allow Python — choose
**Private networks**.

> Always run **one** server process. The detector owns the camera; two
> processes (or `gunicorn -w 4`) would fight over it. Use `--threads` for more
> viewers instead. Each open dashboard tab uses one thread.

### Start automatically on boot

**Windows (Task Scheduler)**

1. Create `start_sentinelx.bat` in the project folder:

   ```bat
   @echo off
   cd /d "%~dp0"
   call venv\Scripts\activate
   waitress-serve --threads=16 --listen=0.0.0.0:5002 app:app >> sentinelx.log 2>&1
   ```

2. Open **Task Scheduler** → **Create Task…**
   - General: name `SentinelX`, select *Run whether user is logged on or not*.
   - Triggers: **New…** → *At startup*.
   - Actions: **New…** → *Start a program* → browse to `start_sentinelx.bat`.
   - Settings: untick *Stop the task if it runs longer than 3 days*.
3. Right-click the task → **Run** to test it.

**Linux (systemd)**

Create `/etc/systemd/system/sentinelx.service` (adjust user and paths):

```ini
[Unit]
Description=SentinelX detection dashboard
After=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/SentinelX
ExecStart=/home/pi/SentinelX/venv/bin/waitress-serve --threads=16 --listen=0.0.0.0:5002 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo usermod -aG video pi          # allow webcam access
sudo systemctl daemon-reload
sudo systemctl enable --now sentinelx
journalctl -u sentinelx -f         # logs
```

This also works on a Raspberry Pi 4/5 (64-bit OS), at a few FPS on CPU.

---

## B. Private access from anywhere (Tailscale)

[Tailscale](https://tailscale.com) builds a private network between your own
devices. The Personal plan is free. Nothing is exposed to the internet, so
this is the safest way to watch the feed from your phone.

1. Install Tailscale on the SentinelX PC and on your phone; sign in to the
   same account on both.
2. Run SentinelX listening on all interfaces (setup A,
   `--listen=0.0.0.0:5002`), with a password set.
3. In the Tailscale app, find the PC's Tailscale IP (`100.x.y.z`) or its
   machine name.
4. On your phone, open `http://100.x.y.z:5002`.

Works on mobile data, any Wi-Fi, anywhere — as long as the PC is on.

---

## C. Public HTTPS link (Cloudflare Tunnel)

A Cloudflare *quick tunnel* gives you a temporary public `https://` URL
without an account, a domain, or opening router ports.

> **Set `SENTINELX_PASSWORD` first.** Anyone who gets this link can reach
> your camera otherwise.

1. Install `cloudflared`:
   - Windows: `winget install --id Cloudflare.cloudflared`
   - Linux/macOS: see https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
2. Start SentinelX (setup A, `127.0.0.1:5002` is enough).
3. In a second terminal:

   ```bash
   cloudflared tunnel --url http://localhost:5002
   ```

4. It prints a URL like `https://random-words.trycloudflare.com`. Share it
   together with the password.

The URL changes each time you restart `cloudflared`. A permanent URL needs a
domain on Cloudflare (not free), so for long-term remote access prefer
Tailscale.

---

## D. Public cloud demo (Hugging Face Spaces)

Runs the project's `Dockerfile` on a free **CPU basic** Space (2 vCPU,
16 GB RAM). Because there is no webcam in the cloud, the demo plays a video
on a loop (or reads a public camera stream) and runs real detection on it.

### 1. Create the Space

1. Sign up at https://huggingface.co (free).
2. **New → Space**: name `sentinelx`, SDK **Docker** → template **Blank**,
   hardware **CPU basic · Free**. Public or private, your choice.

### 2. Upload the files

On the Space page open **Files → Add file → Upload files** and upload, keeping
the folder structure:

```
Dockerfile
requirements.txt
app.py  camera.py  models.py  telegram_alerts.py
templates/index.html
static/css/styles.css
static/js/app.js
static/images/X.png
static/images/favicon.ico
sx_model/my_model.pt
demo.mp4                 # any short clip to run detection on
```

**Keep the Space's own `README.md`.** Its header (`sdk: docker`) is what tells
Hugging Face how to run the Space; don't replace it with the project README.
The web uploader handles large/binary files (model, video) for you; if you
push with `git` instead, run `git lfs install` and
`git lfs track "*.pt" "*.mp4" "*.png" "*.ico"` first.

### 3. Configure

**Settings → Variables and secrets**:

| Type | Name | Value |
|---|---|---|
| Variable | `SENTINELX_CAMERA` | `demo.mp4` (or a public `http(s)://`/`rtsp://` stream) |
| Secret | `SENTINELX_PASSWORD` | a password for the dashboard |
| Secret | `TELEGRAM_BOT_TOKEN` | optional |
| Secret | `TELEGRAM_CHAT_ID` | optional |

The Space rebuilds automatically (first build ~5–10 minutes).

### 4. Open it

Use the direct URL **`https://<your-username>-sentinelx.hf.space`** — the
login prompt and the video stream work best outside the huggingface.co page
frame.

### Free-tier limits

- Inference on 2 shared vCPUs runs at a few FPS, not real time.
- The Space sleeps after ~48 hours without visitors and wakes on the next
  visit (takes a minute).
- Storage is temporary: alerts, snapshots and saved settings reset whenever
  the Space restarts. Fine for a demo.

### Same container anywhere else

The `Dockerfile` works on any Docker host:

```bash
docker build -t sentinelx .
docker run -p 7860:7860 --env-file .env \
  -e SENTINELX_CAMERA=demo.mp4 -v "$PWD/demo.mp4:/home/user/app/demo.mp4" sentinelx
```

On a Linux host with a webcam, add `--device /dev/video0` and use
`-e SENTINELX_CAMERA=0`. Docker Desktop on Windows/macOS cannot pass USB
webcams into containers — run natively (setup A) there.

---

## Security checklist

- [ ] `.env` is not committed (it's in `.gitignore`) and the Telegram token
      has never been shared.
- [ ] `SENTINELX_PASSWORD` is set whenever anything other than this PC can
      reach the dashboard.
- [ ] `FLASK_DEBUG` is **not** set to `1` on any reachable machine (the
      debugger allows running code on the server).
- [ ] Prefer Tailscale over a public link for a real camera.
- [ ] Never forward port 5002 on your router — plain HTTP sends the password
      unencrypted. Tailscale and Cloudflare encrypt the connection.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Banner says **NO SIGNAL** | Wrong `SENTINELX_CAMERA`, or another app is using the webcam. Try `1` instead of `0`. For a phone/IP camera, open the URL in a browser on the same PC first. |
| Feed works but **nothing gets detected** | The model is trained on CCTV-style footage and is weak on close-up webcam video. Lower **Confidence threshold** to 25–30 % in the dashboard and test with real content (e.g. play a sample video in front of the camera). |
| Telegram pill says **not set up** | `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` missing from `.env`; restart after editing. Test with `python test_tele.py`. |
| Login prompt keeps coming back | Wrong user/password; the username defaults to `admin`. |
| `Address already in use` / port busy | Another SentinelX is already running, or change the port in `--listen`. |
| Low FPS | Expected on CPU. Install the CUDA build of PyTorch on an NVIDIA GPU, or use a smaller camera resolution. |
| Hugging Face build fails | Check the **Logs** tab; make sure `Dockerfile` and `requirements.txt` are at the top level of the Space. |
