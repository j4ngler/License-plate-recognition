from PIL import Image
import cv2
import torch
import time
import threading
import queue
import function.utils_rotate as utils_rotate
import function.helper as helper
import logging

stop_event = threading.Event()

# ==== LOGGING CONFIGURATION ====
logging.basicConfig(
    filename='detections.log',
    filemode='a',
    format='[%(asctime)s] %(message)s',
    level=logging.INFO
)

# ==== LOAD YOLO MODELS ====
yolo_LP_detect = torch.hub.load('yolov5', 'custom', path='model/LP_detector_nano_61.pt', force_reload=True, source='local')
yolo_license_plate = torch.hub.load('yolov5', 'custom', path='model/LP_ocr_nano_62.pt', force_reload=True, source='local')
yolo_license_plate.conf = 0.40

# ==== QUEUES ====
frame_queue = queue.Queue(maxsize=100)
# plate_queue = queue.Queue()
# ocr_results = []
queue_full_logged = False

# ==== THREAD 1: Capture frames from RTSP ====
def capture_worker(rtsp_url):
    error_count = 0
    max_errors = 30
    vid = cv2.VideoCapture(rtsp_url)

    while not stop_event.is_set():
        ret, frame = vid.read()
        if not ret or frame is None:
            error_count += 1
            print(f"[WARNING] Can't read frame ({error_count}/{max_errors})")
            if error_count >= max_errors:
                print("[ERROR] Camera error threshold reached. Reinitializing...")
                vid.release()
                time.sleep(0.01)
                vid = cv2.VideoCapture(rtsp_url)
                error_count = 0
            continue

        error_count = 0
        frame = cv2.resize(frame, (1600, 800))
        if frame_queue.full():
            # Bỏ frame cũ nhất để giữ frame mới
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                pass
        
        frame_queue.put(frame)
# ==== THREAD 2: Detect license plates and display ====
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
            x = int(plate[0])
            y = int(plate[1])
            x2 = int(plate[2])
            y2 = int(plate[3])
            conf = float(plate[4])
            label = plate[6] if len(plate) > 6 else "plate"
            
            # Draw rectangle
            cv2.rectangle(frame, (x, y), (x2, y2), color=(0, 0, 255), thickness=2)
            cv2.putText(frame, f'{label} {conf:.2f}', (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (36, 255, 12), 2)

            # Log detection
            logging.info(f'Detected: {label} | Confidence: {conf:.2f} | Box: ({x}, {y}), ({x2}, {y2})')

            # ==== COMMENTED: Send crop to OCR queue ====
            # crop_img = frame[y:y2, x:x2]
            # plate_queue.put((crop_img.copy(), (x, y)))

        # ==== COMMENTED: Draw OCR results ====
        # for lp, (x, y) in ocr_results:
        #     cv2.putText(frame, lp, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)

        # Show FPS
        new_time = time.time()
        fps = 1 / (new_time - prev_time)
        prev_time = new_time
        cv2.putText(frame, str(int(fps)), (7, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (100, 255, 0), 3, cv2.LINE_AA)

        cv2.imshow('License Plate Detection', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# ==== THREAD 3 - OCR (COMMENTED) ====
# def ocr_worker():
#     while True:
#         item = plate_queue.get()
#         if item is None:
#             break
#         crop_img, box = item
#         x, y = box
#         lp = "unknown"
#         for cc in range(0, 2):
#             for ct in range(0, 2):
#                 lp = helper.read_plate(yolo_license_plate, utils_rotate.deskew(crop_img, cc, ct))
#                 if lp != "unknown":
#                     ocr_results.append((lp, (x, y)))
#                     break
#             if lp != "unknown":
#                 break
#         plate_queue.task_done()

# ==== START THREADS ====
rtsp_url = 'rtsp://admin:UIZCHI@192.168.100.98:554/cam/realmonitor?channel=1&subtype=0'

thread_capture = threading.Thread(target=capture_worker, args=(rtsp_url,), daemon=True)
thread_detect = threading.Thread(target=detect_worker, daemon=True)
# thread_ocr = threading.Thread(target=ocr_worker, daemon=True)

try:
    thread_capture.start()
    thread_detect.start()
    # thread_ocr.start()

    # Chờ detect thread kết thúc (vẫn có thể bị ngắt bằng Ctrl+C)
    while thread_detect.is_alive():
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n[INFO] KeyboardInterrupt received. Exiting program...")
    stop_event.set()

finally:
    # ==== CLEANUP ====
    # plate_queue.put(None)
    # thread_ocr.join()
    cv2.destroyAllWindows()
    print("[INFO] Resources released. Program terminated.")

