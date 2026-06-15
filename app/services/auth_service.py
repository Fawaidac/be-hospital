# app/services/auth_service.py
import hashlib
from app.models.user import UserModel


class AuthService:

    @staticmethod
    def verify_pin(current_user: UserModel, pin_input: str) -> tuple[bool, str]:
        """
        Verifikasi PIN 6 digit user menggunakan hash SHA-256.
        Returns: (is_valid: bool, error_message: str)
        """
        if not current_user.pin:
            return False, "User tidak memiliki PIN."

        input_pin_hash = hashlib.sha256(pin_input.encode("utf-8")).hexdigest()

        if input_pin_hash != current_user.pin:
            return False, "PIN salah."

        return True, ""
