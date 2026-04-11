# EdgeGuard 智能家庭安防系统

基于 Flask + YOLO + VLM 的家庭安防实时监测系统，支持多路视频流监控、AI 行为分析、ESP32 硬件告警推送。

## 系统概述

EdgeGuard 是一款面向家庭场景的智能安防解决方案，集成计算机视觉推理、多模态大模型分析、实时告警推送三大核心能力。系统由 Web 管理后台和 ESP32 硬件终端两部分组成，通过 MQTT 协议实现云端联动——当 AI 检测到危险行为时，ESP32 设备可触发本地声光告警，同时向家庭群推送通知。

```
┌─────────────┐      MQTT       ┌─────────────┐
│  ESP32      │◄──────────────►│   云端      │
│  硬件终端   │                │  Flask     │
└─────────────┘                └──────┬─────┘
                                     │
                              ┌──────▼──────┐
                              │  YOLO       │
                              │  推理引擎   │
                              └──────┬──────┘
                                     │
                              ┌──────▼──────┐
                              │  VLM       │
                              │  行为分析  │
                              └────────────┘
```

## 核心功能

### Web 管理后台
| 功能模块 | 说明 |
|---------|------|
| 用户认证 | 注册、登录、会话管理，支持「记住我」 |
| 实时视频监控 | 支持 RTSP 流和 USB 摄像头，Web 实时预览 |
| AI 行为分析 | YOLO 人体检测 + VLM 多模态大模型异常行为识别 |
| 运动检测优化 | 帧差法预过滤，减少无效推理，节省 CPU |
| 人在持续检测 | 检测到人后短时持续推理，捕捉静态危险动作 |
| 自动告警推送 | 危险行为触发抓拍，发送通知到家庭群 |
| 家庭聊天 | 家庭成员群聊，支持文字、图片消息 |
| 主题切换 | 浅色/深色主题切换 |

### ESP32 硬件终端
| 功能模块 | 说明 |
|---------|------|
| 告警执行 | 接收 MQTT 告警消息，触发本地声光提示 |
| 状态上报 | 定期上报设备在线状态 |
| 远程配置 | 支持 MQTT 主题配置 修改设备参数 |

## 技术架构

### 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | Flask 3.1+ (Blueprint 模块化) |
| 数据库 | MySQL 5.7+ / SQLAlchemy 2.0 |
| 认证 | Flask-Login + Flask-Bcrypt |
| AI 推理 | Ultralytics YOLO (ONNX/PyTorch) |
| 视频处理 | OpenCV |
| 多模态模型 | Ollama / OpenAI / DashScope API |
| 前端 | HTML5 + Jinja2 + Bootstrap 5.3 |
| 通信协议 | MQTT (ESP32 云端联动) |
| 固件 | ESP32 (merged-binary.bin) |

### 系统要求

- **Python**: 3.10+
- **MySQL**: 5.7+
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
```

### 3. 数据库初始化

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS home DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 4. 配置修改

编辑 `web/config.py`，修改以下配置：

```python
# 数据库密码
PASSWORD = 'your_mysql_password'

# VLM 分析（可选，默认为关闭）
VLM_ENABLED = False  # 改为 True 开启大模型联动分析
```

### 5. 启动服务

```bash
cd web
python app.py
```

服务启动在 `http://0.0.0.0:5000`

### 6. 添加摄像头

摄像头配置方式任选其一：

**方式一：编辑 cameras.json**

```json
{
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

**方式二：前端添加**

在监控页面直接输入 RTSP 地址和名称即可添加。

## Web 应用详细文档

### 项目结构

```
chen/
├── README.md                   # 本文件
├── web/                       # Flask Web 应用
│   ├── app.py                 # 应用入口
│   ├── config.py              # 配置文件
│   ├── cameras.json          # 摄像头配置
│   ├── exts.py              # Flask 扩展实例
│   ├── AGENTS.md            # 开发规范
│   ├── requirements.txt     # Python 依赖
│   ├── blueprints/         # 蓝图模块
│   │   ├── __init__.py    # 数据库初始化
│   │   ├── models.py     # 数据模型
│   │   ├── main.py      # 首页/监控/告警
│   │   ├── auth.py      # 认证
│   │   ├── chat.py     # 家庭聊天
│   │   ├── capture.py # 告警抓拍
│   │   └── video_inference.py  # YOLO推理进程
│   ├── templates/          # Jinja2 模板
│   ├── static/            # 静态资源
│   └── model/             # YOLO 模型文件
└── esp32/                    # ESP32 固件
    ├── merged-binary.bin    # 固件二进制
    └── README.md         # 固件说明（待补充）
```

### AI 分析配置

在 `web/config.py` 中配置 VLM 分析：

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
VLM_FRAME_SKIP = 30      # 抽帧间隔
VLM_ANALYZE_INTERVAL = 3.0  # 分析冷却时间
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

# 运动检测
MOTION_THRESHOLD = 0.05   # 帧差变化 < 5% 时跳过推理
PERSON_TIMEOUT = 3.0       # 人在持续检测窗口（秒）
FULL_SCAN_INTERVAL = 1.0   # 强制心跳扫描间隔
```

### 告警行为类型

VLM 分析支持识别以下行为类型：

| 分类 | 行为 |
|------|------|
| 高危 | elderly_fall（老人跌倒）、home_invasion（入室抢劫）、weapon_threat（持刀威胁）、violence（暴力殴打） |
| 中危 | suspicious_intrusion（可疑人员闯入）、fire_smoke（火灾烟雾）、elderly_abnormal（老人行动异常） |
| 正常 | normal（正常行为） |

## ESP32 固件说明

### 功能定义

current firmware 执行以下任务：

- 订阅 MQTT 告警主题，接收云端告警消息
- 触发 GPIO 输出（蜂鸣器/LED）本地声光告警
- 定期发布设备状态 heartbeat
- 支持远程配置更新（通过 MQTT 主题）

### 固件烧录

使用 ESP-IDF 或 Espressif 工具链编译烧录：

```bash
# 编译
idf.py build

# 烧录
idf.py -p /dev/ttyUSB0 flash monitor
```

或使用预编译的 `merged-binary.bin` 直接烧录：

```bash
esptool.py --chip esp32 write_flash 0x1000 merged_binary.bin
```

## 用户��册

### 角色权限

| 角色 | 权限 |
|------|------|
| 超级管理员 (admin) | 系统管理、用户管理、摄像头管理、监控、聊天 |
| 家人 (family) | 监控、聊天、告警查看 |
| 游客 (user) | 仅预览监控画面 |

### 首次使用流程

1. 管理员注册账号
2. 登录后台，添加摄像头
3. 启动服务，开始监控
4. 可选：开启 VLM 分析 `VLM_ENABLED = True`
5. 可选：配置 ESP32 硬件联动

## 开发者指南

### 开发规范

项目开发规范见 [web/AGENTS.md](web/AGENTS.md)，主要要点：

- 使用中文回答所有问题
- 遵循 Blueprint 模块化架构
- 数据库使用 SQLAlchemy，避免原生 SQL
- API 路由使用 `/api/` 前缀
- 前端使用 fetch API 异步通信
- 代码变更需验证后提交

### 本地开发

```bash
# 激活环境
conda activate bishe

# 启动应用（开发模式）
python app.py

# 检查推理进程
ps -ef | grep video_inference
```

### 调试技巧

- 开启 SQL 查询日志：`SQLALCHEMY_ECHO = True` 在 config.py
- 查看 SocketIO 连接：浏览器 console 监听 `connect`/`disconnect`
- 推理进程卡死：`ps -ef | grep video_inference` 找到 PID 后 `kill`

## 常见问题

### 监控页面黑屏无画面？

1. 检查 cameras.json 配置是否正确
2. 验证 RTSP 地址可访问：`ffplay rtsp://...`
3. 确认 username/password 填写正确

### YOLO 推理帧率过低？

1. 使用 GPU 或 ONNX 加速模型
2. 降低 `YOLO_IMG_SIZE`
3. 调整 `YOLO_QUEUE_SIZE`

### VLM API 调用失败？

1. 检查 `VLM_ENABLED = True`
2. 验证 API Key 有效
3. 检查网络能访问 API 地址

### ESP32 无法接收告警？

1. 确认 MQTT Broker 可连接
2. 检查设备订阅主题是否正确
3. 查看串口日志输出

---

本项目仅供学习参考。