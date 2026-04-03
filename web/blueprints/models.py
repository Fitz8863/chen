from . import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='user')
    nickname = db.Column(db.String(80), default='')
    avatar = db.Column(db.String(255), default='')

    @property
    def is_super_admin(self):
        return self.role == 'admin'

    @property
    def is_assistant(self):
        return self.role == 'assistant'
    
    @property
    def is_admin(self):
        return self.role in ['admin', 'assistant', 'family']

class Capture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(db.String(50), nullable=False, index=True)
    location = db.Column(db.String(100), nullable=False, index=True)
    image_path = db.Column(db.String(255), nullable=False)
    thumbnail_path = db.Column(db.String(255))
    violation_type = db.Column(db.String(100))
    threat_level = db.Column(db.String(20), default='low')
    num_people_involved = db.Column(db.Integer, default=0)
    evidence = db.Column(db.Text)
    capture_time = db.Column(db.DateTime, default=datetime.now, index=True)


class ChatRoom(db.Model):
    """聊天室：支持群聊和私聊"""
    __tablename__ = 'chat_room'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default='')
    type = db.Column(db.String(20), default='group')
    is_pinned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    members = db.relationship('ChatRoomMember', back_populates='room', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('ChatMessage', back_populates='room', lazy='dynamic', cascade='all, delete-orphan')


class ChatRoomMember(db.Model):
    """聊天室成员"""
    __tablename__ = 'chat_room_member'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    joined_at = db.Column(db.DateTime, default=datetime.now)
    room = db.relationship('ChatRoom', back_populates='members')
    user = db.relationship('User', backref=db.backref('chat_memberships', lazy='dynamic'))
    __table_args__ = (db.UniqueConstraint('room_id', 'user_id', name='uq_room_user'),)


class ChatMessage(db.Model):
    """聊天消息"""
    __tablename__ = 'chat_message'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    content = db.Column(db.Text, default='')
    message_type = db.Column(db.String(20), default='text')
    image_url = db.Column(db.String(255), default='')
    is_recalled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    room = db.relationship('ChatRoom', back_populates='messages')
    sender = db.relationship('User', backref=db.backref('chat_messages', lazy='dynamic'))


