import os
import json
from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, jsonify, make_response, abort
from . import db, login_manager
from .auth import admin_required

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'system_config.json')

def load_system_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'allow_registration': True}

def save_system_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

@settings_bp.before_request
def before_request():
    if not current_user.is_authenticated:
        return login_manager.unauthorized()
    if request.path.startswith('/settings/api/video/stream/') or request.path.startswith('/settings/api/audio/stream/'):
        return
    if request.path.startswith('/settings/api/system/config'):
        if not current_user.is_super_admin:
            abort(403)

@settings_bp.route('/api/system/config', methods=['GET'])
def get_system_config():
    config = load_system_config()
    return jsonify(config), 200

@settings_bp.route('/api/system/config', methods=['POST'])
def update_system_config():
    data = request.json
    config = load_system_config()
    
    if 'allow_registration' in data:
        config['allow_registration'] = bool(data['allow_registration'])
    
    save_system_config(config)
    return jsonify({'message': '配置已更新', 'config': config}), 200

@settings_bp.route('/')
def index():
    """系统设置页面"""
    return render_template('settings.html')


@settings_bp.route('/api/video/stream/<camera_id>')
def video_stream(camera_id):
    """YOLO推理视频流接口"""
    try:
        from blueprints.video_inference import video_inference
        from blueprints.video_stream import load_cameras_config

        cameras = load_cameras_config()
        stream_url = None
        for cam in cameras:
            if str(cam.get('id', '')) == str(camera_id):
                stream_url = cam.get('rtsp_url') or cam.get('http_url', '')
                break

        if not stream_url:
            return f"未找到摄像头 {camera_id} 的流地址", 404

        video_inference.get_or_create_capture(camera_id, stream_url)

        def generate():
            while True:
                frame = video_inference.get_frame(camera_id)
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                else:
                    import time
                    time.sleep(0.03)

        response = make_response(generate())
        response.headers['Content-Type'] = 'multipart/x-mixed-replace; boundary=frame'
        return response

    except Exception as e:
        return str(e), 500


@settings_bp.route('/api/cameras/add', methods=['POST'])
def add_camera():
    try:
        data = request.json
        name = data.get('name')
        url = data.get('url')
        
        if not name or not url:
            return jsonify({'error': '名称和地址不能为空'}), 400
            
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cameras.json')
        
        cameras = []
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                cameras = config.get('cameras', [])
        
        import uuid
        new_id = str(uuid.uuid4().hex[:8])
        
        new_camera = {
            'id': new_id,
            'name': name,
            'location': name,
            'rtsp_url': url if url.startswith('rtsp') else '',
            'http_url': url if not url.startswith('rtsp') else ''
        }
        
        cameras.append(new_camera)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump({'cameras': cameras}, f, ensure_ascii=False, indent=4)
            
        return jsonify({'message': '摄像头添加成功', 'id': new_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/api/vlm/status/<camera_id>', methods=['GET'])
def get_vlm_status(camera_id):
    """获取特定摄像头的最新 VLM 分析结果"""
    try:
        from blueprints.video_inference import video_inference
        with video_inference.lock:
            c_data = video_inference.captures.get(camera_id)
        
        if not c_data:
            return jsonify({'active': False}), 200
        
        with c_data['lock']:
            vlm_result = c_data.get('vlm_result')
            last_vlm_time = c_data.get('last_vlm_time', 0)
        
        if not vlm_result or last_vlm_time == 0:
            return jsonify({'active': False}), 200
        
        import time
        elapsed = time.time() - last_vlm_time
        
        return jsonify({
            'active': True,
            'result': vlm_result,
            'timestamp': last_vlm_time,
            'elapsed': round(elapsed, 1)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 通过 VideoInference 统一全局管理音频进程，防止双重启动
@settings_bp.route('/api/audio/control/<camera_id>', methods=['POST'])
def audio_control(camera_id):
    """前端音频控制接口：只改变后台静音状态标志位，绝不自己启动进程"""
    try:
        from blueprints.video_inference import video_inference
        data = request.get_json() or {}
        action = data.get('action')
        
        if action == 'status':
            is_playing = video_inference.is_audio_playing(camera_id)
            return jsonify({"playing": is_playing}), 200

        elif action == 'stop':
            video_inference.set_audio_muted(camera_id, True)
            return jsonify({"status": "stopped"}), 200

        elif action == 'play':
            video_inference.set_audio_muted(camera_id, False)
            return jsonify({"status": "play_requested"}), 200

        return jsonify({"error": "无效的 action"}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500




