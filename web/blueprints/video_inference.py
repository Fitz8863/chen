import sys
import os

# 将项目根目录添加到 sys.path，以便正确导入 config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# 使用 config.xxx 访问配置，更加清晰且不会出现 NameError
YOLO_MODEL_PATH = config.YOLO_MODEL_PATH
YOLO_CONF_THRESHOLD = config.YOLO_CONF_THRESHOLD
YOLO_IOU_THRESHOLD = config.YOLO_IOU_THRESHOLD
YOLO_DEVICE = config.YOLO_DEVICE
YOLO_IMG_SIZE = config.YOLO_IMG_SIZE
YOLO_QUEUE_SIZE = config.YOLO_QUEUE_SIZE
MOTION_THRESHOLD = config.MOTION_THRESHOLD
FULL_SCAN_INTERVAL = config.FULL_SCAN_INTERVAL
PERSON_TIMEOUT = config.PERSON_TIMEOUT
VLM_ENABLED = config.VLM_ENABLED
VLM_BACKEND = config.VLM_BACKEND
VLM_API_BASE = config.VLM_API_BASE
VLM_API_KEY = config.VLM_API_KEY
VLM_MODEL_NAME = config.VLM_MODEL_NAME
VLM_FRAME_SKIP = config.VLM_FRAME_SKIP
VLM_ANALYZE_INTERVAL = config.VLM_ANALYZE_INTERVAL
VLM_PROMPT = config.VLM_PROMPT

import cv2
import threading
import numpy as np
import time
import requests
import base64
import json
from collections import defaultdict
from queue import Queue, Empty, Full
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urlunparse, quote



def _load_cameras_config():
    """从 cameras.json 加载摄像头配置"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'cameras.json'
    )
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('cameras', [])
    except Exception as e:
        print(f"[Config] 加载 cameras.json 失败: {e}")
        return []

def _format_camera_source(source, username, password):
    if not source:
        return source
    if source.startswith('rtsp://') and username and password:
        return _format_rtsp_url(source, username, password)
    return source
    if not username or not password:
        return url
    
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        return url 
        
    # 安全编码用户名和密码
    safe_user = quote(str(username), safe='')
    safe_pass = quote(str(password), safe='')
    
    netloc = f"{safe_user}:{safe_pass}@{parsed.netloc}"
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

third_party_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '3rdparty'
)
if third_party_path not in sys.path:
    sys.path.insert(0, third_party_path)

from ultralytics import YOLO

class VideoInference:
    def __init__(self, model_path=YOLO_MODEL_PATH):
        self.pid = os.getpid()
        print(f"[VideoInference] 正在实例化守护进程，当前 PID: {self.pid}")
        
        self.app = None
        self.model = None
        self.model_path = model_path
        self.captures = {}
        self.lock = threading.Lock()
        self.fps_stats = defaultdict(lambda: {"count": 0, "start_time": time.time(), "display": 0})
        
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer"
        
        self.vlm_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="VLM")
        
        self.running = True
        daemon_thread = threading.Thread(target=self._daemon_sync_loop, daemon=True)
        daemon_thread.name = f"DaemonSyncThread-{self.pid}"
        daemon_thread.start()
        
    def _daemon_sync_loop(self):
        """全天候同步守护进程：根据 cameras.json 配置自动维持所有摄像头的拉流和推理"""
        while self.running:
            # time.sleep(3.0)
            try:
                active_cameras = _load_cameras_config()
                if not active_cameras:
                    continue
                    
                active_ids = set()
                
                for cam in active_cameras:
                    cam_id = str(cam.get('id', ''))
                    if not cam_id: continue
                    active_ids.add(cam_id)
                    
                    source = cam.get('source')
                    if source:
                        formatted_url = _format_camera_source(source, cam.get('username'), cam.get('password'))
                        self.get_or_create_capture(cam_id, formatted_url)
                        
                with self.lock:
                    cameras_to_stop = [cid for cid in self.captures.keys() if cid not in active_ids]
                    
                for cid in cameras_to_stop:
                    print(f"[VideoInference] 摄像头 {cid} 已从配置中移除，自动停止视频推理资源")
                    self.stop_capture(cid)
                    
            except Exception as e:
                print(f"[VideoInference] Daemon 同步异常: {e}")

    def load_model(self):
        if self.model is None:
            full_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                self.model_path
            )
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"找不到模型路径: {full_path}")
            
            self.model_type = 'pytorch'
            if os.path.isdir(full_path) or 'openvino' in full_path.lower():
                self.model_type = 'openvino'
            elif full_path.lower().endswith('.onnx'):
                self.model_type = 'onnx'
            
            print(f"[VideoInference] 正在初始化 {self.model_type.upper()} 推理引擎: {full_path}")
            
            try:
                if self.model_type in ['openvino', 'onnx']:
                    self.model = YOLO(full_path, task='detect')
                else:
                    self.model = YOLO(full_path)
                    if YOLO_DEVICE != 'cpu':
                        self.model.to(YOLO_DEVICE)
                
                print(f"[VideoInference] {self.model_type.upper()} 模型就绪，运行设备: {YOLO_DEVICE}")
            except Exception as e:
                print(f"[VideoInference] 模型加载失败: {e}")
                raise e

    def get_or_create_capture(self, camera_id, stream_url):
        with self.lock:
            if camera_id not in self.captures:
                # 初始化三级流水线队列 (从 config 读取深度)
                self.captures[camera_id] = {
                    'url': stream_url,
                    'raw_queue': Queue(maxsize=int(YOLO_QUEUE_SIZE)),
                    'latest_jpeg': None,  # 缓存压缩后的 JPEG 数据，实现单次编码多路分发
                    'last_vlm_time': 0,   # 记录上次发送给 VLM 的时间戳
                    'vlm_result': None,   # 记录 VLM 返回的行为分析结果
                    'vlm_frame_counter': 0, # VLM 抽帧计数器
                    'last_vlm_frame': None, # 缓存上次触发 VLM 的帧，用于时序对比
                    'last_gray_frame': None, # 缓存上一帧灰度图，用于运动检测
                    'last_annotated_frame': None, # 缓存上一帧标注结果，用于运动检测跳过时复用
                    'lock': threading.Lock(),
                    'stop_event': threading.Event(),
                    'threads': []
                }
                
                # 启动三级并行线程
                c_data = self.captures[camera_id]
                
                # 1. 拉流线程
                t_cap = threading.Thread(target=self._thread_capture, args=(camera_id,), daemon=True)
                # 2. 推理线程
                t_inf = threading.Thread(target=self._thread_inference, args=(camera_id,), daemon=True)
                
                c_data['threads'] = [t_cap, t_inf]
                for t in c_data['threads']: t.start()
                
            elif self.captures[camera_id]['url'] != stream_url:
                self.stop_capture(camera_id)
                return self.get_or_create_capture(camera_id, stream_url)
            
            return self.captures[camera_id]

    def _thread_capture(self, camera_id):
        """第一级：原始流抓取线程 (Producer)"""
        c_data = self.captures[camera_id]
        url = c_data['url']
        print(f"[Capture] 启动拉流线程: {camera_id}, 源: {url}")
        
        is_usb = url.startswith('/dev/video')
        
        if is_usb:
            device_index = int(url.split('/')[-1].replace('video', ''))
            cap = cv2.VideoCapture(device_index)
        else:
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(YOLO_IMG_SIZE))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(YOLO_IMG_SIZE * 0.75))
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        while not c_data['stop_event'].is_set():
            ret, frame = cap.read()
            if not ret:
                if not is_usb and not cap.isOpened():
                    print(f"[Capture] 尝试重连: {url}")
                    cap.release()
                    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(YOLO_IMG_SIZE))
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(YOLO_IMG_SIZE * 0.75))
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                time.sleep(0.1)
                continue
            
            try:
                while c_data['raw_queue'].full():
                    c_data['raw_queue'].get_nowait()
                c_data['raw_queue'].put_nowait(frame)
            except:
                pass
        
        cap.release()
        print(f"[Capture] 停止拉流线程: {camera_id}")

    def _thread_inference(self, camera_id):
        """第二级：YOLO 推理线程 (Consumer)"""
        c_data = self.captures[camera_id]
        print(f"[Inference] 启动推理线程: {camera_id}")
        
        if self.model is None: self.load_model()
        
        last_full_scan = time.time()
        last_person_seen = 0.0
        
        while not c_data['stop_event'].is_set():
            try:
                frame = c_data['raw_queue'].get(timeout=1.0)
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)
                
                prev_gray = c_data.get('last_gray_frame')
                c_data['last_gray_frame'] = gray
                
                time_since_person = time.time() - last_person_seen
                in_person_window = time_since_person < float(PERSON_TIMEOUT)
                
                should_skip = False
                if prev_gray is not None and not in_person_window:
                    diff = cv2.absdiff(prev_gray, gray)
                    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                    motion_ratio = cv2.countNonZero(thresh) / (frame.shape[0] * frame.shape[1])
                    
                    time_since_scan = time.time() - last_full_scan
                    if motion_ratio < float(MOTION_THRESHOLD) and time_since_scan < float(FULL_SCAN_INTERVAL):
                        should_skip = True
                
                if should_skip:
                    last_annotated = c_data.get('last_annotated_frame')
                    if last_annotated is not None:
                        ret, jpeg = cv2.imencode('.jpg', last_annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                        if ret:
                            with c_data['lock']:
                                c_data['latest_jpeg'] = jpeg.tobytes()
                        continue
                
                last_full_scan = time.time()
                
                # 核心优化 2：对齐 predict.py 的轻量级调用
                # 根据模型类型动态调整参数
                infer_args = {
                    'source': frame,
                    'conf': float(YOLO_CONF_THRESHOLD),
                    'iou': float(YOLO_IOU_THRESHOLD),
                    'classes': [0], # 仅识别 0 号类别 (通常是 person 人)
                    'verbose': False
                }
                
                # 如果是 PyTorch 模型，允许显式指定 device
                if self.model_type == 'pytorch':
                    infer_args['device'] = YOLO_DEVICE
                
                results = self.model.predict(**infer_args)
                
                if len(results[0].boxes) > 0:
                    last_person_seen = time.time()
                
                annotated_frame = results[0].plot()
                
                # ==========================================
                # VLM 多模态大模型异步联动分析逻辑
                # ==========================================
                if VLM_ENABLED and len(results[0].boxes) > 0:
                    current_time = time.time()
                    with c_data['lock']:
                        c_data['vlm_frame_counter'] += 1
                        frame_count = c_data['vlm_frame_counter']
                        last_vlm_time = c_data.get('last_vlm_time', 0)
                        
                    # 只有达到抽帧间隔且超过冷却时间才触发
                    if frame_count >= int(VLM_FRAME_SKIP) and (current_time - last_vlm_time > float(VLM_ANALYZE_INTERVAL)):
                        with c_data['lock']:
                            c_data['last_vlm_time'] = current_time
                            c_data['vlm_frame_counter'] = 0  # 触发后重置计数器
                        
                        # 开启一个独立的守护线程进行请求，绝不阻塞当前的视频流推理
                        prev_frame = c_data.get('last_vlm_frame')
                        c_data['last_vlm_frame'] = frame.copy()
                        
                        self.vlm_executor.submit(
                            self._run_vlm_analysis,
                            camera_id, prev_frame, frame.copy()
                        )
                
                ret, jpeg = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    with c_data['lock']:
                        c_data['latest_jpeg'] = jpeg.tobytes()
                        c_data['last_annotated_frame'] = annotated_frame
                    
            except Empty:
                continue
            except Exception as e:
                print(f"[Inference] 推理运行报错: {e}")
        
        print(f"[Inference] 停止推理线程: {camera_id}")


    def get_frame(self, camera_id):
        """供接口调用的输出端 (Output)，只做读取，无繁重计算"""
        with self.lock:
            c_data = self.captures.get(camera_id)
            
        if not c_data: return None
        
        with c_data['lock']:
            return c_data['latest_jpeg']
    
    def stop_capture(self, camera_id):
        with self.lock:
            c_data = self.captures.pop(camera_id, None)
            
        if c_data:
            c_data['stop_event'].set()

    def stop_all(self):
        with self.lock:
            for camera_id in list(self.captures.keys()):
                self.stop_capture(camera_id)
        self.vlm_executor.shutdown(wait=False)

    def _run_vlm_analysis(self, camera_id, prev_frame, curr_frame):
        """专门负责与 Ollama / OpenAI API 交互的后台大模型推理子线程"""
        try:
            ret, buffer = cv2.imencode('.jpg', curr_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret: return
            
            b64_curr = base64.b64encode(buffer).decode('utf-8')
            
            b64_prev = None
            if prev_frame is not None:
                ret2, buffer2 = cv2.imencode('.jpg', prev_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret2:
                    b64_prev = base64.b64encode(buffer2).decode('utf-8')
            
            payload = {}
            if VLM_BACKEND.lower() == 'ollama':
                images = [b64_prev, b64_curr] if b64_prev else [b64_curr]
                payload = {
                    "model": VLM_MODEL_NAME,
                    "messages": [
                        {
                            "role": "user",
                            "content": VLM_PROMPT,
                            "images": images
                        }
                    ],
                    "stream": False,
                    "format": "json"
                }
                headers = {'Content-Type': 'application/json'}
            elif VLM_BACKEND.lower() == 'openai':
                content_parts = [{"type": "text", "text": VLM_PROMPT}]
                if b64_prev:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_prev}", "detail": "low"}
                    })
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_curr}", "detail": "low"}
                })
                payload = {
                    "model": VLM_MODEL_NAME,
                    "messages": [
                        {"role": "user", "content": content_parts}
                    ],
                    "response_format": { "type": "json_object" }
                }
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {VLM_API_KEY}'
                }
            else:
                print(f"[VLM] 未知的 VLM 后端: {VLM_BACKEND}")
                return

            print(f"[VLM] 正在向 {VLM_BACKEND} 引擎发送行为分析请求...")
            start_time = time.time()
            
            # 使用较长超时时间（大模型处理图片通常需要 2-10 秒）
            response = requests.post(VLM_API_BASE, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                resp_json = response.json()
                content = ""
                
                # 兼容 Ollama 和 OpenAI 的返回结构
                if VLM_BACKEND.lower() == 'ollama':
                    content = resp_json.get('message', {}).get('content', '{}')
                else:
                    content = resp_json['choices'][0]['message']['content']
                
                # 尝试解析大模型返回的严格 JSON
                try:
                    result_dict = json.loads(content)
                    print(f"[VLM] 分析完成 (耗时: {time.time() - start_time:.1f}s), 结果: {result_dict}")
                    
                    with self.lock:
                        c_data = self.captures.get(camera_id)
                        if c_data:
                            with c_data['lock']:
                                c_data['vlm_result'] = result_dict
                    if result_dict.get('is_violent', False):
                        self._handle_violent_capture(camera_id, curr_frame, result_dict)
                        
                except json.JSONDecodeError:
                    print(f"[VLM] 解析大模型返回的 JSON 失败, 原文: {content}")
            else:
                print(f"[VLM] 请求失败，状态码: {response.status_code}, {response.text}")
                
        except Exception as e:
            print(f"[VLM] 大模型请求异常: {e}")

    def _handle_violent_capture(self, camera_id, frame, vlm_result):
        """当 VLM 检测到暴力行为时，自动抓拍图片、保存数据库、并推送 SocketIO 警报"""
        try:
            import os
            import uuid
            from datetime import datetime
            
            upload_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'static', 'captures'
            )
            os.makedirs(upload_path, exist_ok=True)
            
            filename = f"violent_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(upload_path, filename)
            cv2.imwrite(filepath, frame)
            
            location = '未知位置'
            try:
                all_cameras = _load_cameras_config()
                for cam in all_cameras:
                    if str(cam.get('id', '')) == str(camera_id):
                        location = cam.get('location', '未知位置')
                        break
            except:
                pass
            
            threat_level = vlm_result.get('threat_level', 'low')
            behavior_type = vlm_result.get('behavior_type', 'normal')
            num_people = vlm_result.get('num_people_involved', 0)
            evidence = vlm_result.get('evidence', '')
            description = vlm_result.get('description', '')
            
            try:
                from blueprints.models import Capture
                from blueprints import db
                
                if not self.app:
                    print("[VLM 抓拍] 警告: Flask 应用实例未注入，跳过数据库写入")
                else:
                    with self.app.app_context():
                        capture = Capture(
                            camera_id=camera_id,
                            location=location,
                            image_path=f"captures/{filename}",
                            thumbnail_path=f"captures/{filename}",
                            violation_type=f"{behavior_type}({threat_level})",
                            threat_level=threat_level,
                            num_people_involved=num_people,
                            evidence=evidence,
                            capture_time=datetime.now()
                        )
                        db.session.add(capture)
                        db.session.commit()
                        print(f"[VLM 抓拍] 图片已保存: {filename}, 违规类型: {behavior_type}, 威胁等级: {threat_level}")
            except Exception as e:
                print(f"[VLM 抓拍] 数据库写入失败: {e}")
                try:
                    db.session.rollback()
                except:
                    pass
            
            try:
                from exts import socketio
                socketio.emit('violent_alert', {
                    'camera_id': camera_id,
                    'location': location,
                    'threat_level': threat_level,
                    'behavior_type': behavior_type,
                    'num_people_involved': num_people,
                    'description': description,
                    'evidence': evidence,
                    'image_path': f"/static/captures/{filename}",
                    'capture_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }, namespace='/')
                print(f"[VLM 警报] 已推送暴力行为告警: 摄像头 {camera_id} @ {location} [{threat_level}]")
            except Exception as e:
                print(f"[VLM 警报] SocketIO 推送失败: {e}")
                
        except Exception as e:
            print(f"[VLM 抓拍] 自动抓拍处理异常: {e}")


video_inference = VideoInference()

