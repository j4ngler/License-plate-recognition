import datetime, os, logging, queue
import function.helper as helper
import function.utils_rotate as utils_rotate
from .utils import save_image, ensure_dir
from .config import IMG_DIR
import torch, re, cv2, time
from .mqtt_client import publish_plate
from function.helper import read_plate, classify_vehicle
from collections import defaultdict
from .db import save_plate

log = logging.getLogger("detector")

# Load models 1 lần
yolo_LP_detect = torch.hub.load('yolov5', 'custom', path='model/LP_detector_nano_61.pt', source='local')
yolo_LP_detect.conf = 0.4
yolo_license_plate = torch.hub.load('yolov5', 'custom', path='model/LP_ocr_nano_62.pt', source='local')
yolo_license_plate.conf = 0.5

PLATE_PATTERN = re.compile(
    r'^('
    r'\d{2}[A-Z]{1,2}-?\d{4,5}'  # xe máy: 1–2 chữ cái, 4 hoặc 5 chữ số
    r'|'
    r'\d{2}[A-Z]-?\d{5}'         # ô tô: 1 chữ cái, 5 chữ số
    r')$'
)

def detect_worker(stop_event, frame_queue, ocr_queue):
    """Worker detect biển số, crop và đẩy vào ocr_queue"""
    while not stop_event.is_set():
        try:
            frame = frame_queue.get(timeout=1)
        except:
            continue

        try:
            det = yolo_LP_detect(frame, size=640)
            list_plates = det.pandas().xyxy[0].values.tolist()
        except Exception as e:
            log.error(f"[DETECT] Lỗi detect: {e}")
            continue

        for plate in list_plates:
            x1, y1, x2, y2 = map(int, plate[:4])
            crop_img = frame[y1:y2, x1:x2]
            if crop_img.size > 0:
                try:
                    ocr_queue.put((crop_img.copy(), (x1, y1, x2, y2)), timeout=1)
                except queue.Full:
                    pass

            # Vẽ khung detect để debug (nếu cần)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

        # Show preview
        cv2.imshow("Detect", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            stop_event.set()
            break

        frame_queue.task_done()

def process_plate(crop_img):
    """OCR biển số với cả deskew"""
    lp = read_plate(yolo_license_plate, crop_img)
    if lp == "unknown":
        # Thử deskew nếu chưa đọc được
        for cc in range(2):
            for ct in range(2):
                rotated = utils_rotate.deskew(crop_img, cc, ct)
                lp = helper.read_plate(yolo_license_plate, rotated)
                if lp != "unknown":
                    return lp

    return lp

def save_and_publish(lp, bbox, crop_img):
    """Lưu ảnh và gửi MQTT"""
    ts = datetime.datetime.now()
    vehicle_type = helper.classify_vehicle(lp, bbox)

    # Lưu ảnh
    day_dir = os.path.join(IMG_DIR, ts.strftime("%Y-%m-%d"))
    ensure_dir(day_dir)
    img_path = save_image(crop_img, day_dir, f"{ts.strftime('%H%M%S')}_{lp}.jpg")
    log.info(f"[{ts}] OCR: {lp} -> saved {img_path}")

    # Lưu db
    save_plate(lp, img_path, ts, vehicle_type)

    # Gửi MQTT
    publish_plate(lp, ts.isoformat(), vehicle_type)
    log.info(f"[MQTT] Sent: {lp} ({vehicle_type})")



def ocr_worker(stop_event, ocr_queue):
    """Worker OCR biển số (chỉ lưu 1 ảnh mới nhất khi cùng biển số)"""
    last_plate = None
    same_count = 0
    last_sent_time = None
    MAX_COUNT = 3  # detect tối đa 3 ảnh liên tiếp trước khi lưu
    MIN_INTERVAL = 10  # giây tối thiểu giữa 2 lần gửi cùng biển

    while not stop_event.is_set():
        try:
            crop_img, bbox = ocr_queue.get(timeout=1)
        except queue.Empty:
            continue

        lp = process_plate(crop_img)

        if lp != "unknown":
            now = datetime.datetime.now()

            # Nếu là biển số mới → reset counter
            if lp != last_plate:
                last_plate = lp
                same_count = 1
            else:
                same_count += 1

            if same_count >= MAX_COUNT:
                # Chống gửi liên tục cùng biển
                if last_sent_time is None or (now - last_sent_time).total_seconds() > MIN_INTERVAL:
                    save_and_publish(lp, bbox, crop_img)
                    last_sent_time = now

                same_count = 0  # reset đếm
        
        ocr_queue.task_done()
