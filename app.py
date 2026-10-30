import os
import csv
import io
import hmac

from dotenv import load_dotenv

# Load .env before importing modules that read credentials at import time.
# Explicit path so it works regardless of the current working directory.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

from flask import Flask, render_template, Response, jsonify, request
from sqlalchemy import or_, and_

from camera import Detector, BASE_DIR
from models import db, Alert
from telegram_alerts import is_configured as telegram_configured

app = Flask(__name__)
# SQLite (stored in instance/sentinelx.db) by default; set DATABASE_URL for MySQL etc.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///sentinelx.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

detector = Detector(app)

# Optional HTTP Basic auth: set SENTINELX_PASSWORD to protect the whole dashboard
DASHBOARD_USER = os.environ.get('SENTINELX_USER', 'admin')
DASHBOARD_PASSWORD = os.environ.get('SENTINELX_PASSWORD', '')


@app.before_request
def require_login():
    if not DASHBOARD_PASSWORD:
        return None
    auth = request.authorization
    if (auth and auth.type == 'basic'
            and hmac.compare_digest((auth.username or '').encode(), DASHBOARD_USER.encode())
            and hmac.compare_digest((auth.password or '').encode(), DASHBOARD_PASSWORD.encode())):
        return None
    return Response('Login required', 401, {'WWW-Authenticate': 'Basic realm="SentinelX"'})

WEAPON_FILTER = or_(Alert.message.like('%guns%'), Alert.message.like('%knife%'))
VIOLENCE_FILTER = and_(Alert.message.like('%Violence%'), ~Alert.message.like('%NonViolence%'))


@app.route('/')
def index():
    detector.start()
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(detector.frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_alerts')
def get_alerts():
    alerts = Alert.query.order_by(Alert.timestamp.desc()).limit(50).all()
    return jsonify({
        'alerts': [a.to_dict() for a in alerts],
        'stats': {
            'total': Alert.query.count(),
            'weapons': Alert.query.filter(WEAPON_FILTER).count(),
            'violence': Alert.query.filter(VIOLENCE_FILTER).count(),
        },
    })

@app.route('/get_current_detections')
def current_detections():
    return jsonify({'detections': detector.get_current_detections()})

@app.route('/status')
def status():
    detector.start()
    return jsonify({**detector.get_status(), 'telegram_configured': telegram_configured()})

@app.route('/clear_alerts', methods=['POST'])
def clear_alerts():
    alerts = Alert.query.all()
    for a in alerts:
        try:
            os.remove(os.path.join(BASE_DIR, a.snapshot_path))
        except OSError:
            pass
    Alert.query.delete()
    db.session.commit()
    return jsonify({'cleared': len(alerts)})

@app.route('/export_alerts')
def export_alerts():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['id', 'timestamp', 'message', 'snapshot'])
    for a in Alert.query.order_by(Alert.timestamp.desc()).all():
        writer.writerow([a.id, a.timestamp.isoformat(), a.message, a.snapshot_path])
    return Response(buf.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=sentinelx_alerts.csv'})

@app.route('/capture', methods=['POST'])
def capture():
    path = detector.capture()
    if path is None:
        return jsonify({'error': 'No frame available yet'}), 503
    return jsonify({'snapshot': '/' + path})

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'GET':
        return jsonify(detector.get_settings())

    data = request.get_json(silent=True) or {}
    try:
        new = {
            'confidence': min(max(float(data['confidence']), 0.1), 0.9),
            'cooldown': min(max(int(data['cooldown']), 5), 60),
            'telegram_enabled': bool(data['telegram_enabled']),
        }
    except (KeyError, TypeError, ValueError):
        return jsonify({'error': 'Expected confidence, cooldown and telegram_enabled'}), 400
    return jsonify(detector.update_settings(new))


if __name__ == '__main__':
    # Debug mode exposes the Werkzeug debugger (remote code execution) - opt in only
    debug = os.environ.get('FLASK_DEBUG') == '1'
    app.run(host=os.environ.get('HOST', '127.0.0.1'),
            port=int(os.environ.get('PORT', 5002)),
            debug=debug, threaded=True)
