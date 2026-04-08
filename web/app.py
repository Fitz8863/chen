from flask import Flask, render_template
from flask_bcrypt import Bcrypt
import config
import os

from exts import socketio

app = Flask(__name__,
template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
static_folder=os.path.join(os.path.dirname(__file__), 'static'))

app.config.from_object(config)

@app.context_processor
def inject_config():
    from flask import Flask
    return dict(AI_URL=config.AI_URL)

bcrypt = Bcrypt(app)
socketio.init_app(app)

from blueprints import init_db
init_db(app)

def ensure_family_assistant():
    from blueprints.models import User, ChatRoom, ChatRoomMember
    from blueprints import db
    from flask_bcrypt import Bcrypt
    with app.app_context():
        assistant = User.query.filter_by(username='family_assistant').first()
        if not assistant:
            bcrypt = Bcrypt(app)
            hashed = bcrypt.generate_password_hash('assistant_auto_2026').decode('utf-8')
            assistant = User(
                username='family_assistant',
                password=hashed,
                role='family',
                nickname='家庭助手',
                avatar=''
            )
            db.session.add(assistant)
            db.session.commit()
            print("[System] 家庭助手用户已自动创建")
        room = ChatRoom.query.filter_by(type='group', is_pinned=True).first()
        if room:
            member = ChatRoomMember.query.filter_by(room_id=room.id, user_id=assistant.id).first()
            if not member:
                db.session.add(ChatRoomMember(room_id=room.id, user_id=assistant.id))
                db.session.commit()
                print("[System] 家庭助手已加入家庭群")
        else:
            print("[System] 家庭群尚未创建，将在首次访问聊天页时自动加入")

ensure_family_assistant()


from blueprints.main import main_bp
from blueprints.auth import auth_bp
from blueprints.capture import capture_bp
from blueprints.settings import settings_bp
from blueprints.user_management import user_mgmt_bp
from blueprints.profile import profile_bp
from blueprints.chat import chat_bp
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(capture_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(user_mgmt_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(chat_bp)

# 在系统启动时强制唤醒后台 AI 守护进程，接管所有边缘设备的自动拉流
# 核心修复：通过检查 WERKZEUG_RUN_MAIN 环境变量，确保在开启 Reloader 的情况下也只运行一次 AI 实例化
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.config.get('DEBUG'):
    try:
        from blueprints.video_inference import video_inference
        video_inference.app = app
        print("[System] 后台视频监控/推理守护进程已成功唤醒（主进程单例）。")
        
        # 添加守护进程心跳监控
        def check_inference_daemon():
            import threading
            import time
            while True:
                time.sleep(30)
                threads = [t.name for t in threading.enumerate()]
                if not any(t.startswith("DaemonSyncThread") for t in threads):
                    print("[System] 警告：视频监控守护进程已停止，请检查系统负载或推理配置。")
        
        socketio.start_background_task(check_inference_daemon)
    except Exception as e:
        print(f"[System] 警告：后台视频守护进程启动失败: {e}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
