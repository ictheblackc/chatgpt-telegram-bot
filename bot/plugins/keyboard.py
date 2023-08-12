from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


class Keyboard:
    def admin_menu(self):
        inline_keyboard = InlineKeyboardMarkup()
        inline_keyboard.row_width = 2
        inline_keyboard.add(
            InlineKeyboardButton('Изменить приветствие', callback_data='change_welcome'),
        )
        return inline_keyboard


keyboard = Keyboard()