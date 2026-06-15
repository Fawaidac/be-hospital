# app/services/review_bot.py
import random
import logging
import httpx
from app.core.config import settings

# Setup logging sederhana untuk mempermudah testing di terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReviewBot")


class ReviewBotService:

    @staticmethod
    def parse_rating(rating_val) -> int:
        """Mengonversi rating dari API Google (enum/string/int) ke integer 1-5."""
        if isinstance(rating_val, int):
            return rating_val
        if isinstance(rating_val, str):
            val = rating_val.upper().strip()
            # Mapping jika Google mengirimkan format Enum String
            mapping = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
            if val in mapping:
                return mapping[val]
            if val.isdigit():
                return int(val)
        try:
            return int(rating_val)
        except (ValueError, TypeError):
            return 3

    @staticmethod
    def generate_reply_template(rating) -> str:
        """Logika penentuan balasan otomatis berdasarkan bintang 1-5 dengan format formal"""
        rating_int = ReviewBotService.parse_rating(rating)

        footer = (
            "\n\nApabila membutuhkan informasi lebih lanjut atau ingin menyampaikan aspirasi, "
            "silakan menghubungi kami melalui:\n"
            "☎️ Telepon/WA: 08113503500\n"
            "📧 Email: rsd.soebandi@jemberkab.go.id\n\n"
            "Ikuti juga informasi pelayanan terbaru kami melalui:\n"
            "📸 Instagram: @rsddrsoebandi\n"
            "👥 Facebook: RSD Dokter Soebandi Jember\n"
            "🎵 TikTok: RSD dr. Soebandi\n"
            "🎥 YouTube: RSD dr. Soebandi"
        )

        templates = {
            5: [
                "Terima kasih atas apresiasi dan kepercayaan yang telah diberikan kepada RSD dr. Soebandi. "
                "Masukan positif dari Bapak/Ibu menjadi motivasi bagi kami untuk terus meningkatkan mutu pelayanan. "
                "Semoga Bapak/Ibu beserta keluarga selalu diberikan kesehatan." + footer,

                "Terima kasih atas ulasan bintang 5 dan kepercayaan Bapak/Ibu kepada RSD dr. Soebandi. "
                "Kami berkomitmen untuk selalu mempertahankan dan memberikan pelayanan medis terbaik bagi masyarakat. "
                "Semoga sehat selalu." + footer
            ],
            4: [
                "Terima kasih atas ulasan dan penilaian baik yang Bapak/Ibu berikan kepada RSD dr. Soebandi. "
                "Segala masukan akan terus kami jadikan acuan untuk berbenah demi kenyamanan pasien yang lebih baik lagi. "
                "Semoga Bapak/Ibu selalu diberikan kesehatan." + footer
            ],
            3: [
                "Terima kasih atas masukan yang Bapak/Ibu sampaikan mengenai pelayanan di RSD dr. Soebandi. "
                "Kami memohon maaf apabila terdapat aspek pelayanan atau kenyamanan yang belum maksimal selama berada di rumah sakit kami. "
                "Catatan ini akan segera kami koordinasikan secara internal untuk perbaikan ke depan." + footer
            ],
            2: [
                "Kami memohon maaf yang sebesar-besarnya atas ketidaknyamanan yang Bapak/Ibu alami selama menjalani pelayanan di RSD dr. Soebandi. "
                "Kenyamanan dan keselamatan pasien adalah prioritas kami. Agar kami dapat mengidentifikasi masalah dan melakukan tindakan korektif yang tepat, "
                "mohon kesediaan Bapak/Ibu untuk menyampaikan detail kendala tersebut melalui kontak resmi di bawah ini." + footer
            ],
            1: [
                "Kami memohon maaf yang sebesar-besarnya atas pengalaman kurang menyenangkan dan pelayanan yang mengecewakan Bapak/Ibu di RSD dr. Soebandi. "
                "Kritik serta keluhan dari Bapak/Ibu menjadi perhatian dan catatan evaluasi yang sangat serius bagi pihak manajemen. "
                "Kami sangat mengharapkan Bapak/Ibu dapat menghubungi Humas/Layanan Pengaduan kami di bawah ini agar permasalahan ini dapat segera kami selesaikan secara langsung." + footer
            ]
        }

        return random.choice(templates.get(rating_int, templates[3]))

    @staticmethod
    def get_clean_account_location_ids() -> tuple[str, str]:
        account_id = settings.GOOGLE_ACCOUNT_ID
        if not account_id.startswith("accounts/"):
            account_id = f"accounts/{account_id}"

        location_id = settings.GOOGLE_LOCATION_ID
        if not location_id.startswith("locations/"):
            location_id = f"locations/{location_id}"

        return account_id, location_id

    @staticmethod
    async def get_live_access_token() -> str:
        """Menghasilkan Access Token baru menggunakan Refresh Token"""
        url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": settings.GOOGLE_REFRESH_TOKEN,
            "grant_type": "refresh_token"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=payload)
                if response.status_code == 200:
                    return response.json().get("access_token", "")
                logger.error(f"Gagal refresh token Google: {response.text}")
                return ""
            except Exception as e:
                logger.error(f"Error koneksi saat refresh token: {str(e)}")
                return ""

    @staticmethod
    async def send_reply_to_google(review_id: str, reply_text: str) -> bool:
        """Fungsi resmi mengirim balasan ke Google Business Profile API (v1 terbaru)"""
        account_id, location_id = ReviewBotService.get_clean_account_location_ids()

        access_token = await ReviewBotService.get_live_access_token()
        if not access_token:
            return False

        # Endpoint resmi Google Business Profile API v1
        url = f"https://mybusinessmanagement.googleapis.com/v1/{account_id}/{location_id}/reviews/{review_id}:reply"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "comment": reply_text
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    logger.info(f"Berhasil membalas review ID: {review_id}")
                    return True
                logger.error(f"Gagal balas review Google: {response.text}")
                return False
            except Exception as e:
                logger.error(f"Error koneksi saat balas review: {str(e)}")
                return False

    @staticmethod
    async def fetch_and_sync_old_reviews() -> list:
        """Fungsi untuk menarik daftar seluruh review lama dari Google API (v1 terbaru)"""
        account_id, location_id = ReviewBotService.get_clean_account_location_ids()

        access_token = await ReviewBotService.get_live_access_token()
        if not access_token:
            return []

        # Endpoint resmi Google Business Profile API v1 untuk list reviews
        url = f"https://mybusinessmanagement.googleapis.com/v1/{account_id}/{location_id}/reviews"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("reviews", [])
                logger.error(f"Gagal mengambil data review: {response.text}")
                return []
            except Exception as e:
                logger.error(f"Error koneksi saat ambil review: {str(e)}")
                return []
