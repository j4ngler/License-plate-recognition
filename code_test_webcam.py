from PIL import Image
from datetime import datetime
import os
import cv2
import torch
import time
import threading
import queue
import function.utils_rotate as utils_rotate
import function.helper as helper
import logging

stop_event = threading.Event()

output_dir = "output/plates"
os.makedirs(output_dir, exist_ok=True)

# ==== LOGGING CONFIGURATION ====
log_handler = logging.FileHandler('detections.log', mode='a', encoding='utf-8')
log_formatter = logging.Formatter('[%(asctime)s] %(message)s')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

# ==== LOAD YOLO MODELS ====
yolo_LP_detect = torch.hub.load('yolov5', 'custom', path='model/LP_detector_nano_61.pt', force_reload=True, source='local')
yolo_LP_detect.conf = 0.4

yolo_license_plate = torch.hub.load('yolov5', 'custom', path='model/LP_ocr_nano_62.pt', force_reload=True, source='local')
yolo_license_plate.conf = 0.5

# ==== QUEUES ====
frame_queue = queue.Queue(maxsize=10)
plate_queue = queue.Queue(maxsize=20)
saved_plates = set()

# ==== THREAD 1: Capture frames ====
def capture_worker(device_id=1):
    error_count = 0
    max_errors = 30
    vid = cv2.VideoCapture(1)

    while not stop_event.is_set():
        ret, frame = vid.read()
        if not ret or frame is None:
            error_count += 1
            print(f"[WARNING] Can't read frame ({error_count}/{max_errors})")
            if error_count >= max_errors:
                print("[ERROR] Camera error threshold reached. Reinitializing...")
                vid.release()
                time.sleep(0.01)
                vid = cv2.VideoCapture(1)
                error_count = 0
            continue

        error_count = 0
        frame = cv2.resize(frame, (1600, 800))
        if frame_queue.full():
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                pass
        
        frame_queue.put(frame)

# ==== THREAD 2: Detect license plates ====
def detect_worker():
    prev_time = time.time()

    while not stop_event.is_set():
        try:
            frame = frame_queue.get(timeout=1)
        except queue.Empty:
            continue
        
        plates = yolo_LP_detect(frame, size=640)
        list_plates = plates.pandas().xyxy[0].values.tolist()

        for plate in list_plates:
            x, y, x2, y2 = map(int, plate[:4])
            conf = float(plate[4])

            # Crop biển số gửi sang OCR
            crop_img = frame[y:y2, x:x2]
            if crop_img.size > 0:
                plate_queue.put((crop_img.copy(), conf))

            # Vẽ khung để debug
            cv2.rectangle(frame, (x, y), (x2, y2), color=(0, 0, 255), thickness=2)
            cv2.putText(frame, f'plate {conf:.2f}', (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (36, 255, 12), 2)

        # FPS
        new_time = time.time()
        fps = 1 / (new_time - prev_time)
        prev_time = new_time
        cv2.putText(frame, str(int(fps)), (7, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 3, (100, 255, 0), 3, cv2.LINE_AA)

        cv2.imshow('License Plate Detection', frame)
        key = cv2.waitKey(1) 
        if key != -1:
            if key & 0xFF == ord('q'):
                stop_event.set()
                break

# ==== THREAD 3: OCR + Save ảnh ====
def ocr_worker():
    while not stop_event.is_set():
        try:
            crop_img, conf = plate_queue.get(timeout=1)
        except queue.Empty:
            continue

        plate_text = "unknown"
        for cc in range(2):
            for ct in range(2):
                lp = helper.read_plate(yolo_license_plate, utils_rotate.deskew(crop_img, cc, ct))
                if lp != "unknown":
                    plate_text = lp
                    break
            if plate_text != "unknown":
                break

        if plate_text != "unknown":
            # Nếu biển số đã tồn tại → bỏ qua, chỉ log
            if plate_text in saved_plates:
                logger.info(f"[SKIP] Plate {plate_text} đã tồn tại.")
            else:
                # Delay để lấy thêm ảnh cho đẹp hơn
                logger.info(f"[INFO] Plate {plate_text} mới → delay 0.5s để lấy khung hình tốt.")
                time.sleep(0.5)

                # Nếu muốn lấy 3 ảnh liên tiếp trước khi lưu
                latest_crop = crop_img
                for _ in range(2):  # lấy thêm 2 ảnh
                    try:
                        latest_crop, _ = plate_queue.get(timeout=0.2)
                    except queue.Empty:
                        break

                # Lưu ảnh mới nhất
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = os.path.join(output_dir, f"{plate_text}_{timestamp}.jpg")
                cv2.imwrite(filename, latest_crop)

                # Đánh dấu đã lưu
                saved_plates.add(plate_text)
                logger.info(f"[SAVE] Lưu biển số {plate_text} vào {filename}")

        plate_queue.task_done()

# ==== MAIN ====
if __name__ == "__main__":
    thread_capture = threading.Thread(target=capture_worker, args=(1,), daemon=True)
    thread_detect = threading.Thread(target=detect_worker, daemon=True)
    thread_ocr = threading.Thread(target=ocr_worker, daemon=True)

    try:
        thread_capture.start()
        thread_detect.start()
        thread_ocr.start()

        while thread_detect.is_alive():
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[INFO] KeyboardInterrupt received. Stopping...")
        stop_event.set()

    finally:
        # Chờ tất cả thread kết thúc
        thread_capture.join(timeout=2)
        thread_detect.join(timeout=2)
        thread_ocr.join(timeout=2)

        cv2.destroyAllWindows()
        print("[INFO] Resources released. Program terminated.")
