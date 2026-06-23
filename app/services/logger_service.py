import os
import json
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# =====================================================================
# CONFIGURATION & INITIALIZATION (Hanya dieksekusi 1x saat aplikasi start)
# =====================================================================
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE_PATH = os.path.join(LOG_DIR, "activity_logs.txt")

# Setup Rotating File Handler:
# - maxBytes = 5 MB (5 * 1024 * 1024). File tidak akan pernah lebih dari 5MB.
# - backupCount = 3. Menyimpan maksimal 3 file cadangan lama (activity_logs.txt.1, dst).
file_handler = RotatingFileHandler(
    LOG_FILE_PATH, 
    maxBytes=5 * 1024 * 1024, 
    backupCount=3, 
    encoding="utf-8"
)

# Buat instance logger khusus aktivitas
activity_logger = logging.getLogger("CustomActivityLogger")
activity_logger.setLevel(logging.INFO)
activity_logger.addHandler(file_handler)


# =====================================================================
# CLASS LOGGER (Siap dipanggil di Router/Service FastAPI)
# =====================================================================
class ActivityLogger:
    @staticmethod
    def log(action: str = "", description: str = "", username: str = "System/Bot"):
        """
        Mencatat aktivitas ke file text dengan format JSON Lines.
        Sangat efisien karena rotasi file dikelola otomatis oleh RotatingFileHandler.
        """
        try:
            now = datetime.now()
            # ID unik berbasis microsecond timestamp (efisien & urut)
            log_id = int(time.time() * 1000000) 
            
            log_entry = {
                "id": log_id,
                "username": username,
                "action": action,
                "description": description,
                "created_at": now.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # json.dumps mengubah dict jadi 1 baris string JSON (JSON Lines format)
            # activity_logger otomatis menangani penulisan baris baru (\n)
            activity_logger.info(json.dumps(log_entry))
            
        except Exception as e:
            # Di production, sebaiknya cetak ke standar error console server
            print(f"❌ Gagal mencatat activity log: {str(e)}")