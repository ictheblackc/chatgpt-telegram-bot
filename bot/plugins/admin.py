from .database import database as db


class Admin:
    """."""
    def __init__(self):
        self.admin_mode = False

    def command_admin(self, bot, message):
        user = db.get_user(user_id=message.from_user.id)
        user_id = user[0]
        if self._is_admin(user_id):
            self.admin_mode = True

    def _is_admin(self, user_id):
        user = db.get_user(user_id=user_id)
        role = user[7]
        is_admin = False
        if role == 'admin':
            is_admin = True
        return is_admin


admin = Admin()
