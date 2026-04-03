# 校园安防智能监测系统 (Campus Security Intelligent Monitoring System)

基于 Flask 的校园安防实时监测系统，支持多路视频流监控、校园违规行为自动抓拍告警、以及多摄像头的统一管理。

## 🌟 功能特性

- **🔒 用户认证系统**：完整的用户注册、登录、会话管理，支持“记住我”功能。
- **📹 实时视频监控**：多摄像头视频流并发监控，支持 WebRTC/RTSP 实时视频流低延迟播放。
- **⚠️ 校园行为监测与告警**：接收并记录远程摄像头/边缘计算节点自动检测到的校园行为（如：攀爬围栏、打架斗殴、人员聚集等）。
- **📊 告警记录管理**：查看和管理所有抓拍记录，支持按时间流展示、图片预览、以及违规数据大屏统计。
- **📱 响应式设计**：基于 Bootstrap 5 构建的现代化深色主题 UI，兼容桌面与移动设备。

---

## 🛠️ 技术栈

### 后端 (Backend)
- **核心框架**: Flask 3.1+ (采用 Blueprint 模块化架构)
- **数据库**: MySQL 5.7+
- **ORM**: SQLAlchemy 2.0 (Flask-SQLAlchemy 3.1.1)
- **身份认证**: Flask-Login 0.6.3 + Flask-Bcrypt 1.0.1

### 前端 (Frontend)
- **页面框架**: HTML5 + Jinja2 Templates
- **UI 库**: Bootstrap 5.3
- **图标库**: Font Awesome 6.0
- **交互与图表**: Vanilla JavaScript (ES6+), 原生 Fetch API

---

## 📁 项目结构

```text
campus_security/
├── app.py                      # Flask 应用主入口
├── config.py                   # 核心配置文件（包含数据库、邮箱、YOLO、VLM配置）
├── cameras.json                # 摄像头静态配置文件
├── exts.py                     # Flask 扩展实例库（解决循环导入问题）
├── blueprints/                 # Flask 蓝图模块（MVC 控制器层）
│   ├── __init__.py             # 数据库初始化及 LoginManager 配置
│   ├── models.py               # SQLAlchemy 数据库模型定义 (User, Capture)
│   ├── main.py                 # 主页面及仪表盘路由
│   ├── auth.py                 # 身份认证（登录/注册/注销）
│   ├── capture.py              # 告警抓拍数据上传及查询 API
│   ├── video_stream.py         # 视频流读取及摄像头状态管理
│   ├── video_inference.py      # AI 推理守护进程逻辑
│   └── settings.py             # 系统设置 (系统配置与安全设置)
├── templates/                  # 视图模板 (Jinja2)
│   ├── base.html               # 全局基础布局 (导航栏, Flash 提示, 页脚)
│   ├── index.html              # 首页仪表盘
│   ├── login.html / register.html # 认证相关页面
│   ├── monitor.html            # 实时视频监控面板
│   ├── alerts.html             # 抓拍告警记录流
│   └── settings.html           # 统一设置中心
├── static/                     # 静态资源文件
│   ├── bootstrap/              # Bootstrap 框架本地缓存
│   ├── css/style.css           # 全局自定义 CSS 样式
│   ├── img/                    # UI 图片资源
│   └── captures/               # 【动态目录】存储远程上传的抓拍违规图片
└── AGENTS.md                   # Agent 开发与代码规范指南
```

---

## 🚀 快速开始

### 1. 环境准备

建议使用 Python 3.10 及以上版本，以及 MySQL 5.7/8.0。推荐使用 Conda 管理虚拟环境。

```bash
# 克隆代码
git clone <repository-url>
cd campus_security

# 创建并激活 Conda 环境
conda create -n bishe python=3.10
conda activate bishe
```

### 2. 安装依赖

```bash
pip install Flask==3.1.3 Flask-SQLAlchemy==3.1.1 Flask-Login==0.6.3
pip install Flask-Bcrypt==1.0.1 PyMySQL==1.1.2 SQLAlchemy==2.0.48
```

### 3. 配置数据库

启动 MySQL，并创建对应的数据库：
```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS home DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;"
```

**修改 `config.py` 中的数据库连接参数：**
```python
HOSTNAME = '127.0.0.1'      
PORT = 3306                 
USERNAME = 'root'           
PASSWORD = 'your_password'  # 替换为你的 MySQL 密码
DATABASE = 'home'        
```

### 4. 运行服务

```bash
python app.py
```

服务将启动在 `http://0.0.0.0:5000`。浏览器访问 `http://localhost:5000` 即可进入系统（首次进入需先注册账号）。数据库表会在首次启动时自动创建。

---

## 🔌 API 文档与边缘端接入

### 1. 抓拍图片上传接口
当边缘设备检测到校园违规行为时，调用此接口上传图片和违规信息。
- **接口**: `POST /capture/upload`
- **Content-Type**: `multipart/form-data`
- **参数**:
  - `file`: (File) 抓拍的图片文件
  - `camera_id`: (String) 摄像头编号
  - `location`: (String) 抓拍地点
  - `violation_type`: (String) 违规类型（如：攀爬围栏）

**调用示例 (Python)**:
```python
import requests

url = "http://192.168.1.100:5000/capture/upload"
files = {'file': open('alert.jpg', 'rb')}
data = {
    'camera_id': '001',
    'location': '西门围栏',
    'violation_type': '攀爬围栏'
}
requests.post(url, files=files, data=data)
```

---

## 🔧 常见问题 (FAQ)

**Q1: 为什么监控页面看不到视频画面？**
A: 请确保 `cameras.json` 中的 `rtsp_url` 或 `http_url` 是可访问的视频流服务地址。

**Q2: 数据库表没有创建？**
A: `app.py` 中通过 `init_db(app)` 和 `db.create_all()` 在应用启动时自动建表。如果未建表，请检查 `config.py` 的密码是否正确，并确保已手动执行 `CREATE DATABASE home;` 创建了 Database。

---

## 💻 开发指南

- 新增功能与代码规范：请务必阅读本项目的 [AGENTS.md](AGENTS.md)。
- 本项目遵循 **Flask 工厂模式和 Blueprint 蓝图分离** 的设计理念，所有新增模块需在 `blueprints/` 目录下创建。
- 模型变更需在 `models.py` 内实现。由于未引入 Alembic/Flask-Migrate，若修改模型字段，需手动更新数据库或清空数据库后重启应用。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。
