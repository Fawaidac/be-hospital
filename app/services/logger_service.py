from sqlalchemy.orm import Session
from app.models.activity_log import ActivityLogModel

class ActivityLogger:
    @staticmethod
    def log(db: Session, action: str, description: str, username: str = "System/Bot"):
        """Fungsi ringkas untuk memasukkan catatan aktivitas ke database"""
        try:
            new_log = ActivityLogModel(
                username=username,
                action=action,
                description=description
            )
            db.add(new_log)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ Gagal mencatat activity log: {str(e)}")