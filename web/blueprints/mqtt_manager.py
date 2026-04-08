"""
MQTT 连接管理器
用于连接 MQTT 服务器并订阅主题
"""

import json
import threading
import time
from flask import current_app

# 全局 MQTT 管理器实例
_mqtt_manager = None
_manager_lock = threading.Lock()


class MQTTManager:
    """MQTT 客户端管理器"""
    
    def __init__(self, broker, port, username='', password='', client_id=''):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id or f'flask_mqtt_{int(time.time())}'
        
        self.client = None
        self._connected = False
        self._subscribed = False
        self.latest_home_info = None
        self.mqtt_cameras = []
        self._lock = threading.Lock()
        
    def connect(self):
        """连接 MQTT 服务器"""
        try:
            import paho.mqtt.client as mqtt
            
            self.client = mqtt.Client(client_id=self.client_id)
            
            if self.username:
                self.client.username_pw_set(self.username, self.password)
            
            # 设置回调
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            
            # 连接
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            
            return True, "连接成功"
        except Exception as e:
            return False, str(e)
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self._connected = True
            print(f"[MQTT] 已连接到 {self.broker}:{self.port}")
            # 订阅主题
            self.subscribe('home/info')
        else:
            self._connected = False
            print(f"[MQTT] 连接失败，返回码: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """消息回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            print(f"[MQTT] 收到主题 {topic} 的消息")
            
            if payload:
                try:
                    data = json.loads(payload)
                    if 'timestamp_ns' in data:
                        del data['timestamp_ns']
                    
                    with self._lock:
                        self.latest_home_info = data
                    
                    cameras_list = data.get('cameras', [])
                    if cameras_list:
                        self.mqtt_cameras = cameras_list
                        print(f"[MQTT] 更新摄像头列表，共 {len(cameras_list)} 个")
                    
                    print(f"[MQTT] 解析数据: {data}")
                except json.JSONDecodeError:
                    print(f"[MQTT] 非 JSON 格式: {payload}")
        except Exception as e:
            print(f"[MQTT] 消息处理错误: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self._connected = False
        self._subscribed = False
        print(f"[MQTT] 已断开连接 (rc={rc})")
    
    def subscribe(self, topic):
        """订阅主题"""
        if self.client and self._connected:
            import paho.mqtt.client as mqtt
            result = self.client.subscribe(topic)
            if result[0] == 0:
                self._subscribed = True
                print(f"[MQTT] 已订阅主题: {topic}")
                return True
        return False
    
    def unsubscribe(self, topic):
        """取消订阅"""
        if self.client and self._connected:
            self.client.unsubscribe(topic)
            self._subscribed = False
            print(f"[MQTT] 已取消订阅: {topic}")
    
    def disconnect(self):
        """断开连接"""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except:
                pass
        self._connected = False
        self._subscribed = False
        print(f"[MQTT] 已断开连接")
    
    def is_connected(self):
        """检查是否已连接"""
        return self._connected
    
    def get_latest_info(self):
        """获取最新的 home/info 数据"""
        with self._lock:
            return self.latest_home_info
    
    def get_mqtt_cameras(self):
        """从 MQTT 获取摄像头列表"""
        with self._lock:
            return self.mqtt_cameras.copy() if self.mqtt_cameras else []


def get_mqtt_manager():
    """获取全局 MQTT 管理器实例"""
    global _mqtt_manager
    return _mqtt_manager


def init_mqtt_manager(broker, port, username='', password='', client_id=''):
    """初始化 MQTT 管理器"""
    global _mqtt_manager
    
    with _manager_lock:
        # 如果已有连接，先断开
        if _mqtt_manager:
            _mqtt_manager.disconnect()
        
        _mqtt_manager = MQTTManager(broker, port, username, password, client_id)
        return _mqtt_manager


def connect_mqtt(broker, port, username='', password='', client_id=''):
    """创建并连接 MQTT 管理器"""
    manager = init_mqtt_manager(broker, port, username, password, client_id)
    return manager.connect()


def disconnect_mqtt():
    """断开 MQTT 连接"""
    global _mqtt_manager
    with _manager_lock:
        if _mqtt_manager:
            _mqtt_manager.disconnect()
            _mqtt_manager = None


def get_mqtt_status():
    """获取 MQTT 连接状态"""
    manager = get_mqtt_manager()
    if not manager:
        return {'connected': False, 'subscribed': False, 'info': None, 'cameras': []}
    
    return {
        'connected': manager.is_connected(),
        'subscribed': manager._subscribed,
        'info': manager.get_latest_info(),
        'cameras': manager.get_mqtt_cameras()
    }


def get_cameras_from_mqtt():
    """获取 MQTT 中的摄像头列表（供 video_stream.py 使用）"""
    manager = get_mqtt_manager()
    if manager and manager.is_connected():
        return manager.get_mqtt_cameras()
    return []
