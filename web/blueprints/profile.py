import os
import uuid
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from flask_bcrypt import Bcrypt
from flask import current_app
from . import db
from .models import User

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

AVATAR_UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'static', 'avatars'
)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@profile_bp.route('/')
@login_required
def index():
    return render_template('profile.html')


@profile_bp.route('/update', methods=['POST'])
@login_required
def update_profile():
    data = request.json
    nickname = data.get('nickname', '').strip()
    new_username = data.get('username', '').strip()

    if new_username and new_username != current_user.username:
        existing = User.query.filter_by(username=new_username).first()
        if existing:
            return jsonify({'error': '用户名已被占用'}), 400
        current_user.username = new_username

    if nickname is not None:
        current_user.nickname = nickname

    try:
        db.session.commit()
        return jsonify({'message': '资料已更新', 'nickname': current_user.nickname, 'username': current_user.username})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '更新失败'}), 500


@profile_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.json
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not old_password or not new_password:
        return jsonify({'error': '请填写完整'}), 400

    if new_password != confirm_password:
        return jsonify({'error': '两次输入的新密码不一致'}), 400

    if len(new_password) < 6:
        return jsonify({'error': '密码长度不能少于6位'}), 400

    bcrypt = Bcrypt(current_app._get_current_object())
    if not bcrypt.check_password_hash(current_user.password, old_password):
        return jsonify({'error': '原密码不正确'}), 400

    current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    try:
        db.session.commit()
        return jsonify({'message': '密码修改成功'})
    except Exception:
        db.session.rollback()
        return jsonify({'error': '修改失败'}), 500


@profile_bp.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'error': '请选择图片'}), 400

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': '请选择图片'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': '仅支持 png/jpg/jpeg/gif/webp 格式'}), 400

    os.makedirs(AVATAR_UPLOAD_FOLDER, exist_ok=True)

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(AVATAR_UPLOAD_FOLDER, filename)

    # 删除旧头像
    if current_user.avatar:
        old_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', current_user.avatar)
        if os.path.exists(old_path):
            os.remove(old_path)

    file.save(filepath)
    current_user.avatar = f"avatars/{filename}"

    try:
        db.session.commit()
        return jsonify({'message': '头像上传成功', 'avatar_url': f"/static/{current_user.avatar}"})
    except Exception:
        db.session.rollback()
        return jsonify({'error': '上传失败'}), 500
