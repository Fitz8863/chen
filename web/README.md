# 家庭安防智能监测系统

基于 Flask 的家庭安防实时监测系统，支持多路视频流监控、AI 行为分析、自动告警推送、以及家庭群聊通知。

## 功能特性

- **用户认证**：完整的注册、登录、会话管理，支持"记住我"
- **实时视频监控**：支持 RTSP 流和 USB 摄像头（/dev/video0），经过 YOLO 人体检测推理后推送至前端
- **AI 行为分析**：集成 VLM 多模态大模型（Ollama/OpenAI），分析画面中是否有老人跌倒、入室抢劫、持刀威胁等异常行为
- **运动检测优化**：高斯模糊 + 帧差法预过滤，画面变化 < 5% 时跳过 YOLO 推理，节省 CPU
- **人在持续检测**：检测到人后 3 秒内持续执行 YOLO 推理，确保捕捉静态危险动作（如老人跌倒不起）
- **自动告警推送**：VLM 检测到危险行为时，自动抓拍并通过"家庭助手"发送告警消息到家庭群
- **家庭聊天**：家庭成员群聊支持，支持文字、图片消息
- **主题切换**：支持浅色/深色主题切换

## 技术栈

### 后端
- Flask 3.1+ (Blueprint 模块化)
- MySQL 5.7+
- SQLAlchemy 2.0
- Flask-Login + Flask-Bcrypt
- Ultralytics YOLO (ONNX/PyTorch)
- OpenCV (视频流处理)

### 前端
- HTML5 + Jinja2 Templates
- Bootstrap 5.3
- Font Awesome 6.0
- Vanilla JavaScript (ES6+)

## 项目结构

```
web/
├── app.py                      # Flask 应用入口
├── config.py                   # 配置文件（数据库、AI、VLM、YOLO配置）
├── cameras.json                # 摄像头配置
├── exts.py                     # Flask 扩展实例
├── blueprints/                 # 蓝图模块
│   ├── __init__.py            # 数据库初始化、全局认证钩子
│   ├── models.py              # SQLAlchemy 模型
│   ├── main.py                # 首页、监控、告警页面
│   ├── auth.py                # 认证（登录/注册）
│   ├── chat.py                # 家庭聊天
│   ├── capture.py             # 告警抓拍上传
│   ├── video_stream.py        # 摄像头列表 API
│   ├── video_inference.py     # YOLO 推理 + VLM 分析守护进程
│   ├── settings.py             # 系统设置、摄像头管理
│   └── user_management.py      # 用户管理
├── templates/                  # Jinja2 模板
├── static/                     # 静态资源
└── AGENTS.md                   # 开发规范
```

## 快速开始

### 1. 环境准备

```bash
conda create -n bishe python=3.10
conda activate bishe
```

### 2. 安装依赖

```bash
pip install Flask==3.1.3 Flask-SQLAlchemy==3.1.1 Flask-Login==0.6.3
pip install Flask-Bcrypt==1.0.1 PyMySQL==1.1.2 SQLAlchemy==2.0.48
pip install opencv-python ultralytics requests
```

### 3. 数据库配置

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS home DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;"
```

修改 `config.py` 中的数据库密码。

### 4. 启动服务

```bash
python app.py
```

服务启动在 `http://0.0.0.0:5000`

## 摄像头配置

### 方式一：cameras.json

```json
{
    "cameras": [
        {
            "id": "001",
            "name": "客厅摄像头",
            "location": "客厅",
            "source": "rtsp://username:password@192.168.1.100:554/stream",
            "username": "",
            "password": ""
        },
        {
            "id": "002",
            "name": "USB摄像头",
            "location": "门口",
            "source": "/dev/video0"
        }
    ]
}
```

- `source` 支持 RTSP 流和 USB 设备（/dev/video*）
- RTSP 可选填 `username` 和 `password`

### 方式二：前端输入框

在监控页面直接输入 RTSP 地址和名称即可添加。

## 用户角色

- **超级管理员 (admin)**：系统管理权限
- **家人 (family)**：可访问监控、聊天
- **游客 (user)**：仅预览

## AI 分析配置

在 `config.py` 中配置：

```python
VLM_ENABLED = True
VLM_BACKEND = 'ollama'  # 或 'openai'
VLM_MODEL_NAME = 'llama3.2-vision'
VLM_API_BASE = 'http://localhost:11434/api/generate'
VLM_PROMPT = '你是一个家庭安防分析师...'
```

## 常见问题

**Q: 监控页面黑屏无画面？**
A: 检查 cameras.json 配置是否正确，RTSP 地址是否可访问，username/password 是否填写正确。

**Q: YOLO 推理帧率过低？**
A: 确保使用 CPU 推理时配置较低分辨率，或使用 GPU/ONNX 加速。

---

本项目仅供学习参考。
