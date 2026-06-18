# app/services/auth_service.py
from sqlalchemy.orm import Session

from app.core.security import hash_password, needs_hash_upgrade, verify_password
from app.models.user import UserModel


class AuthService:

    @staticmethod
    def verify_pin(current_user: UserModel, pin_input: str, db: Session = None) -> tuple[bool, str, bool]:
        """
        Verify PIN with Argon2 while supporting legacy SHA-256 hashes.
        Returns: (is_valid, error_message, was_upgraded)
        """
        if not current_user.pin:
            return False, "User does not have a PIN.", False

        if not verify_password(pin_input, current_user.pin):
            return False, "Invalid PIN.", False

        was_upgraded = False
        if needs_hash_upgrade(current_user.pin):
            current_user.pin = hash_password(pin_input)
            was_upgraded = True
            if db is not None:
                db.commit()

        return True, "", was_upgraded
