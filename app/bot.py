import sqlite3
import time
from telebot import TeleBot
from telebot import types
from telebot.types import LabeledPrice
from config import *
from database import database as db
from chatgpt import chatgpt as gpt
from app.message import message as msg


gpt.set_key()
search_indexes = gpt.load_search_indexes(DOCUMENT+'&rtpof=true&sd=true')
bot = TeleBot(BOT_TOKEN)
db.create_db()


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    is_bot = message.from_user.is_bot
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username
    language_code = message.from_user.language_code
    is_premium = message.from_user.is_premium

    db.insert_user(user_id, is_bot, first_name, last_name, username, language_code, is_premium)

    text = msg.welcome
    start_button = types.InlineKeyboardButton('Начать', callback_data='start')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(start_button)
    bot.send_message(message.chat.id, text, reply_markup=keyboard)


def wait(message):
    text = """Секунду, думаю, как вам лучше ответить 🤔"""
    message = bot.send_message(message.chat.id, text=text)
    bot.register_next_step_handler(message, guide_step)


def send_invoice(message, label, amount):
    bot.send_message(message.chat.id,
                     "Демонстрация приема платежей"
                     "\n\nПример счета:", parse_mode='Markdown')
    bot.send_invoice(
        chat_id=message.chat.id,
        title='Онлайн-урок',
        description='Онлайн-урок по продажам на 1 час. Внутри объясняется схема продаж, чтобы закрывать 6 из 10 холодных клиентов с высоким чеком.',
        invoice_payload='invoice_payload',
        provider_token=PROVIDER_TOKEN,
        currency='RUB',
        prices=[LabeledPrice(label=label, amount=amount)]
    )


@bot.callback_query_handler(func=lambda c: c.data == 'start')
def start_callback(call: types.CallbackQuery):
    text = """Отлично!\n
Я готов тебе отдать гайд Анастасии "Как создать авторский продукт и продавать его на 1-3 млн руб. на холодную аудиторию"\n
Но сначала прошу ответить на 3 простых вопроса. Хорошо?"""
    start_button = types.InlineKeyboardButton('Договорились', callback_data='ok')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(start_button)
    bot.send_message(chat_id=call.message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'ok')
def ok_callback(call: types.CallbackQuery):
    text = msg.question_1
    message = bot.send_message(chat_id=call.message.chat.id, text=text)
    bot.register_next_step_handler(message, sales_step)


def sales_step(message):
    db.update_user(message.from_user.id, 'answer_1', message.text)
    text = msg.question_2
    message = bot.send_message(message.chat.id, text=text)
    bot.register_next_step_handler(message, income_step)


def income_step(message):
    db.update_user(message.from_user.id, 'answer_2', message.text)
    text = msg.question_3
    message = bot.send_message(message.chat.id, text=text)
    bot.register_next_step_handler(message, guide_step)


def guide_step(message):
    db.update_user(message.from_user.id, 'answer_3', message.text)
    wait(message)
    user = db.get_user(message.from_user.id)
    info = ''
    info += 'Ниша и средний чек продукта: {}; '.format(user[7])
    info += 'в среднем продаж в месяц с блога: {}; '.format(user[8])
    info += 'хотел бы выйти на доход: {}.'.format(user[9])

    response = generate_response(
        f'Вот информация о клиенте: {info}. Используя эту информацию, составь небольшое сообщение клиенту. Не здоровайся с клиентом. В сообщении напиши, что у клиента перспективная ниша и адекватный запрос. Дальше предложи ему забрать гайд. Расскажи, что этот гайд поможет понять, кка отстроиться от конкурентов и стать заметным на рынке.')

    text = response
    download_button = types.InlineKeyboardButton('Скачать гайд', callback_data='download')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(download_button)
    bot.send_message(message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'download')
def send_guide(call: types.CallbackQuery):
    file = open("../kivy.pdf", "rb")
    bot.send_document(chat_id=call.message.chat.id, document=file)
    text = """Подождите, не уходите. У меня есть еще одна схема продаж, которая помогает Анастасии делать 6 из 10 продаж на холодную аудиторию (то есть на тех, кто только подписался на ее блог)\n
Интересно?"""
    interesting_button = types.InlineKeyboardButton('Да, интересно', callback_data='interesting')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(interesting_button)
    bot.send_message(chat_id=call.message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'interesting')
def problem_step(call: types.CallbackQuery):
    text = """Отлично!\n
Сначала расскажи, что тебе сейчас мешает, по твоему мнению, вдвое-втрое увеличить продажи?"""
    message = bot.send_message(chat_id=call.message.chat.id, text=text)
    bot.register_next_step_handler(message, send_testimonial)


def send_testimonial(message):
    conn = sqlite3.connect('../database.sqlite3')
    cur = conn.cursor()
    sql = """
    UPDATE users
    SET answer_4 = '{}'
    WHERE id = '{}';
    """.format(
        message.text,
        message.from_user.id
    )
    cur.execute(sql)
    conn.commit()

    wait(message)

    sql = """
    SELECT answer_1, answer_4
    FROM users
    WHERE id = '{}';
    """.format(
        message.from_user.id
    )
    cur.execute(sql)
    answers = cur.fetchall()
    info = ''
    for answer in answers:
        info += f'ниша и средний чек продукта: {answer[0]}; проблема клиента: {answer[1]}'

    response = generate_response(
        f'Вот информация о клиенте: {info}. Используя эту информацию, составь небольшое сообщение клиенту. Не здоровайся с клиентом. В сообщении напиши, что у Анастасии есть сильный эфир, который поможет преодолеть ту пролбему, о которой написал клиент. Предложи посмотреть отзыв про эфир.')

    text = response
    bot.send_message(message.chat.id, text=text)
    bot.send_video(message.chat.id, video=open('../video.MP4', 'rb'), supports_streaming=True)
    text = """Внутри эфира Анастасия разбирает:\n
- Как сейчас люди принимаюсь решение о покупке инфопродуктов и услуг?
- Почему ценность продукта уже не играет главной роли при принятии решения купить?
- Как продавать холодной аудитории, которая только подписалась на твой блог?
- Как на микроблоге с охватами от 200 просмотров стабильно продавать на + 1 млн руб. в месяц.\n
Что скажешь? Интересно?"""
    yes_button = types.InlineKeyboardButton('Да', callback_data='first_yes')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(yes_button)
    bot.send_message(message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'first_yes')
def offer_step_1(call: types.CallbackQuery):
    text = msg.offer
    yes_button = types.InlineKeyboardButton('Да', callback_data='second_yes')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(yes_button)
    bot.send_message(chat_id=call.message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'second_yes')
def offer_step_2(call: types.CallbackQuery):
    text = """На 48 часов эфир можно забрать за 399 руб.\n
Навсегда за 999 руб.\n
Какой вариант подходит?"""
    first_button = types.InlineKeyboardButton('399', callback_data='first_price')
    second_button = types.InlineKeyboardButton('999', callback_data='second_price')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(first_button)
    keyboard.add(second_button)
    bot.send_message(chat_id=call.message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'first_price')
def offer_step_cheap(call: types.CallbackQuery):
    send_invoice(call.message, 'Онлайн-урок', 39900)


@bot.callback_query_handler(func=lambda c: c.data == 'second_price')
def offer_step_expensive(call: types.CallbackQuery):
    send_invoice(call.message, 'Онлайн-урок', 99900)


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True,
        error_message=msg.checkout_error)


@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
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


def generate_response(message):
    # get answer from chatgpt
    answer = gpt.answer_index(
        SYSTEM,
        message,
        search_indexes,
    )
    return answer
