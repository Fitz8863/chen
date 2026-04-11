# EdgeGuard 智能家庭安防系统

基于 Flask + YOLO + VLM + MQTT 的家庭安防实时监测系统，支持多路视频流监控、AI 行为分析、云端联动告警。

## 系统概述

EdgeGuard 是一款面向家庭场景的智能安防解决方案，集成计算机视觉推理、多模态大模型分析、MQTT 云端联动三大核心能力。系统采用 MQTT 动态拉取视频流配置，支持边缘设备自治推送。

```
┌─────────────┐      MQTT       ┌─────────────┐
│  边缘设备   │◄───────────►│   云端      │
│  (ESP32)   │  home/info  │  Flask     │
└─────────────┘              └──────┬──────┘
                                   │
                          ┌───────▼───────┐
                          │  MQTT Manager │
                          │  动态配置    │
                          └──────┬───────┘
                                   │
                          ┌───────▼───────┐
                          │  YOLO        │
                          │  推理引擎    │
                          └──────┬───────┘
                                   │
                          ┌───────▼───────┐
                          │  VLM        │
                          │  行为分析   │
                          └─────────────┘
```

## 核心功能

### 云端 Web 管理后台
| 功能模块 | 说明 |
|---------|------|
| 用户认证 | 注册、登录、会话管理，支持「记住我」 |
| MQTT 动态拉流 | 通过 MQTT 订阅 `home/info` 主题动态获取摄像头配置 |
| 实时视频监控 | 支持 RTSP 流和 USB 摄像头，Web 实时预览 |
| AI 行为分析 | YOLO 人体检测 + VLM 多模态大模型异常行为识别 |
| 运动检测优化 | 帧差法预过滤，减少无效推理，节省 CPU |
| 人在持续检测 | 检测到人后短时持续推理，捕捉静态危险动作 |
| 自动告警推送 | 危险行为触发抓拍，发送通知到家庭群 |
| 家庭聊天 | 家庭成员群聊，支持文字、图片消息 |
| 主题切换 | 浅色/深色主题切换 |

### MQTT 联动机制
| 功能 | 说明 |
|------|------|
| 视频流配置 | 订阅 `home/info` 主题，动态获取边缘设备推送的摄像头信息 |
| 状态同步 | 接收边缘设备状态，保持配置实时更新 |
| 告警下发 | 危险行为发生时，可向边缘设备下发告警指令 |

## 技术架构

### 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | Flask 3.1+ (Blueprint 模块化) + Flask-SocketIO |
| 数据库 | MySQL 5.7+ / SQLAlchemy 2.0 |
| 认证 | Flask-Login + Flask-Bcrypt |
| 消息队列 | MQTT (paho-mqtt) 用于边缘设备通信 |
| AI 推理 | Ultralytics YOLO (ONNX/PyTorch) |
| 视频处理 | OpenCV |
| 多模态模型 | Ollama / OpenAI / DashScope API |
| 前端 | HTML5 + Jinja2 + Bootstrap 5.3 |
| 固件 | ESP32 (merged-binary.bin) |

### 系统要求

- **Python**: 3.10+
- **MySQL**: 5.7+
- **MQTT Broker**: 任意兼容 MQTT 3.1.1/3.1 协议 (e.g., Mosquitto)
- **运行环境**: Conda env `bishe`

## 快速开始

### 1. 环境准备

```bash
conda create -n bishe python=3.10
conda activate bishe
```

### 2. 安装依赖

```bash
cd web
pip install -r requirements.txt
pip install paho-mqtt
```

### 3. 数据库初始化

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS home DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 4. MQTT Broker 启动（可选）

```bash
# 使用 Mosquitto
sudo apt install mosquitto
sudo systemctl start mosquitto
```

### 5. 配置修改

编辑 `web/config.py`，修改以下配置：

```python
# 数据库密码
PASSWORD = 'your_mysql_password'

# MQTT 配置（根据实际 broker 修改）
MQTT_BROKER = 'localhost'
MQTT_PORT = 1883
MQTT_USERNAME = ''      # 如需认证填写
MQTT_PASSWORD = ''

# VLM 分析（可选，默认为开启）
VLM_ENABLED = True     # 改为 False 关闭大模型分析
```

### 6. 启动服务

```bash
cd web
python app.py
```

服务启动在 `http://0.0.0.0:5000`

### 7. 边缘设备配置

边缘设备（ESP32）需要向 MQTT Broker 推送 `home/info` 主题，格式如下：

```json
{
    "timestamp_ns": 1234567890,
    "cameras": [
        {
            "id": "001",
            "name": "客厅摄像头",
            "location": "客厅",
            "source": "rtsp://username:password@192.168.1.100:554/stream"
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

## 项目结构

```
chen/
├── README.md                   # 本文件
├── web/                       # Flask Web 应用
│   ├── app.py                # 应用入口
│   ├── config.py            # 配置文件
│   ├── cameras.json         # 本地摄像头配置（备用）
│   ├── exts.py             # Flask 扩展实例
│   ├── AGENTS.md           # 开发规范
│   ├── requirements.txt    # Python 依赖
│   ├── blueprints/        # 蓝图模块
│   │   ├── __init__.py   # 数据库初始化
│   │   ├── models.py    # 数据模型
│   │   ├── main.py    # 首页/监控/告警
│   │   ├── auth.py   # 认证
│   │   ├── chat.py   # 家庭聊天
│   │   ├── capture.py   # 告警抓拍
│   │   ├── mqtt_manager.py  # MQTT 连接管理
│   │   ├── video_inference.py  # YOLO推理进程
│   │   └── video_stream.py    # 视频流API
│   ├── templates/      # Jinja2 模板
│   ├── static/        # 静态资源
│   └── model/         # YOLO 模型文件
└── esp32/                # ESP32 固件
    ├── merged-binary.bin  # 固件二进制
    └── README.md       # 固件说明
```

## 配置文件详解

### MQTT 配置 (config.py)

```python
# MQTT Broker 连接
MQTT_BROKER = 'localhost'    # Broker 地址
MQTT_PORT = 1883           # 端口
MQTT_USERNAME = ''        # 用户名（可选）
MQTT_PASSWORD = ''        # 密码（可选）
```

### YOLO 推理配置

```python
# 模型路径
YOLO_MODEL_PATH = 'model/yolo26n_openvino_model'

# 置信度阈值
YOLO_CONF_THRESHOLD = 0.25
YOLO_IOU_THRESHOLD = 0.45

# 设备选择
YOLO_DEVICE = 'cpu'

# 运动检测优化
MOTION_THRESHOLD = 0.05      # 帧差变化 < 5% 时跳过推理
PERSON_TIMEOUT = 3.0      # 人在持续检测窗口（秒）
FULL_SCAN_INTERVAL = 1.0  # 强制心跳扫描间隔
```

### VLM 分析配置

```python
# 基础开关
VLM_ENABLED = True

# 后端选择：ollama | openai
VLM_BACKEND = 'openai'

# 模型配置
VLM_MODEL_NAME = 'qwen2.5-vl-72b-instruct'
VLM_API_BASE = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
VLM_API_KEY = 'sk-xxxx'

# 推理参数
VLM_FRAME_SKIP = 30        # 抽帧间隔
VLM_ANALYZE_INTERVAL = 3.0  # 分析冷却时间
```

## 告警行为类型

VLM 分析支持识别以下行为：

| 分类 | 行为 |
|------|------|
| 高危 | elderly_fall（老人跌倒）、home_invasion（入室抢劫）、weapon_threat（持刀威胁）、violence（暴力殴打） |
| 中危 | suspicious_intrusion（可疑闯入）、fire_smoke（火灾烟雾）、elderly_abnormal（老人异常） |
| 正常 | normal（正常行为） |

## 用户手册

### 角色权限

| 角色 | 权限 |
|------|------|
| 超级管理员 (admin) | 系统管理、用户管理、摄像头管理、监控、聊天 |
| 家人 (family) | 监控、聊天、告警查看 |
| 游客 (user) | 仅预览监控画面 |

### 首次使用流程

1. 管理员注册账号
2. 确保边缘设备已连接 MQTT 并推送 `home/info`
3. 启动云端服务
4. Web 页面自动显示 MQTT 获取的摄像头
5. 可选：开启 VLM 分析

## 开发者指南

### 开发规范

项目开发规范见 [web/AGENTS.md](web/AGENTS.md)

### 本地开发

```bash
# 激活环境
conda activate bishe

# 启动应用
python app.py

# 检查推理进程
ps -ef | grep video_inference

# 检查 MQTT 连接状态
# 查看日志中的 [MQTT] 相关输出
```

### MQTT 调试

```bash
# 手动订阅主题（使用 mosquitto_sub）
mosquitto_sub -t 'home/info' -v

# 发布测试消息
mosquitto_pub -t 'home/info' -m '{"cameras": []}'
```

## ESP32 固件说明

ESP32 固件执行以下任务：

- 连接 MQTT Broker
- 推送 `home/info` 主题（摄像头配置）
- 订阅告警主题，接收云端告警消息
- 触发 GPIO 输出本地声光告警

### 固件烧录

```bash
# 使用预编译固件
esptool.py --chip esp32 write_flash 0x1000 merged-binary.bin
```

## 常见问题

### 监控页面无画面？

1. 检查边缘设备是否已推送 `home/info`
2. 验证 MQTT 连接：`mosquitto_sub` 订阅主题检查
3. 确认 cameras.json 配置正确

### MQTT 连接失败？

1. 检查 Broker 是否运行：`sudo systemctl status mosquitto`
2. 验证端口可达：`netcat -zv localhost 1883`
3. 检查用户名密码配置

### YOLO 推理卡顿？

1. 使用 ONNX 加速模型
2. 降低 `YOLO_IMG_SIZE`
3. 调整 `YOLO_QUEUE_SIZE`

### VLM API 调用失败？

1. 检查 `VLM_ENABLED = True`
2. 验证 API Key 有效
3. 检查网络能访问 API 地址

---

本项目仅供学习参考。