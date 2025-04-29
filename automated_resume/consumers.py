import json
import asyncio
import base64
import cv2
import torch
import numpy as np
from datetime import datetime
from PIL import Image
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from ultralytics import YOLO
from .coco_classes import class_names
from .models import AdminSetting

def get_admin_settings():
    return AdminSetting.objects.first() or AdminSetting()

# Get admin settings object to dynamically load admin settings
admin_settings_object = get_admin_settings()

class ProctoringConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for proctoring tasks. Handles WebSocket messages and performs proctoring tasks.
    It also manages video recording and sends the processed frames to the client.
    Each frame is processed using YOLOv11n model and the result is sent to the client.
    After each frame is processed, if there are any violations, it sends a notification to the client.
    """
    async def connect(self):
        """Handle WebSocket connection"""
        await self.accept()
        await self.send(text_data=json.dumps({'message': 'Proctoring started'}))

        # Initialize attributes
        self.flags = 0
        self.violation_count = 0
        self.VIOLATION_THRESHOLD = admin_settings_object.NUMBER_OF_VIOLATIONS  # Maximum violations before quiz termination
        self.running = True
        self.model = YOLO("yolo11n.pt")
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        self.model.to(self.device)
        
        # Output Video Setup
        self.frame_queue = asyncio.Queue()  # Queue to store frames for recording
        self.recording_active = True  # Control flag for video recording
        self.video_writer = None  # OpenCV video writer
        self.frame_width = 640  # Assuming 640x480 frames
        self.frame_height = 480
        self.fps = 12  # Frames per second

        # Start the recording process in the background
        # asyncio.create_task(self.record_video_task())

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        self.running = False
        self.recording_active = False  # Stop recording task
        await self.frame_queue.put(None)  # Signal the task to exit
        if self.video_writer:
            self.video_writer.release()  # Ensure video file is closed properly
        await self.send(text_data=json.dumps({
            "message": "Proctoring stopped",
        }))
        raise StopConsumer()
        
    async def receive(self, text_data):
        """Receive frames from frontend and analyze them"""
        data = json.loads(text_data)
        if data.get("action") == "resume":
            self.violation_count = 0  # Reset violation count
            self.running = True
            await self.send(json.dumps({"message": "Detections Resumed"}))
            return # Exit to avoid further processing issues

        try:
            # Process Audio
            if "audio" in data:
                print("Audio data received")
                audio_data = base64.b64decode(data["audio"])
                with open("recorded_audio.webm", "wb") as f:
                    f.write(audio_data)
            # Process Video Frames
            if "frame" in data and self.running:
                frame_data = data["frame"].split(",")[1]  # Extract base64 data
                frame = self.decode_image(frame_data)

                # Run AI proctoring on the frame
                await self.run_proctoring(frame)
        except Exception as e:
            print("Error processing frame or proctoring Paused:", str(e))
            # if data.get("action") == "stop":
            #     self.running = False
            #     await self.send(text_data=json.dumps({"message": "Proctoring stopped"}))
            #     await self.disconnect(close_code=1000)

    @staticmethod
    def decode_image(frame_base64):
        """Convert base64 image to OpenCV format"""
        img_data = base64.b64decode(frame_base64)
        np_arr = np.frombuffer(img_data, np.uint8)
        # Ensure correct color format
        img = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)  # Read as is
        if img.shape[-1] == 4:  # Check if image has an alpha channel (RGBA)
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)  # Convert RGBA to RGB
        
        return img

    async def trigger_quiz_submission(self):
        """Trigger quiz submission when cheating is detected"""
        await self.send(text_data=json.dumps({"message": "Cheating detected! Submitting the quiz..."}))
        # await self.send(text_data=json.dumps({"message": f"Number of flags:{self.flags}"}))
        self.running = False
        await self.disconnect(close_code=1001)

    async def run_proctoring(self, frame):
        """Run AI proctoring on the received frame"""
        phone_class_id = class_names.index("cell phone")
        person_class_id = class_names.index("person")
        
        results = self.model.predict(frame, imgsz=640)
        detections = results[0].boxes.xyxy.cpu().numpy()
        confidences = results[0].boxes.conf.cpu().numpy()
        classes = results[0].boxes.cls.cpu().numpy()

        people_count = 0
        phone_detected = False

        for i, det in enumerate(detections):
            cls = int(classes[i])
            conf = confidences[i]
            if cls == person_class_id and conf >= 0.50:
                people_count += 1
            elif cls == phone_class_id and conf >= 0.50:
                phone_detected = True

        if people_count == 0:
            self.violation_count += 1
        if people_count > 1:
            self.violation_count += 1
        if phone_detected:
            self.violation_count += 1

        if self.violation_count >= self.VIOLATION_THRESHOLD and self.flags < 2:
            self.flags += 1
            await self.send(text_data=json.dumps({"message": "Violation Threshold crossed"}))
            self.running = False
        elif self.flags >= 2:
            
            await self.trigger_quiz_submission()
        
        # Add frame to queue for recording
        if self.recording_active:
            await self.frame_queue.put(frame)
    
    async def record_video_task(self):
        """Asynchronously write frames to a video file without blocking detection"""
        video_filename = f"proctoring_record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # Codec for MP4 format
        self.video_writer = cv2.VideoWriter(video_filename, fourcc, self.fps, (self.frame_width, self.frame_height))

        while self.recording_active:
            frame = await self.frame_queue.get()  # Get frame from queue
            if frame is None:
                break  # Stop when receiving None
            
            if frame.shape[:2] != (self.frame_height, self.frame_width):
                frame = cv2.resize(frame, (self.frame_width, self.frame_height))
            self.video_writer.write(frame)

        self.video_writer.release()
