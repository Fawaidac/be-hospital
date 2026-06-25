#app/services/review_bot.py
import os
import logging
import httpx
import joblib
from datetime import datetime
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReviewBot")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "ml_models") 

try:
    tfidf = joblib.load(os.path.join(MODEL_DIR, 'vectorizer_tfidf.pkl'))
    model_svm_sentimen = joblib.load(os.path.join(MODEL_DIR, 'model_svm_sentimen.pkl'))
    model_svm_intent = joblib.load(os.path.join(MODEL_DIR, 'model_svm_intent.pkl'))
    logger.info("✅ Model SVM Lokal & TF-IDF Berhasil Dimuat di Backend FastAPI!")
except Exception as e:
    tfidf = None
    model_svm_sentimen = None
    model_svm_intent = None
    logger.error(f"❌ Gagal memuat file .pkl Model ML: {str(e)}")


class ReviewBotService:

    @staticmethod
    def parse_rating(rating_val) -> int:
        """Mengonversi rating dari API Google (enum/string/int) ke integer 1-5."""
        if isinstance(rating_val, int):
            return rating_val
        if isinstance(rating_val, str):
            val = rating_val.upper().strip()
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
    async def generate_reply_template(rating, db_session) -> str:
        """Mengambil balasan otomatis secara dinamis dari database master template"""
        from app.models.review_template import ReviewTemplateModel
        
        rating_int = ReviewBotService.parse_rating(rating)

        if rating_int in [1, 2]:
            return ""

        db_template = db_session.query(ReviewTemplateModel).filter(ReviewTemplateModel.rating == rating_int).first()

        if db_template and db_template.template_text:
            return db_template.template_text

        return "Terima kasih atas ulasan dan masukan yang Bapak/Ibu berikan kepada RSD dr. Soebandi. Semoga sehat selalu."

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
                err_msg = f"OAuth2 Error: {response.text.strip()}"
                logger.error(f"Gagal refresh token Google: {err_msg}")
                ReviewBotService.write_bot_log("ERROR", f"Gagal refresh token Google Maps API. Detail: {err_msg}")
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

    @staticmethod
    async def analyze_review_intent_and_sentiment(comment_text: str, rating_int: int = 3) -> dict:
        """
        [HYBRID CASCADE CLASSIFIER]
        Level 1: Prediksi instan via SVM Lokal (.pkl)
        Level 2: Jika SVM Ragu Total (Margin Ketidakpastian), Lempar ke Gemini AI (Hakim Garis)
        Level 3: Jika Gemini Down/Timeout, gunakan Fallback Kamus Lokal
        """
        fallback_sentiment = "NEUTRAL"
        if rating_int in [4, 5]:
            fallback_sentiment = "POSITIVE"
        elif rating_int in [1, 2]:
            fallback_sentiment = "NEGATIVE"

        fallback_keywords = []
        if comment_text:
            text_lower = comment_text.lower()
            kamus_lokal = {
                "ramah": "#friendly", "baik": "#friendly", "sopan": "#friendly", "senyum": "#friendly", 
                "telaten": "#friendly", "sabar": "#friendly", "humble": "#friendly", "care": "#friendly",
                "lama": "#slow_response", "antri": "#slow_response", "lelet": "#slow_response", 
                "lambat": "#slow_response", "ngaret": "#slow_response", "suwe": "#slow_response",
                "nunggu": "#slow_response", "berjam-jam": "#slow_response", "bersih": "#clean", 
                "wangi": "#clean", "rapi": "#clean", "resik": "#clean", "nyaman": "#cozy", 
                "adem": "#cozy", "tenang": "#cozy", "sejuk": "#cozy", "ac dingin": "#cozy",
                "cepat": "#gercep", "cepet": "#gercep", "kilat": "#gercep", "gercep": "#gercep", 
                "satset": "#gercep", "responsif": "#gercep", "sigap": "#gercep", "jutek": "#unfriendly", 
                "marah": "#unfriendly", "kasar": "#unfriendly", "bentak": "#unfriendly", "cuek": "#unfriendly", 
                "penuh": "#crowded", "sesak": "#crowded", "antrean": "#crowded", "padat": "#crowded",
                "bagus": "#aesthetic", "indah": "#aesthetic", "modern": "#aesthetic", "keren": "#aesthetic", 
                "kumuh": "#hygiene", "kotor": "#hygiene", "bau": "#hygiene", "pesing": "#hygiene",
                "bpjs lancar": "#fast_service", "online mudah": "#fast_service", "pendaftaran cepat": "#fast_service",
                "panas": "#hot_vibe", "sumuk": "#hot_vibe", "ac mati": "#hot_vibe", "gerah": "#hot_vibe",
                "ribet": "#l_vibe", "kecewa": "#l_vibe", "parah": "#l_vibe", "buruk": "#l_vibe"
            }   
            for kata_kunci, hashtag in kamus_lokal.items():
                if kata_kunci in text_lower:
                    if hashtag not in fallback_keywords:
                        fallback_keywords.append(hashtag)
                if len(fallback_keywords) >= 3:
                    break

        default_result = {
            "is_asking": False, 
            "sentiment": fallback_sentiment, 
            "keywords": fallback_keywords
        }

        if not comment_text or len(comment_text.strip()) < 3:
            return default_result

        pake_gemini_cascade = False
        local_sentiment = fallback_sentiment
        local_is_asking = False

        if tfidf and model_svm_sentimen and model_svm_intent:
            try:
                teks_vector = tfidf.transform([comment_text])
                
                prob_sentimen = model_svm_sentimen.predict_proba(teks_vector)[0]
                prob_intent = model_svm_intent.predict_proba(teks_vector)[0]
                
                prob_neg = float(prob_sentimen[0])
                prob_neu = float(prob_sentimen[1]) if len(prob_sentimen) > 2 else 0.0
                prob_pos = float(prob_sentimen[-1])
                
                prob_false = float(prob_intent[0])
                prob_true = float(prob_intent[1])

                max_prob_sentimen = float(max(prob_sentimen))

                logger.info(f"📊 [SVM Lokal Prob] Pos:{prob_pos:.2f} | Neg:{prob_neg:.2f} | True(Ask):{prob_true:.2f}")

                intent_ragu = (0.35 <= prob_true <= 0.65)
                sentimen_ragu = (max_prob_sentimen < 0.55)

                if intent_ragu or sentimen_ragu:
                    alasan_cascade = []
                    if intent_ragu:
                        alasan_cascade.append(f"Intent Ragu (True Prob: {prob_true:.2f})")
                    if sentimen_ragu:
                        alasan_cascade.append(f"Sentimen Ragu (Max Prob: {max_prob_sentimen:.2f})")
                    
                    logger.warning(f"🛑 [SVM Lokal Ragu] Mengaktifkan Cascade Level 2 -> Minta bantuan Gemini AI... Alasan: {', '.join(alasan_cascade)}")
                    pake_gemini_cascade = True
                else:
                    local_sentiment = model_svm_sentimen.predict(teks_vector)[0]
                    local_is_asking = model_svm_intent.predict(teks_vector)[0] == "True"
                    
                    logger.info(f"⚡ [SVM Lokal Pede] Sentimen: {local_sentiment} | Intent (IsAsking): {local_is_asking}")
                    
                    return {
                        "is_asking": local_is_asking,
                        "sentiment": local_sentiment,
                        "keywords": fallback_keywords
                    }

            except Exception as e:
                logger.error(f"⚠️ Kegagalan komputasi SVM Lokal: {str(e)}. Alihkan paksa ke Gemini.")
                pake_gemini_cascade = True

        if pake_gemini_cascade or not tfidf:
            if not hasattr(settings, "GEMINI_API_KEY") or not settings.GEMINI_API_KEY:
                logger.warning("⚠️ Gemini API Key kosong. Masuk ke Pertahanan Terakhir (Level 3: Fallback).")
                return default_result

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            
            prompt = (
                "Analisis teks ulasan pasien Rumah Sakit dr. Soebandi berikut.\n\n"
                f"Teks Pasien: \"{comment_text}\"\n\n"
                "Tugas Anda:\n"
                "1. Tentukan INTENT: Apakah mengandung unsur PERTANYAAN, permintaan info, atau kebingungan aktif? (Jawab TRUE atau FALSE).\n"
                "2. Tentukan SENTIMEN: POSITIVE (pujian), NEGATIVE (keluhan/sarkas), atau NEUTRAL (biasa).\n"
                "3. Ekstrak KEYWORD/HASHTAG tren (Maksimal 3, contoh #slow_response, #clean, #friendly).\n\n"
                "Aturan Respon: Anda WAJIB membalas HANYA dengan format teks string pendek tanpa alasan tambahan: "
                "INTENT=TRUE;SENTIMEN=NEGATIVE;KEYWORDS=#slow_response,#unfriendly"
            )

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.0, 
                    "maxOutputTokens": 100
                }
            }

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(url, json=payload, timeout=5.0)
                    
                    if response.status_code != 200:
                        logger.warning(f"⚠️ Gemini API bermasalah ({response.status_code}). Masuk ke Level 3 (Fallback).")
                        return default_result
                        
                    res_json = response.json()
                    ai_reply = res_json['candidates'][0]['content']['parts'][0]['text'].strip().upper()
                    logger.info(f"🔮 [Gemini Hakim Garis Result]: {ai_reply}")
                    
                    parsed = {}
                    for item in ai_reply.split(";"):
                        if "=" in item:
                            k, v = item.split("=")
                            parsed[k.strip()] = v.strip()
                    
                    keywords_str = parsed.get("KEYWORDS", "")
                    keywords_list = [kw.strip().lower() for kw in keywords_str.split(",") if kw.strip()]
                    
                    return {
                        "is_asking": parsed.get("INTENT") == "TRUE",
                        "sentiment": parsed.get("SENTIMEN", default_result["sentiment"]),
                        "keywords": keywords_list if keywords_list else default_result["keywords"]
                    }
                    
                except Exception as e:
                    logger.error(f"❌ Gagal koneksi ke Gemini API: {str(e)}. Masuk ke Level 3 (Fallback).")
                    return default_result

        return default_result

    @staticmethod
    def write_bot_log(level: str, message: str):
        """Mencatat aktivitas operasional bot ke dalam file text lokal log"""
        import os
        
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file_path = os.path.join(log_dir, "review_bot_activity.txt")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_line = f"[{timestamp}] [{level.upper()}] {message}\n"
        
        try:
            with open(log_file_path, "a", encoding="utf-8") as file:
                file.write(log_line)
        except Exception as e:
            logger.error(f"Gagal menulis ke file log lokal: {str(e)}")