SECRET_KEY='asdmmnkdnlamdl;awwd'

# 数据库基本信息
HOSTNAME='127.0.0.1'
PORT=3306
USERNAME='root'
PASSWORD='heweijie'
DATABASE = 'home'
DB_URI = 'mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8'.format(USERNAME,PASSWORD,HOSTNAME,PORT,DATABASE)
SQLALCHEMY_DATABASE_URI = DB_URI

# 邮箱配置
# qvqnpnqkirdldgbb
MAIL_SERVER='smtp.qq.com'
MAIL_USE_SSL=True
MAIL_PORT=465
MAIL_USERNAME='3189801930@qq.com'
MAIL_PASSWORD='efcupjqhgltfddaj'
MAIL_DEFAULT_SENDER='3189801930@qq.com'



# YOLO 推理配置
YOLO_MODEL_PATH = 'model/yolo26n_openvino_model'
YOLO_CONF_THRESHOLD = 0.25
YOLO_IOU_THRESHOLD = 0.45
YOLO_DEVICE = 'cpu'
YOLO_IMG_SIZE = 640
YOLO_QUEUE_SIZE = 1  # 推理队列深度，1为极致实时，增加可提高流畅度但会增加延迟
MOTION_THRESHOLD = 0.05  # 运动检测阈值：帧差变化像素占比低于此值时跳过YOLO推理（0.03~0.15，值越小越敏感）
FULL_SCAN_INTERVAL = 1.0   # 强制心跳扫描间隔（秒）：即使画面静止，也定期运行YOLO以检测倒地等静态危险
PERSON_TIMEOUT = 3.0       # 人在持续检测窗口（秒）：检测到有人后，此时间内始终执行YOLO不跳帧，确保捕捉摔倒等静态危险

# 多模态大模型 (VLM) 暴力行为分析配置
VLM_ENABLED = False  # 默认为 False，你可以手动改为 True 开启大模型联动分析
VLM_BACKEND = 'openai'  # 可选: 'ollama' 或 'openai' (后者兼容几乎所有商用云端 API)
VLM_API_BASE = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'  # api地址
VLM_API_KEY = 'sk-41fd6c7956c1414ba4c1662cb07ad846'  # OpenAI 等云端大模型需要的 API Key，Ollama 本地部署可留空
VLM_MODEL_NAME = 'qwen2.5-vl-72b-instruct'
# VLM_MODEL_NAME = 'llama3.2-vision:11b'  # 模型名称，如 ollama 的 'llava', 'qwen2-vl'，或 openai 的 'gpt-4o'
VLM_FRAME_SKIP = 30  # 抽帧间隔：每处理多少帧才评估一次是否交给大模型(约等于1-2秒)，过滤闪现残影
VLM_ANALYZE_INTERVAL = 3.0  # 分析冷却时间(秒)。为防止API被请求淹没，只有画面中检测到人且超过冷却时间才分析一次
VLM_PROMPT = """你是一个专业的家庭安防监控行为分析专家。我会按时间顺序给你两张连续帧图像（第一张是之前的画面，第二张是当前画面），请对比两张图片的变化，重点分析人物的动作趋势和状态演变。

【对比分析要点】
- 人物姿态变化：从站立到倒地、从正常到摔倒、从平静到激烈动作
- 位置移动：是否有人突然闯入、快速接近他人、逃离现场
- 物体交互：是否有人拿起刀具、棍棒，或物品被翻动、破坏
- 持续状态：某人是否长时间保持倒地、被束缚、痛苦姿态

【高危行为 - 必须立即报警】
- 老人跌倒倒地不起：有人倒在地上且保持不动，或呈现痛苦挣扎姿态
- 入室抢劫/持刀威胁：陌生人闯入室内，手持刀具、棍棒或其他武器威胁他人
- 暴力殴打/绑架：对他人实施严重身体暴力、捆绑或限制人身自由

【中危行为 - 需要关注】
- 老人行动异常：缓慢行走、扶墙站立、突然坐下不起、肢体不协调
- 可疑人员闯入：非家庭成员在室内徘徊、撬门、翻找贵重物品
- 火灾/烟雾迹象：明火、浓烟、电线短路火花

【正常行为 - 无需报警】
- 家庭成员正常起居：吃饭、看电视、走动、打扫卫生
- 老人正常休息：坐在沙发上、躺在床上、缓慢散步
- 宠物活动：猫狗走动不属于异常

请严格按照以下 JSON 格式返回结果，不要输出任何额外的思考过程、解释、Markdown 或 JSON 之外的内容：

{
  "is_violent": true/false,
  "threat_level": "low/medium/high",
  "behavior_type": "elderly_fall/home_invasion/weapon_threat/violence/suspicious_intrusion/fire_smoke/elderly_abnormal/normal",
  "description": "用中文对比前后两帧的变化，描述动作趋势，例如：'前一帧老人站立，后一帧已仰面倒在地上，呈摔倒过程'",
  "num_people_involved": 整数,
  "evidence": "列出支持判断的关键视觉线索，用简短中文描述"
}
"""
