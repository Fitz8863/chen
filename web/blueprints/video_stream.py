import os
import json
from flask import Blueprint, jsonify

from .models import User
from .auth import admin_required

video_stream_bp = Blueprint('video_stream', __name__, url_prefix='/api')

CAMERAS_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cameras.json')


def load_cameras_config():
    if not os.path.exists(CAMERAS_CONFIG_PATH):
        return []
    try:
        with open(CAMERAS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('cameras', [])
    except Exception:
        return []


@video_stream_bp.route('/cameras')
def list_cameras():
    cameras = load_cameras_config()
    result = []
    for cam in cameras:
        result.append({
            'id': cam.get('id'),
            'name': cam.get('name', f"摄像头 {cam.get('id', '')}"),
            'webrtc_url': cam.get('http_url') or cam.get('rtsp_url'),
            'location': cam.get('location', '未知位置'),
        })
    return jsonify({'cameras': result}), 200
