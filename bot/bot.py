import time
from telebot import TeleBot
from telebot import types
from telebot.types import LabeledPrice
from .config import *
from .plugins.database import database as db
from .plugins.chatgpt import chatgpt as gpt
from .plugins.message import message as msg


# Create a bot
bot = TeleBot(BOT_TOKEN)
# Create a database
db.create_db()
# Set OpenAI API key
gpt.set_key()
# Load search indexes
search_indexes = gpt.load_search_indexes(DOCUMENT+'&rtpof=true&sd=true')


@bot.message_handler(commands=['start'])
def command_start(message):
    """Start work after starting the bot."""
    # Get user info
    user_id = message.from_user.id
    is_bot = message.from_user.is_bot
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username
    language_code = message.from_user.language_code
    is_premium = message.from_user.is_premium
    # Insert user into db
    db.insert_user(user_id, is_bot, first_name, last_name, username, language_code, is_premium)
    # Send a welcome message
    text = msg.welcome
    start_button = types.InlineKeyboardButton('Начать', callback_data='start')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(start_button)
    bot.send_message(message.chat.id, text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'start')
def start_callback(call: types.CallbackQuery):
    """First step."""
    text = """Отлично!\n
Я готов тебе отдать гайд Анастасии "Как создать авторский продукт и продавать его на 1-3 млн руб. на холодную
аудиторию"\n Но сначала прошу ответить на 3 простых вопроса. Хорошо?"""
    start_button = types.InlineKeyboardButton('Договорились', callback_data='ok')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(start_button)
    bot.send_message(chat_id=call.message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'ok')
def ok_callback(call: types.CallbackQuery):
    """Send first question."""
    text = msg.question_1
    message = bot.send_message(chat_id=call.message.chat.id, text=text)
    bot.register_next_step_handler(message, sales_step)


def sales_step(message):
    """Send second question."""
    db.update_user(message.from_user.id, 'answer_1', message.text)
    text = msg.question_2
    message = bot.send_message(message.chat.id, text=text)
    bot.register_next_step_handler(message, income_step)


def income_step(message):
    """Send third question."""
    db.update_user(message.from_user.id, 'answer_2', message.text)
    text = msg.question_3
    message = bot.send_message(message.chat.id, text=text)
    bot.register_next_step_handler(message, guide_step)


def guide_step(message):
    """Make first request to ChatGPT API."""
    db.update_user(message.from_user.id, 'answer_3', message.text)
    wait(message)
    user = db.get_user(message.from_user.id)
    info = ''
    info += 'Ниша и средний чек продукта: {}; '.format(user[7])
    info += 'в среднем продаж в месяц с блога: {}; '.format(user[8])
    info += 'хотел бы выйти на доход: {}.'.format(user[9])

    response = generate_response(
        f'Вот информация о клиенте: {info}. Используя эту информацию, составь небольшое сообщение клиенту. Не'
        f'здоровайся с клиентом. В сообщении напиши, что у клиента перспективная ниша и адекватный запрос. Дальше'
        f'предложи ему забрать гайд. Расскажи, что этот гайд поможет понять, кка отстроиться от конкурентов и стать'
        f'заметным на рынке.')

    text = response
    download_button = types.InlineKeyboardButton('Скачать гайд', callback_data='download')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(download_button)
    bot.send_message(message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'download')
def send_guide(call: types.CallbackQuery):
    """Send document."""
    file = open("../assets/document.pdf", "rb")
    bot.send_document(chat_id=call.message.chat.id, document=file)
    text = """Подождите, не уходите. У меня есть еще одна схема продаж, которая помогает Анастасии делать 6 из 10
    продаж на холодную аудиторию (то есть на тех, кто только подписался на ее блог)\n
    Интересно?"""
    interesting_button = types.InlineKeyboardButton('Да, интересно', callback_data='interesting')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(interesting_button)
    bot.send_message(chat_id=call.message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'interesting')
def problem_step(call: types.CallbackQuery):
    """Send fourth question."""
    text = msg.question_4
    message = bot.send_message(chat_id=call.message.chat.id, text=text)
    bot.register_next_step_handler(message, send_testimonial)


def send_testimonial(message):
    """Send a message and video with description."""
    db.update_user(message.from_user.id, 'answer_4', message.text)
    wait(message)
    user = db.get_user(message.from_user.id)
    info = ''
    info += 'Ниша и средний чек продукта: {}; '.format(user[7])
    info += 'проблема клиента: {}.'.format(user[10])
    response = generate_response(
        f'Вот информация о клиенте: {info}. Используя эту информацию, составь небольшое сообщение клиенту. Не'
        f'здоровайся с клиентом. В сообщении напиши, что у Анастасии есть сильный эфир, который поможет преодолеть ту'
        f'пролбему, о которой написал клиент. Предложи посмотреть отзыв про эфир.')
    text = response
    bot.send_message(message.chat.id, text=text)
    bot.send_video(message.chat.id, video=open('../assets/video.MP4', 'rb'), supports_streaming=True)
    text = msg.video_description
    yes_button = types.InlineKeyboardButton('Да', callback_data='first_yes')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(yes_button)
    bot.send_message(message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'first_yes')
def offer_step_1(call: types.CallbackQuery):
    """Send first offer's part."""
    text = msg.offer_1
    yes_button = types.InlineKeyboardButton('Да', callback_data='second_yes')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(yes_button)
    bot.send_message(chat_id=call.message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'second_yes')
def offer_step_2(call: types.CallbackQuery):
    """Send second offer's part."""
    text = msg.offer_2
    first_button = types.InlineKeyboardButton('399', callback_data='first_price')
    second_button = types.InlineKeyboardButton('999', callback_data='second_price')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(first_button)
    keyboard.add(second_button)
    bot.send_message(chat_id=call.message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'first_price')
def offer_step_cheap(call: types.CallbackQuery):
    """Send invoice for first link."""
    send_invoice(call.message, 'Онлайн-урок', 39900)


@bot.callback_query_handler(func=lambda c: c.data == 'second_price')
def offer_step_expensive(call: types.CallbackQuery):
    """Send invoice for second link."""
    send_invoice(call.message, 'Онлайн-урок', 99900)


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    """Answer the PreQecheckoutQuery."""
    bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True,
        error_message=msg.checkout_error)


@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    """Confirms the successful payment."""
    delete = False
    if message.successful_payment.total_amount / 100 == 399:
        text = FIRST_LINK
        delete = True
    else:
        text = SECOND_LINK
    message = bot.send_message(message.chat.id, text=text)
    if delete:
        time.sleep(DELETE_LINK_TIME)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


def wait(message):
    """Send a message asking you to wait."""
    text = msg.wait
    message = bot.send_message(message.chat.id, text=text)
    bot.register_next_step_handler(message, guide_step)


def send_invoice(message, label, amount):
    """Send an invoice with the specific data."""
    chat_id = message.chat.id
    title = 'Онлайн-урок'
    description = 'Онлайн-урок по продажам на 1 час. Внутри объясняется схема продаж, чтобы закрывать 6 из 10' \
                  'холодных клиентов с высоким чеком.'
    invoice_payload = 'Online lesson'
    provider_token = PROVIDER_TOKEN
    currency = 'RUB'
    bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        invoice_payload=invoice_payload,
        provider_token=provider_token,
        currency=currency,
        prices=[LabeledPrice(label=label, amount=amount)]
    )


def generate_response(message):
    """Generate response from ChatGPT."""
    answer = gpt.answer_index(
        SYSTEM,
        message,
        search_indexes,
    )
    return answer
