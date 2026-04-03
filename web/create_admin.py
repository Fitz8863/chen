import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from blueprints import db
from blueprints.models import User
from flask_bcrypt import generate_password_hash

def create_admin_user():
    with app.app_context():
        username = 'root'
        password = 'admin'
        role = 'admin'

        user = User.query.filter_by(username=username).first()
        
        if user:
            print(f"用户 '{username}' 已存在，正在重置密码为 'admin' 并确认为管理员...")
            user.password = generate_password_hash(password).decode('utf-8')
            user.role = role
        else:
            print(f"正在创建超级管理员用户 '{username}'...")
            hashed_password = generate_password_hash(password).decode('utf-8')
            user = User(username=username, password=hashed_password, role=role)
            db.session.add(user)
        
        try:
            db.session.commit()
            print("✅ 操作成功！您现在可以使用 root / admin 登录系统。")
        except Exception as e:
            db.session.rollback()
            print(f"❌ 数据库操作失败：{e}")

if __name__ == "__main__":
    create_admin_user()
