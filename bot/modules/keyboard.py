from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


class Keyboard:
    def admin_menu(self):
        inline_keyboard = InlineKeyboardMarkup()
        inline_keyboard.row_width = 1
        inline_keyboard.add(
            InlineKeyboardButton('Изменить приветствие', callback_data='change_welcome'),
            InlineKeyboardButton('Выход', callback_data='exit'),
        )
        return inline_keyboard


keyboard = Keyboard()