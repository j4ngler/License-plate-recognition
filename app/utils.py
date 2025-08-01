import os, cv2, datetime, shutil, logging

log = logging.getLogger("utils")

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_image(img, dir_day: str, filename: str) -> str:
    ensure_dir(dir_day)
    path = os.path.join(dir_day, filename)
    cv2.imwrite(path, img)
    return path


def cleanup_old(dir_root: str, keep_days: int) -> None:
    now = datetime.datetime.now()
    for d in os.listdir(dir_root):
        full = os.path.join(dir_root, d)
        if not os.path.isdir(full):
            continue
        try:
            day = datetime.datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            continue  # thư mục không phải YYYY-MM-DD
        if (now - day).days > keep_days:
            shutil.rmtree(full, ignore_errors=True)
            log.info("Removed old dir %s", full)
