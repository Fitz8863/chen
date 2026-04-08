import json
from flask import Blueprint, jsonify

from .models import User
from .auth import admin_required

video_stream_bp = Blueprint('video_stream', __name__, url_prefix='/api')


def get_cameras():
    """从 MQTT 获取摄像头列表"""
    try:
        from blueprints.mqtt_manager import get_cameras_from_mqtt
        return get_cameras_from_mqtt()
    except Exception:
        return []


@video_stream_bp.route('/cameras')
def list_cameras():
    cameras = get_cameras()
    result = []
    for cam in cameras:
        result.append({
            'id': cam.get('id'),
            'name': cam.get('name', f"摄像头 {cam.get('id', '')}"),
            'source': cam.get('source'),
            'location': cam.get('location', '未知位置'),
        })
    return jsonify({'cameras': result}), 200
