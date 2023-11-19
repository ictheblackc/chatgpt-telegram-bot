import time
import os
from telebot import TeleBot
from telebot import types
from telebot.types import LabeledPrice
from .config import Config as conf
from .modules.database import database as db
from .modules.chatgpt import chatgpt as gpt
from .modules.message import message as msg
from .modules.admin import admin
from .modules.keyboard import keyboard as kb


# Create a bot
bot = TeleBot(conf.BOT_TOKEN)
# Create a database
db.create_db()
# Set OpenAI API key
gpt.set_key()
# Load search indexes
search_indexes = gpt.load_search_indexes(conf.DOCUMENT+'&rtpof=true&sd=true')


# @bot.message_handler(commands=['admin'])
# def command_admin(message):
#     admin.command_admin(bot, message)


# @bot.callback_query_handler(func=lambda call: True)
# def admin_callback_query_handler(call):
#     if call.data == 'change_welcome':
#         text = 'Введите новое приветствие'
#         send = bot.send_message(call.message.chat.id, text)
#         bot.register_next_step_handler(send, update_welcome)
#     elif call.data == 'exit':
#         text = 'Выход'
#         bot.send_message(call.message.chat.id, text)


# def update_welcome(message):
#     value = message.text
#     db.update_settings_by_key('welcome', value)
#     bot.send_message(message.chat.id, 'Текcт приветствия обновлен', reply_markup=kb.admin_menu())


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
    role = 'user'
    # Insert user into db
    db.insert_user(
        user_id=user_id,
        is_bot=is_bot,
        first_name=first_name,
        last_name=last_name,
        username=username,
        language_code=language_code,
        is_premium=is_premium,
        role=role,
    )
    user = db.get_user(message.from_user.id)
    if user[8] != '':
        text = 'Вы уже запускали бота :('
        bot.send_message(message.chat.id, text)
    else:
        # Send a welcome message
        text = msg.welcome
        start_button = types.InlineKeyboardButton('Начать', callback_data='start')
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(start_button)
        bot.send_message(message.chat.id, text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'start')
def start_callback(call: types.CallbackQuery):
    """First step."""
    text = msg.guide
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
    info += 'Ниша и средний чек продукта: {}; '.format(user[8])
    info += 'в среднем число продаж в месяц с блога: {}; '.format(user[9])
    info += 'хотел бы выйти на доход: {}.'.format(user[10])
    instruction = conf.INSTRUCTION

    response = generate_response(
        f'Бот-помощник Анастасии Любарской должен консультировать и направлять клиентов, согласно своей роли и —> {instruction}. Эти люди'
        f'ищут помощи в расширении своего бизнеса или увеличении продаж продукции. Вам будет предоставлена информация'
        f'о потенциального клиенте —> {info}. Составьте свой ответ с учетом этой информации, на какой доход хотел бы выйти клиент.'
        f'Ваш ответ должен быть не длинее 130 символов, а также должен содержать контекст ответов клиента и заинтересовать его в сотрудничестве с Анастасией.')

    text = response
    read_button = types.InlineKeyboardButton('Читать статью', callback_data='read')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(read_button)
    bot.send_message(message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'read')
def send_guide(call: types.CallbackQuery):
    """Send link."""
    #file = open(os.getcwd()+'/assets/document.pdf', 'rb')
    #bot.send_document(chat_id=call.message.chat.id, document=file)
    text = 'Ссылка - https://mighty-prawn-26c.notion.site/9-1-3-b669f7638a2041059b240c5500e74e8d?pvs=4'
    bot.send_message(chat_id=call.message.chat.id, text=text)
    text = msg.donotescape
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
    user = db.get_user(message.from_user.id)
    info = ''
    info += 'Ниша и средний чек продукта: {}; '.format(user[8])
    info += 'проблема клиента: {}.'.format(user[11])
    response = generate_response(
        f'Бот-помощник Анастасии Любарской продолжаете консультировать и направлять клиентов, согласно своей роли. Эти люди ищут'
        f'помощи в расширении своего бизнеса или увеличении продаж продукции. Вам будет предоставлены ответы'
        f'потенциального клиента —>{info}. В них будут ответы клиента'
        f'Ваш ответ должен быть такого формата —> ```-Последовательно сформируйте ответ согласно вышесказанной'
        f'инструкции. -Уложитесь в 130 слов. -Ваш ответ должен заканчиваться фиксированным текстом '
        f'У Анастасии есть очень сильный эфир с конкретными инструментами продаж, которые как раз покажут, как в твоей'
        f'нише увеличить продажи.` ``` **Важная информация:** Строго соответствовать вашей роли Бот-помощник Анастасии Любарской, никакой'
        f'дополнительной информации от себя добавлять нельзя')
    text = response
    bot.send_message(message.chat.id, text=text)
    bot.send_video(message.chat.id, video=open(os.getcwd()+'/assets/video.MP4', 'rb'), supports_streaming=True)
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
    #send_invoice(call.message, 'Онлайн-урок', 39900)
    text = """
    Вот ссылка на оплату\n
https://robo.market/product/3008432\n
Спасибо за ваш выбор. После оплаты Анастасия пришлет вам ссылку на эфир 🦋
    """
    bot.send_message(chat_id=call.message.chat.id, text=text)


@bot.callback_query_handler(func=lambda c: c.data == 'second_price')
def offer_step_expensive(call: types.CallbackQuery):
    """Send invoice for second link."""
    #send_invoice(call.message, 'Онлайн-урок', 99900)
    text = """
    Вот ссылка на оплату\n
https://robo.market/product/3008433\n
Спасибо за ваш выбор. После оплаты Анастасия пришлет вам ссылку на эфир 🦋
    """
    bot.send_message(chat_id=call.message.chat.id, text=text)


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
        text = conf.FIRST_LINK
        delete = True
    else:
        text = conf.SECOND_LINK
    message = bot.send_message(message.chat.id, text=text)
    if delete:
        time.sleep(conf.DELETE_LINK_TIME)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


def wait(message):
    """Send a message asking you to wait."""
    text = msg.wait
    message = bot.send_message(message.chat.id, text=text)
    #bot.register_next_step_handler(message, guide_step)


def send_invoice(message, label, amount):
    """Send an invoice with the specific data."""
    chat_id = message.chat.id
    title = 'Онлайн-урок'
    description = 'Онлайн-урок по продажам на 1 час. Внутри объясняется схема продаж, чтобы закрывать 6 из 10' \
                  'холодных клиентов с высоким чеком.'
    invoice_payload = 'Online lesson'
    provider_token = conf.PROVIDER_TOKEN
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
        conf.SYSTEM,
        message,
        search_indexes,
    )
    return answer
