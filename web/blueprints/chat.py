from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
import os
import uuid
from datetime import datetime
from . import db
from exts import socketio
from .models import User, ChatRoom, ChatRoomMember, ChatMessage

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

online_users = {}


def get_family_room():
    room = ChatRoom.query.filter_by(type='group', is_pinned=True).first()
    if not room:
        room = ChatRoom(name='家庭群', type='group', is_pinned=True)
        db.session.add(room)
        db.session.flush()
        for user in User.query.filter(User.role.in_(['family', 'admin', 'assistant'])).all():
            member = ChatRoomMember(room_id=room.id, user_id=user.id)
            db.session.add(member)
        db.session.commit()
    return room


def get_or_create_private_room(user1_id, user2_id):
    uid_a, uid_b = min(user1_id, user2_id), max(user1_id, user2_id)
    room = ChatRoom.query.filter_by(type='private').join(ChatRoomMember).filter(
        ChatRoomMember.user_id.in_([uid_a, uid_b])
    ).group_by(ChatRoom.id).having(db.func.count(ChatRoomMember.id) == 2).first()
    if not room:
        room = ChatRoom(type='private')
        db.session.add(room)
        db.session.flush()
        db.session.add(ChatRoomMember(room_id=room.id, user_id=uid_a))
        db.session.add(ChatRoomMember(room_id=room.id, user_id=uid_b))
        db.session.commit()
    return room


def user_rooms(user_id):
    rooms = ChatRoom.query.join(ChatRoomMember).filter(ChatRoomMember.user_id == user_id).all()
    result = []
    for r in rooms:
        last_msg = ChatMessage.query.filter_by(room_id=r.id).order_by(ChatMessage.created_at.desc()).first()
        other_members = []
        if r.type == 'private':
            for m in r.members.all():
                if m.user_id != user_id:
                    u = User.query.get(m.user_id)
                    other_members.append({
                        'id': u.id,
                        'nickname': u.nickname or u.username,
                        'avatar': u.avatar,
                        'online': u.id in online_users
                    })
        last_preview = ''
        if last_msg:
            if last_msg.is_recalled:
                last_preview = '撤回了一条消息'
            elif last_msg.message_type == 'image':
                last_preview = '[图片]'
            else:
                last_preview = last_msg.content
        result.append({
            'id': r.id,
            'name': r.name if r.type == 'group' else (other_members[0]['nickname'] if other_members else '未知'),
            'type': r.type,
            'is_pinned': r.is_pinned,
            'last_message': last_preview,
            'last_time': last_msg.created_at.strftime('%H:%M') if last_msg else '',
            'last_sender': (User.query.get(last_msg.sender_id).nickname or User.query.get(last_msg.sender_id).username) if last_msg else '',
            'other_members': other_members,
            'online': other_members[0]['online'] if other_members and r.type == 'private' else False,
        })
    result.sort(key=lambda x: (not x['is_pinned'], x['last_time'] or ''))
    return result


@chat_bp.route('/')
@login_required
def index():
    get_family_room()
    return render_template('chat.html')


@chat_bp.route('/api/rooms')
@login_required
def api_rooms():
    get_family_room()
    return jsonify({'rooms': user_rooms(current_user.id)})


@chat_bp.route('/api/rooms/<int:room_id>/messages')
@login_required
def api_messages(room_id):
    member = ChatRoomMember.query.filter_by(room_id=room_id, user_id=current_user.id).first()
    if not member:
        return jsonify({'error': '无权访问'}), 403
    page = request.args.get('page', 1, type=int)
    per_page = 50
    pagination = ChatMessage.query.filter_by(room_id=room_id).order_by(
        ChatMessage.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    messages = []
    for m in pagination.items:
        sender = User.query.get(m.sender_id)
        reply_content = None
        reply_sender_name = None
        if m.reply_to_id:
            quoted_msg = ChatMessage.query.get(m.reply_to_id)
            if quoted_msg:
                reply_content = quoted_msg.content
                quoted_sender = User.query.get(quoted_msg.sender_id)
                if quoted_sender:
                    reply_sender_name = quoted_sender.nickname or quoted_sender.username
        messages.append({
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_name': sender.nickname or sender.username,
            'sender_avatar': sender.avatar,
            'content': m.content,
            'message_type': m.message_type,
            'image_url': m.image_url,
            'reply_to_id': m.reply_to_id,
            'reply_content': reply_content,
            'reply_sender_name': reply_sender_name,
            'is_recalled': m.is_recalled,
            'time': m.created_at.strftime('%H:%M'),
            'is_mine': m.sender_id == current_user.id,
            'created_at': m.created_at.isoformat(),
        })
    messages.reverse()
    return jsonify({'messages': messages, 'has_more': pagination.has_next})


@chat_bp.route('/api/rooms/<int:room_id>/members')
@login_required
def api_room_members(room_id):
    members = ChatRoomMember.query.filter_by(room_id=room_id).all()
    result = []
    for m in members:
        u = User.query.get(m.user_id)
        if u:
            result.append({
                'id': u.id,
                'nickname': u.nickname or u.username,
                'avatar': u.avatar,
                'role': u.role,
                'online': u.id in online_users
            })
    return jsonify({'members': result})


@chat_bp.route('/api/rooms/create-private', methods=['POST'])
@login_required
def create_private():
    data = request.json
    target_id = data.get('user_id')
    if not target_id or target_id == current_user.id:
        return jsonify({'error': '无效的用户'}), 400
    target = User.query.get(target_id)
    if not target:
        return jsonify({'error': '用户不存在'}), 404
    room = get_or_create_private_room(current_user.id, target_id)
    return jsonify({'room_id': room.id})


@chat_bp.route('/api/users')
@login_required
def api_users():
    users = User.query.filter(User.role.in_(['family', 'admin', 'assistant'])).all()
    return jsonify({
        'users': [{
            'id': u.id,
            'username': u.username,
            'nickname': u.nickname or u.username,
            'avatar': u.avatar,
            'role': u.role,
            'online': u.id in online_users
        } for u in users if u.id != current_user.id]
    })


@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        online_users[current_user.id] = {
            'username': current_user.username,
            'nickname': current_user.nickname or current_user.username,
            'avatar': current_user.avatar,
            'sid': request.sid
        }
        emit('online_status', {'user_id': current_user.id, 'online': True}, broadcast=True)


@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        online_users.pop(current_user.id, None)
        emit('online_status', {'user_id': current_user.id, 'online': False}, broadcast=True)


@socketio.on('join_room')
def handle_join_room(data):
    room_id = data.get('room_id')
    print(f"[SocketIO] User {current_user.id} attempting to join room: {room_id}")
    member = ChatRoomMember.query.filter_by(room_id=room_id, user_id=current_user.id).first()
    if member:
        join_room(str(room_id))
        print(f"[SocketIO] User {current_user.id} joined room: {room_id}")
        emit('joined', {'room_id': room_id})
    else:
        print(f"[SocketIO] User {current_user.id} denied join room: {room_id}")


@socketio.on('leave_room')
def handle_leave_room(data):
    room_id = data.get('room_id')
    leave_room(str(room_id))


@socketio.on('send_message')
def handle_message(data):
    room_id = data.get('room_id')
    content = data.get('content', '').strip()
    image_url = data.get('image_url', '')
    message_type = data.get('message_type', 'text')
    reply_to_id = data.get('reply_to_id')
    
    print(f"[SocketIO] handle_message triggered: room={room_id}, content={content}, type={message_type}, reply_to={reply_to_id}")
    
    if not room_id:
        return
    member = ChatRoomMember.query.filter_by(room_id=room_id, user_id=current_user.id).first()
    if not member:
        print(f"[SocketIO] User {current_user.id} not in room {room_id}")
        return
    sender_name = current_user.nickname or current_user.username
    msg = ChatMessage(
        room_id=room_id,
        sender_id=current_user.id,
        content=content,
        message_type=message_type,
        image_url=image_url,
        reply_to_id=reply_to_id
    )
    db.session.add(msg)
    db.session.commit()
    
    reply_content = None
    reply_sender_name = None
    if reply_to_id:
        quoted_msg = ChatMessage.query.get(reply_to_id)
        if quoted_msg:
            reply_content = quoted_msg.content
            quoted_sender = User.query.get(quoted_msg.sender_id)
            if quoted_sender:
                reply_sender_name = quoted_sender.nickname or quoted_sender.username
    
    payload = {
        'id': msg.id,
        'room_id': room_id,
        'sender_id': current_user.id,
        'sender_name': sender_name,
        'sender_avatar': current_user.avatar,
        'content': content,
        'message_type': message_type,
        'image_url': image_url,
        'time': msg.created_at.strftime('%H:%M'),
        'created_at': msg.created_at.isoformat(),
        'is_recalled': False,
        'reply_to_id': reply_to_id,
        'reply_content': reply_content,
        'reply_sender_name': reply_sender_name
    }
    
    print(f"[SocketIO] Emitting new_message to room {room_id}: {payload}")
    from exts import socketio
    socketio.emit('new_message', payload, room=str(room_id))


@chat_bp.route('/api/upload-image', methods=['POST'])
@login_required
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': '未选择图片'}), 400
    file = request.files['image']
    if not file.filename or file.filename == '':
        return jsonify({'error': '未选择图片'}), 400
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
        return jsonify({'error': '不支持的图片格式'}), 400
    if file.content_length and file.content_length > 10 * 1024 * 1024:
        return jsonify({'error': '图片大小不能超过 10MB'}), 400
    filename = uuid.uuid4().hex[:12] + ext
    save_dir = os.path.join(current_app.static_folder, 'chat_images')
    os.makedirs(save_dir, exist_ok=True)
    file.save(os.path.join(save_dir, filename))
    return jsonify({'url': f'static/chat_images/{filename}'})


@chat_bp.route('/api/messages/<int:msg_id>/recall', methods=['POST'])
@login_required
def recall_message(msg_id):
    msg = ChatMessage.query.get(msg_id)
    if not msg:
        return jsonify({'error': '消息不存在'}), 404
    if msg.sender_id != current_user.id:
        return jsonify({'error': '无权撤回'}), 403
    if (datetime.now() - msg.created_at).total_seconds() > 120:
        return jsonify({'error': '超过2分钟，无法撤回'}), 400
    msg.is_recalled = True
    db.session.commit()
    socketio.emit('message_recalled', {
        'msg_id': msg_id,
        'room_id': msg.room_id,
        'sender_id': msg.sender_id,
    }, room=str(msg.room_id))
    return jsonify({'message': '已撤回'})


@socketio.on('request_recall')
def handle_recall(data):
    msg_id = data.get('msg_id')
    msg = ChatMessage.query.get(msg_id)
    if not msg:
        return
    if msg.sender_id != current_user.id:
        return
    if (datetime.now() - msg.created_at).total_seconds() > 120:
        return
    msg.is_recalled = True
    db.session.commit()
    emit('message_recalled', {
        'msg_id': msg_id,
        'room_id': msg.room_id,
        'sender_id': msg.sender_id,
    }, room=str(msg.room_id))
