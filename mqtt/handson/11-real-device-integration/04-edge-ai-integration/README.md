# 演習4: エッジAI統合とMQTT連携

## 概要

NVIDIA JetsonのGPU能力を活用して、エッジでのAI推論とMQTT通信を組み合わせたシステムを構築します。リアルタイム画像認識、音声処理、センサーデータ分析をエッジで実行し、結果をMQTT経由でクラウドに送信します。

## 学習目標

- JetsonでのTensorRT最適化AI推論
- カメラ・音声データのリアルタイム処理
- AI推論結果のMQTT送信
- エッジ-クラウド連携アーキテクチャ
- 複数AI モデルの並列実行

## 必要機材

### ハードウェア
- NVIDIA Jetson Xavier NX/Orin Nano (Nanoでも可、ただし性能制限あり)
- CSIカメラ (Raspberry Pi Camera V2推奨) または USBカメラ
- USB マイク
- microSDカード (64GB以上推奨)
- 冷却ファン（長時間AI処理時）

### ソフトウェア環境
- JetPack SDK 5.1.2+
- TensorRT 8.5+
- OpenCV 4.8+
- PyTorch 2.0+ (JetPack版)

## 演習手順

### Step 1: AI環境セットアップ

#### 1.1 JetPack AI コンポーネント確認

```bash
# JetPack コンポーネント確認
jetson_release -v

# CUDA確認
nvcc --version
nvidia-smi  # Orin系のみ

# TensorRT確認
python3 -c "import tensorrt; print(f'TensorRT version: {tensorrt.__version__}')"

# PyTorch確認
python3 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
```

#### 1.2 AI開発環境構築

```bash
# 仮想環境作成
python3 -m venv ~/jetson_ai_env
source ~/jetson_ai_env/bin/activate

# JetPack対応パッケージインストール
pip install -r requirements.txt

# OpenCV確認（CUDA対応版）
python3 -c "import cv2; print(f'OpenCV: {cv2.__version__}, CUDA: {cv2.cuda.getCudaEnabledDeviceCount()}')"
```

### Step 2: リアルタイム画像認識システム

#### 2.1 YOLO物体検出 + MQTT

`src/yolo_mqtt_detector.py`:

```python
#!/usr/bin/env python3
import cv2
import numpy as np
import torch
import torchvision
import json
import time
import asyncio
import threading
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import paho.mqtt.client as mqtt

# JetsonでのTensorRT最適化
try:
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit
    TENSORRT_AVAILABLE = True
except ImportError:
    print("⚠ TensorRT not available, using PyTorch inference")
    TENSORRT_AVAILABLE = False

class YOLODetector:
    """YOLO物体検出器（TensorRT最適化）"""
    
    def __init__(self, model_name: str = 'yolov5s', confidence_threshold: float = 0.5):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # モデル読み込み
        self.model = self.load_model()
        self.class_names = self.model.names if hasattr(self.model, 'names') else []
        
        print(f"✓ YOLO model loaded: {model_name} on {self.device}")
    
    def load_model(self):
        """モデル読み込み"""
        try:
            # YOLOv5 Hub からモデル読み込み
            model = torch.hub.load('ultralytics/yolov5', self.model_name, pretrained=True)
            model.to(self.device)
            model.eval()
            
            # TensorRT最適化（可能な場合）
            if TENSORRT_AVAILABLE and self.device.type == 'cuda':
                model = self.optimize_tensorrt(model)
            
            return model
            
        except Exception as e:
            print(f"Model loading error: {e}")
            # フォールバック：事前訓練済みResNet
            model = torchvision.models.resnet18(pretrained=True)
            model.to(self.device)
            model.eval()
            return model
    
    def optimize_tensorrt(self, model):
        """TensorRT最適化"""
        try:
            # TorchScript変換
            model.eval()
            with torch.no_grad():
                traced_model = torch.jit.trace(model, torch.randn(1, 3, 640, 640).to(self.device))
            
            # TensorRT最適化
            from torch2trt import torch2trt
            model_trt = torch2trt(traced_model, [torch.randn(1, 3, 640, 640).to(self.device)],
                                fp16_mode=True, max_workspace_size=1<<30)
            
            print("✓ TensorRT optimization successful")
            return model_trt
            
        except Exception as e:
            print(f"TensorRT optimization failed: {e}")
            return model
    
    def detect(self, frame: np.ndarray) -> List[Dict]:
        """物体検出実行"""
        try:
            # 前処理
            input_tensor = self.preprocess_frame(frame)
            
            # 推論実行
            with torch.no_grad():
                start_time = time.time()
                results = self.model(input_tensor)
                inference_time = (time.time() - start_time) * 1000  # ms
            
            # 後処理
            detections = self.postprocess_results(results, frame.shape, inference_time)
            
            return detections
            
        except Exception as e:
            print(f"Detection error: {e}")
            return []
    
    def preprocess_frame(self, frame: np.ndarray) -> torch.Tensor:
        """フレーム前処理"""
        # YOLOv5入力サイズにリサイズ
        resized = cv2.resize(frame, (640, 640))
        
        # BGR → RGB
        rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # 正規化とテンソル変換
        tensor = torch.from_numpy(rgb_frame).permute(2, 0, 1).float() / 255.0
        tensor = tensor.unsqueeze(0).to(self.device)
        
        return tensor
    
    def postprocess_results(self, results, original_shape: Tuple, inference_time: float) -> List[Dict]:
        """結果後処理"""
        detections = []
        
        try:
            # YOLOv5結果解析
            if hasattr(results, 'xyxy'):
                predictions = results.xyxy[0].cpu().numpy()
            else:
                predictions = results[0].cpu().numpy() if isinstance(results, (list, tuple)) else results.cpu().numpy()
            
            h_orig, w_orig = original_shape[:2]
            h_input, w_input = 640, 640
            
            for pred in predictions:
                confidence = pred[4] if len(pred) > 4 else 1.0
                
                if confidence >= self.confidence_threshold:
                    # 座標をオリジナルサイズにスケール
                    x1, y1, x2, y2 = pred[:4]
                    x1 = int(x1 * w_orig / w_input)
                    y1 = int(y1 * h_orig / h_input)
                    x2 = int(x2 * w_orig / w_input)
                    y2 = int(y2 * h_orig / h_input)
                    
                    class_id = int(pred[5]) if len(pred) > 5 else 0
                    class_name = self.class_names[class_id] if class_id < len(self.class_names) else f'class_{class_id}'
                    
                    detection = {
                        'bbox': [x1, y1, x2, y2],
                        'confidence': float(confidence),
                        'class_id': class_id,
                        'class_name': class_name,
                        'area': (x2 - x1) * (y2 - y1)
                    }
                    
                    detections.append(detection)
            
            # メタデータ追加
            if detections:
                detections[0]['inference_time_ms'] = round(inference_time, 2)
                detections[0]['total_objects'] = len(detections)
            
        except Exception as e:
            print(f"Postprocessing error: {e}")
        
        return detections

class CameraCapture:
    """カメラキャプチャ管理"""
    
    def __init__(self, camera_id: int = 0, width: int = 1280, height: int = 720, fps: int = 30):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.frame_count = 0
        
    def initialize(self) -> bool:
        """カメラ初期化"""
        try:
            # CSIカメラ（Jetson）の場合
            if self.camera_id == 0:
                gstreamer_pipeline = (
                    f"nvarguscamerasrc sensor-id=0 ! "
                    f"video/x-raw(memory:NVMM), width={self.width}, height={self.height}, "
                    f"format=NV12, framerate={self.fps}/1 ! "
                    f"nvvidconv ! video/x-raw, format=BGRx ! "
                    f"videoconvert ! video/x-raw, format=BGR ! appsink"
                )
                
                self.cap = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)
            else:
                # USBカメラ
                self.cap = cv2.VideoCapture(self.camera_id)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            if not self.cap.isOpened():
                raise Exception("Failed to open camera")
            
            print(f"✓ Camera initialized: {self.width}x{self.height}@{self.fps}fps")
            return True
            
        except Exception as e:
            print(f"Camera initialization error: {e}")
            return False
    
    def read_frame(self) -> Optional[np.ndarray]:
        """フレーム読み取り"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.frame_count += 1
                return frame
        return None
    
    def release(self):
        """リソース解放"""
        if self.cap:
            self.cap.release()

class EdgeAIMQTTClient:
    """エッジAI + MQTTクライアント"""
    
    def __init__(self, broker_host: str = "localhost", device_id: str = None):
        self.broker_host = broker_host
        self.device_id = device_id or f"jetson_ai_{int(time.time())}"
        
        # コンポーネント初期化
        self.detector = YOLODetector()
        self.camera = CameraCapture()
        self.mqtt_client = mqtt.Client(client_id=self.device_id)
        
        # 統計情報
        self.stats = {
            'frames_processed': 0,
            'detections_sent': 0,
            'average_fps': 0.0,
            'average_inference_time': 0.0,
            'start_time': time.time()
        }
        
        # MQTT設定
        self.setup_mqtt()
        
    def setup_mqtt(self):
        """MQTT設定"""
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_message = self.on_message
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✓ MQTT connected: {self.device_id}")
            client.subscribe(f"ai/{self.device_id}/command", qos=1)
        else:
            print(f"✗ MQTT connection failed: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"⚠ Unexpected MQTT disconnect: {rc}")
    
    def on_message(self, client, userdata, msg):
        """コマンド受信処理"""
        try:
            command = json.loads(msg.payload.decode())
            asyncio.create_task(self.handle_command(command))
        except Exception as e:
            print(f"Command processing error: {e}")
    
    async def handle_command(self, command: Dict):
        """コマンド処理"""
        cmd_type = command.get('type')
        
        if cmd_type == 'status':
            self.publish_status()
        elif cmd_type == 'config':
            self.update_config(command.get('config', {}))
        elif cmd_type == 'capture':
            await self.capture_and_analyze()
    
    def publish_detections(self, detections: List[Dict], frame_info: Dict):
        """検出結果送信"""
        if not detections:
            return
        
        detection_data = {
            'timestamp': datetime.now().isoformat(),
            'device_id': self.device_id,
            'frame_info': frame_info,
            'detections': detections,
            'summary': {
                'object_count': len(detections),
                'classes': list(set(d['class_name'] for d in detections)),
                'avg_confidence': sum(d['confidence'] for d in detections) / len(detections)
            }
        }
        
        topic = f"ai/{self.device_id}/detections"
        self.mqtt_client.publish(topic, json.dumps(detection_data), qos=1)
        self.stats['detections_sent'] += 1
    
    def publish_status(self):
        """状態送信"""
        uptime = time.time() - self.stats['start_time']
        
        status_data = {
            'timestamp': datetime.now().isoformat(),
            'device_id': self.device_id,
            'status': 'running',
            'uptime_seconds': round(uptime, 2),
            'statistics': {
                'frames_processed': self.stats['frames_processed'],
                'detections_sent': self.stats['detections_sent'],
                'average_fps': self.stats['average_fps'],
                'average_inference_time_ms': self.stats['average_inference_time']
            },
            'hardware': {
                'gpu_available': torch.cuda.is_available(),
                'gpu_memory_mb': torch.cuda.get_device_properties(0).total_memory // 1024 // 1024 if torch.cuda.is_available() else 0,
                'tensorrt_enabled': TENSORRT_AVAILABLE
            }
        }
        
        topic = f"ai/{self.device_id}/status"
        self.mqtt_client.publish(topic, json.dumps(status_data), qos=1, retain=True)
    
    async def capture_and_analyze(self):
        """単発キャプチャ・解析"""
        frame = self.camera.read_frame()
        if frame is not None:
            detections = self.detector.detect(frame)
            
            frame_info = {
                'width': frame.shape[1],
                'height': frame.shape[0],
                'channels': frame.shape[2],
                'frame_number': self.camera.frame_count
            }
            
            self.publish_detections(detections, frame_info)
    
    async def run_continuous_detection(self):
        """連続検出ループ"""
        print("🚀 Starting Edge AI MQTT Client")
        
        # 初期化
        if not self.camera.initialize():
            print("❌ Camera initialization failed")
            return
        
        try:
            self.mqtt_client.connect(self.broker_host, 1883, 60)
            self.mqtt_client.loop_start()
            
            # FPS計算用
            fps_counter = 0
            fps_start_time = time.time()
            inference_times = []
            
            while True:
                frame = self.camera.read_frame()
                if frame is None:
                    continue
                
                # AI推論実行
                detections = self.detector.detect(frame)
                
                # フレーム情報
                frame_info = {
                    'width': frame.shape[1],
                    'height': frame.shape[0],
                    'channels': frame.shape[2],
                    'frame_number': self.camera.frame_count,
                    'timestamp': datetime.now().isoformat()
                }
                
                # 検出結果送信（検出があった場合のみ）
                if detections:
                    self.publish_detections(detections, frame_info)
                    
                    # 推論時間統計
                    if detections and 'inference_time_ms' in detections[0]:
                        inference_times.append(detections[0]['inference_time_ms'])
                        if len(inference_times) > 100:
                            inference_times.pop(0)
                
                # 統計更新
                self.stats['frames_processed'] += 1
                fps_counter += 1
                
                # FPS計算（5秒間隔）
                if time.time() - fps_start_time >= 5.0:
                    self.stats['average_fps'] = fps_counter / 5.0
                    fps_counter = 0
                    fps_start_time = time.time()
                    
                    # 推論時間平均
                    if inference_times:
                        self.stats['average_inference_time'] = sum(inference_times) / len(inference_times)
                    
                    # ステータス送信
                    self.publish_status()
                
                # フレームレート制御（オプション）
                await asyncio.sleep(0.033)  # ~30 FPS
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping Edge AI client...")
        except Exception as e:
            print(f"Runtime error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """リソースクリーンアップ"""
        self.camera.release()
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        print("✓ Edge AI client stopped")

def main():
    """メイン関数"""
    import os
    
    broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
    device_id = os.getenv('DEVICE_ID', None)
    
    client = EdgeAIMQTTClient(broker_host, device_id)
    
    try:
        asyncio.run(client.run_continuous_detection())
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    main()
```

#### 2.2 音声認識統合

`src/audio_recognition.py`:

```python
#!/usr/bin/env python3
import numpy as np
import pyaudio
import wave
import json
import time
import asyncio
import threading
from datetime import datetime
import paho.mqtt.client as mqtt

# 音声認識ライブラリ
try:
    import speech_recognition as sr
    import webrtcvad
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    print("⚠ Speech recognition not available")
    SPEECH_RECOGNITION_AVAILABLE = False

class AudioProcessor:
    """音声処理・認識"""
    
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        
        # PyAudio初期化
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # 音声認識初期化
        if SPEECH_RECOGNITION_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.vad = webrtcvad.Vad(2)  # Aggressiveness level (0-3)
        
        # 音声バッファ
        self.audio_buffer = []
        self.is_recording = False
        
        print("🎤 Audio processor initialized")
    
    def start_audio_stream(self):
        """音声ストリーム開始"""
        try:
            self.stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self.audio_callback
            )
            self.stream.start_stream()
            print("✓ Audio stream started")
            return True
            
        except Exception as e:
            print(f"Audio stream error: {e}")
            return False
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """音声コールバック"""
        if self.is_recording:
            self.audio_buffer.append(in_data)
        
        # 音声活性検出（VAD）
        if SPEECH_RECOGNITION_AVAILABLE:
            audio_frame = np.frombuffer(in_data, dtype=np.int16)
            if self.detect_speech(audio_frame):
                if not self.is_recording:
                    self.start_recording()
            else:
                if self.is_recording and len(self.audio_buffer) > 10:  # 最小録音長
                    self.stop_recording()
        
        return (in_data, pyaudio.paContinue)
    
    def detect_speech(self, audio_frame: np.ndarray) -> bool:
        """音声検出"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            return False
        
        try:
            # WebRTC VADは10ms, 20ms, 30msフレームが必要
            frame_duration_ms = len(audio_frame) * 1000 // self.sample_rate
            
            if frame_duration_ms in [10, 20, 30]:
                # 16bitサンプルを8bitに変換
                audio_bytes = audio_frame.tobytes()
                return self.vad.is_speech(audio_bytes, self.sample_rate)
        except:
            pass
        
        # フォールバック: 音量ベース検出
        rms = np.sqrt(np.mean(audio_frame**2))
        return rms > 1000  # 閾値調整が必要
    
    def start_recording(self):
        """録音開始"""
        if not self.is_recording:
            self.is_recording = True
            self.audio_buffer = []
            print("🔴 Recording started")
    
    def stop_recording(self):
        """録音終了・音声認識実行"""
        if self.is_recording:
            self.is_recording = False
            
            # 音声データを結合
            audio_data = b''.join(self.audio_buffer)
            
            # 音声認識を別スレッドで実行
            threading.Thread(target=self.process_audio, args=(audio_data,), daemon=True).start()
            
            print("⏹️ Recording stopped, processing...")
    
    def process_audio(self, audio_data: bytes):
        """音声認識処理"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            return
        
        try:
            # 音声データをAudioDataに変換
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            audio_data_sr = sr.AudioData(audio_data, self.sample_rate, 2)
            
            # Google音声認識（ネット接続必要）
            try:
                text = self.recognizer.recognize_google(audio_data_sr, language='ja-JP')
                self.on_speech_recognized(text, len(audio_data))
            except sr.UnknownValueError:
                print("🔇 Speech not recognized")
            except sr.RequestError as e:
                print(f"🌐 Speech recognition service error: {e}")
                
        except Exception as e:
            print(f"Audio processing error: {e}")
    
    def on_speech_recognized(self, text: str, audio_length: int):
        """音声認識結果処理（オーバーライド用）"""
        print(f"🗣️ Recognized: {text}")
    
    def stop_audio_stream(self):
        """音声ストリーム停止"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
        print("✓ Audio stream stopped")

class VoiceControlMQTT:
    """音声制御MQTTクライアント"""
    
    def __init__(self, broker_host: str = "localhost", device_id: str = None):
        self.broker_host = broker_host
        self.device_id = device_id or f"jetson_voice_{int(time.time())}"
        
        # 音声プロセッサー
        self.audio_processor = AudioProcessor()
        self.audio_processor.on_speech_recognized = self.on_speech_recognized
        
        # MQTT
        self.mqtt_client = mqtt.Client(client_id=self.device_id)
        self.setup_mqtt()
        
        # 音声コマンド辞書
        self.voice_commands = {
            'ライトオン': {'type': 'device_control', 'device': 'light', 'action': 'on'},
            'ライトオフ': {'type': 'device_control', 'device': 'light', 'action': 'off'},
            'エアコンオン': {'type': 'device_control', 'device': 'aircon', 'action': 'on'},
            'エアコンオフ': {'type': 'device_control', 'device': 'aircon', 'action': 'off'},
            'アラート': {'type': 'alert', 'level': 'warning', 'message': 'Voice alert triggered'},
            'ステータス': {'type': 'status_request'},
            'ヘルプ': {'type': 'help_request'}
        }
        
        print("🎙️ Voice Control MQTT initialized")
    
    def setup_mqtt(self):
        """MQTT設定"""
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✓ Voice Control MQTT connected: {self.device_id}")
        else:
            print(f"✗ MQTT connection failed: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"⚠ Unexpected MQTT disconnect: {rc}")
    
    def on_speech_recognized(self, text: str, audio_length: int):
        """音声認識結果処理"""
        print(f"🗣️ Voice input: {text}")
        
        # 音声認識結果をMQTTで送信
        voice_data = {
            'timestamp': datetime.now().isoformat(),
            'device_id': self.device_id,
            'recognized_text': text,
            'audio_length_bytes': audio_length,
            'language': 'ja-JP'
        }
        
        topic = f"voice/{self.device_id}/recognition"
        self.mqtt_client.publish(topic, json.dumps(voice_data), qos=1)
        
        # コマンド解析・実行
        command = self.parse_voice_command(text)
        if command:
            self.execute_voice_command(command)
    
    def parse_voice_command(self, text: str) -> Dict:
        """音声コマンド解析"""
        # 完全一致チェック
        for keyword, command in self.voice_commands.items():
            if keyword in text:
                return command
        
        # 部分一致チェック
        text_lower = text.lower()
        if 'ライト' in text and ('つけ' in text or 'オン' in text):
            return {'type': 'device_control', 'device': 'light', 'action': 'on'}
        elif 'ライト' in text and ('消し' in text or 'オフ' in text):
            return {'type': 'device_control', 'device': 'light', 'action': 'off'}
        
        return None
    
    def execute_voice_command(self, command: Dict):
        """音声コマンド実行"""
        print(f"🎯 Executing voice command: {command}")
        
        command_data = {
            'timestamp': datetime.now().isoformat(),
            'device_id': self.device_id,
            'source': 'voice_recognition',
            'command': command
        }
        
        # デバイス制御コマンド
        if command['type'] == 'device_control':
            topic = f"control/device/{command['device']}/command"
            control_command = {
                'action': command['action'],
                'source': self.device_id,
                'timestamp': command_data['timestamp']
            }
            self.mqtt_client.publish(topic, json.dumps(control_command), qos=1)
        
        # アラート
        elif command['type'] == 'alert':
            topic = f"alerts/{self.device_id}/voice"
            alert_data = {
                'level': command['level'],
                'message': command['message'],
                'source': 'voice_command',
                'timestamp': command_data['timestamp']
            }
            self.mqtt_client.publish(topic, json.dumps(alert_data), qos=1)
        
        # ステータス要求
        elif command['type'] == 'status_request':
            topic = "system/status/request"
            self.mqtt_client.publish(topic, json.dumps(command_data), qos=1)
        
        # 汎用コマンドログ
        topic = f"voice/{self.device_id}/commands"
        self.mqtt_client.publish(topic, json.dumps(command_data), qos=1)
    
    async def run(self):
        """メインループ"""
        print("🎤 Starting Voice Control MQTT")
        
        # MQTT接続
        try:
            self.mqtt_client.connect(self.broker_host, 1883, 60)
            self.mqtt_client.loop_start()
            
            # 音声ストリーム開始
            if self.audio_processor.start_audio_stream():
                print("👂 Listening for voice commands...")
                
                # メインループ
                while True:
                    await asyncio.sleep(1)
            else:
                print("❌ Failed to start audio stream")
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping voice control...")
        except Exception as e:
            print(f"Runtime error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """リソースクリーンアップ"""
        self.audio_processor.stop_audio_stream()
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        print("✓ Voice control stopped")

def main():
    """メイン関数"""
    import os
    
    broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
    device_id = os.getenv('DEVICE_ID', None)
    
    voice_control = VoiceControlMQTT(broker_host, device_id)
    
    try:
        asyncio.run(voice_control.run())
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    main()
```

### Step 3: 統合AI管理システム

#### 3.1 マルチモーダルAIオーケストレーター

`src/ai_orchestrator.py`:

```python
#!/usr/bin/env python3
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import threading
import queue
from dataclasses import dataclass
from enum import Enum
import paho.mqtt.client as mqtt

from yolo_mqtt_detector import EdgeAIMQTTClient
from audio_recognition import VoiceControlMQTT

class AITaskType(Enum):
    OBJECT_DETECTION = "object_detection"
    VOICE_RECOGNITION = "voice_recognition"
    SENSOR_ANALYSIS = "sensor_analysis"
    BEHAVIOR_ANALYSIS = "behavior_analysis"

@dataclass
class AITask:
    task_id: str
    task_type: AITaskType
    priority: int  # 1=highest, 5=lowest
    data: Dict[str, Any]
    timestamp: float
    callback: Optional[callable] = None

class AIOrchestrator:
    """AI処理オーケストレーター"""
    
    def __init__(self, broker_host: str = "localhost", device_id: str = None):
        self.broker_host = broker_host
        self.device_id = device_id or f"jetson_orchestrator_{int(time.time())}"
        
        # タスクキュー（優先度付き）
        self.task_queue = queue.PriorityQueue()
        self.active_tasks = {}
        self.completed_tasks = []
        
        # AIモジュール
        self.vision_client = None
        self.voice_client = None
        
        # MQTT
        self.mqtt_client = mqtt.Client(client_id=self.device_id)
        self.setup_mqtt()
        
        # 統計
        self.stats = {
            'tasks_processed': 0,
            'tasks_failed': 0,
            'average_processing_time': 0.0,
            'start_time': time.time()
        }
        
        # ワーカースレッド
        self.worker_threads = []
        self.running = False
        
        print("🧠 AI Orchestrator initialized")
    
    def setup_mqtt(self):
        """MQTT設定"""
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✓ AI Orchestrator MQTT connected: {self.device_id}")
            
            # AIタスクリクエスト購読
            client.subscribe(f"ai/{self.device_id}/task/request", qos=1)
            client.subscribe("ai/broadcast/task/request", qos=1)
            
            # 他のAIクライアントからの結果購読
            client.subscribe("ai/+/detections", qos=1)
            client.subscribe("voice/+/recognition", qos=1)
            client.subscribe("sensors/+/+/data", qos=1)
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信処理"""
        try:
            topic_parts = msg.topic.split('/')
            payload = json.loads(msg.payload.decode())
            
            if "/task/request" in msg.topic:
                self.handle_task_request(payload)
            elif "/detections" in msg.topic:
                self.handle_detection_result(payload)
            elif "/recognition" in msg.topic:
                self.handle_voice_result(payload)
            elif "/data" in msg.topic:
                self.handle_sensor_data(payload)
                
        except Exception as e:
            print(f"Message processing error: {e}")
    
    def handle_task_request(self, request: Dict):
        """AIタスクリクエスト処理"""
        task_type_str = request.get('task_type')
        priority = request.get('priority', 3)
        task_data = request.get('data', {})
        
        try:
            task_type = AITaskType(task_type_str)
            task_id = f"{task_type_str}_{int(time.time() * 1000)}"
            
            task = AITask(
                task_id=task_id,
                task_type=task_type,
                priority=priority,
                data=task_data,
                timestamp=time.time()
            )
            
            self.submit_task(task)
            
        except ValueError:
            print(f"Unknown task type: {task_type_str}")
    
    def handle_detection_result(self, result: Dict):
        """物体検出結果処理"""
        # 行動解析タスクを生成
        if result.get('detections'):
            behavior_task = AITask(
                task_id=f"behavior_{int(time.time() * 1000)}",
                task_type=AITaskType.BEHAVIOR_ANALYSIS,
                priority=2,
                data={'detection_result': result},
                timestamp=time.time()
            )
            self.submit_task(behavior_task)
    
    def handle_voice_result(self, result: Dict):
        """音声認識結果処理"""
        # 音声コマンドの意図分析
        text = result.get('recognized_text', '')
        if text:
            print(f"🎤 Processing voice: {text}")
            # より高度な自然言語処理をここに実装
    
    def handle_sensor_data(self, data: Dict):
        """センサーデータ処理"""
        # センサーデータ異常検出
        sensors = data.get('sensors', {})
        
        # 異常値検出の簡単な例
        for sensor_name, sensor_data in sensors.items():
            temp = sensor_data.get('temperature_c')
            if temp and (temp > 40 or temp < 0):  # 異常温度
                analysis_task = AITask(
                    task_id=f"sensor_analysis_{int(time.time() * 1000)}",
                    task_type=AITaskType.SENSOR_ANALYSIS,
                    priority=1,  # 高優先度
                    data={'sensor_anomaly': {'sensor': sensor_name, 'value': temp}},
                    timestamp=time.time()
                )
                self.submit_task(analysis_task)
    
    def submit_task(self, task: AITask):
        """タスク投入"""
        # 優先度付きキューに追加（数値が小さいほど高優先度）
        self.task_queue.put((task.priority, task.timestamp, task))
        print(f"📋 Task submitted: {task.task_id} (priority: {task.priority})")
    
    async def initialize_ai_modules(self):
        """AIモジュール初期化"""
        try:
            # 物体検出クライアント初期化
            self.vision_client = EdgeAIMQTTClient(self.broker_host, f"{self.device_id}_vision")
            
            # 音声認識クライアント初期化
            self.voice_client = VoiceControlMQTT(self.broker_host, f"{self.device_id}_voice")
            
            print("✓ AI modules initialized")
            
        except Exception as e:
            print(f"AI module initialization error: {e}")
    
    def start_workers(self, num_workers: int = 2):
        """ワーカースレッド開始"""
        self.running = True
        
        for i in range(num_workers):
            worker = threading.Thread(target=self.worker_loop, args=(i,), daemon=True)
            worker.start()
            self.worker_threads.append(worker)
        
        print(f"✓ Started {num_workers} worker threads")
    
    def worker_loop(self, worker_id: int):
        """ワーカーループ"""
        print(f"👷 Worker {worker_id} started")
        
        while self.running:
            try:
                # タスク取得（ブロッキング、タイムアウト付き）
                priority, timestamp, task = self.task_queue.get(timeout=1.0)
                
                # タスク実行
                start_time = time.time()
                result = self.execute_task(task)
                processing_time = time.time() - start_time
                
                # 結果処理
                self.handle_task_result(task, result, processing_time)
                
                # 統計更新
                self.update_stats(processing_time, True)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker {worker_id} error: {e}")
                self.update_stats(0, False)
    
    def execute_task(self, task: AITask) -> Dict[str, Any]:
        """タスク実行"""
        print(f"⚡ Executing task: {task.task_id} (type: {task.task_type.value})")
        
        if task.task_type == AITaskType.BEHAVIOR_ANALYSIS:
            return self.analyze_behavior(task.data)
        elif task.task_type == AITaskType.SENSOR_ANALYSIS:
            return self.analyze_sensor_anomaly(task.data)
        else:
            return {'status': 'not_implemented', 'task_type': task.task_type.value}
    
    def analyze_behavior(self, data: Dict) -> Dict[str, Any]:
        """行動解析（簡単な例）"""
        detection_result = data.get('detection_result', {})
        detections = detection_result.get('detections', [])
        
        behaviors = []
        
        # 人の検出数による分析
        person_count = sum(1 for d in detections if d.get('class_name') == 'person')
        if person_count > 5:
            behaviors.append({
                'type': 'crowding',
                'severity': 'medium',
                'description': f'Many people detected: {person_count}'
            })
        
        # 車両検出による分析
        vehicle_classes = ['car', 'truck', 'bus', 'motorcycle']
        vehicle_count = sum(1 for d in detections if d.get('class_name') in vehicle_classes)
        if vehicle_count > 3:
            behaviors.append({
                'type': 'traffic_congestion',
                'severity': 'low',
                'description': f'Multiple vehicles detected: {vehicle_count}'
            })
        
        return {
            'status': 'completed',
            'behaviors': behaviors,
            'person_count': person_count,
            'vehicle_count': vehicle_count
        }
    
    def analyze_sensor_anomaly(self, data: Dict) -> Dict[str, Any]:
        """センサー異常分析"""
        anomaly = data.get('sensor_anomaly', {})
        sensor_name = anomaly.get('sensor')
        value = anomaly.get('value')
        
        analysis_result = {
            'status': 'completed',
            'anomaly_detected': True,
            'sensor': sensor_name,
            'value': value,
            'recommendations': []
        }
        
        # 温度異常の場合
        if 'temperature' in sensor_name:
            if value > 40:
                analysis_result['severity'] = 'high'
                analysis_result['recommendations'].append('Check for fire or overheating')
                analysis_result['recommendations'].append('Activate cooling systems')
            elif value < 0:
                analysis_result['severity'] = 'medium'
                analysis_result['recommendations'].append('Check for freezing conditions')
                analysis_result['recommendations'].append('Activate heating systems')
        
        return analysis_result
    
    def handle_task_result(self, task: AITask, result: Dict, processing_time: float):
        """タスク結果処理"""
        print(f"✅ Task completed: {task.task_id} ({processing_time:.2f}s)")
        
        # 結果をMQTT送信
        result_data = {
            'timestamp': datetime.now().isoformat(),
            'device_id': self.device_id,
            'task_id': task.task_id,
            'task_type': task.task_type.value,
            'processing_time_seconds': round(processing_time, 3),
            'result': result
        }
        
        topic = f"ai/{self.device_id}/task/result"
        self.mqtt_client.publish(topic, json.dumps(result_data), qos=1)
        
        # コールバック実行
        if task.callback:
            try:
                task.callback(result)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def update_stats(self, processing_time: float, success: bool):
        """統計更新"""
        if success:
            self.stats['tasks_processed'] += 1
            # 移動平均での処理時間更新
            if self.stats['average_processing_time'] == 0:
                self.stats['average_processing_time'] = processing_time
            else:
                alpha = 0.1  # 重み
                self.stats['average_processing_time'] = (
                    alpha * processing_time + 
                    (1 - alpha) * self.stats['average_processing_time']
                )
        else:
            self.stats['tasks_failed'] += 1
    
    def publish_status(self):
        """状態送信"""
        uptime = time.time() - self.stats['start_time']
        
        status_data = {
            'timestamp': datetime.now().isoformat(),
            'device_id': self.device_id,
            'status': 'running',
            'uptime_seconds': round(uptime, 2),
            'statistics': self.stats,
            'queue_size': self.task_queue.qsize(),
            'active_workers': len(self.worker_threads)
        }
        
        topic = f"ai/{self.device_id}/orchestrator/status"
        self.mqtt_client.publish(topic, json.dumps(status_data), qos=1, retain=True)
    
    async def run(self):
        """メインループ"""
        print("🧠 Starting AI Orchestrator")
        
        # MQTT接続
        try:
            self.mqtt_client.connect(self.broker_host, 1883, 60)
            self.mqtt_client.loop_start()
            
            # AIモジュール初期化
            await self.initialize_ai_modules()
            
            # ワーカー開始
            self.start_workers(num_workers=3)
            
            # 定期ステータス送信
            last_status_time = 0
            
            while True:
                current_time = time.time()
                
                # 5分間隔でステータス送信
                if current_time - last_status_time >= 300:
                    self.publish_status()
                    last_status_time = current_time
                
                await asyncio.sleep(10)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping AI Orchestrator...")
        except Exception as e:
            print(f"Runtime error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """リソースクリーンアップ"""
        self.running = False
        
        # ワーカー停止待機
        for worker in self.worker_threads:
            worker.join(timeout=2)
        
        # MQTT切断
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        
        print("✓ AI Orchestrator stopped")

def main():
    """メイン関数"""
    import os
    
    broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
    device_id = os.getenv('DEVICE_ID', None)
    
    orchestrator = AIOrchestrator(broker_host, device_id)
    
    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    main()
```

## 課題

### 基礎課題

1. **YOLO物体検出実装**
   - カメラからリアルタイム物体検出
   - 検出結果のMQTT送信

2. **音声認識統合**
   - 日本語音声認識
   - 音声コマンドのMQTT制御

3. **パフォーマンス最適化**
   - TensorRT最適化
   - FPS向上

### 応用課題

1. **マルチモーダルAI**
   - 画像・音声・センサーデータ統合
   - 複合的な状況判断

2. **エッジ-クラウド連携**
   - エッジ前処理、クラウド詳細分析
   - 適応的負荷分散

3. **カスタムAIモデル**
   - 独自データセットでの学習
   - エッジデプロイメント

## トラブルシューティング

### GPU・CUDA関連
```bash
# CUDA確認
nvidia-smi
nvcc --version

# PyTorchのCUDA対応確認
python3 -c "import torch; print(torch.cuda.is_available())"

# TensorRT確認
python3 -c "import tensorrt; print(tensorrt.__version__)"
```

### カメラ関連
```bash
# CSIカメラ確認
ls /dev/video*

# USBカメラテスト
v4l2-ctl --list-devices
```

## 次のステップ

演習5で複数デバイスを統合したスケーラブルなIoTシステムを構築します。

---

このエッジAI統合により、Jetsonの真の能力を活用したリアルタイムAIシステムを体験できます。