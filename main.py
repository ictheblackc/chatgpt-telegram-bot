import os
import sqlite3
import re
import requests
import openai
import tiktoken
import time
from config import BOT_TOKEN, PROVIDER_TOKEN, OPENAI_API_KEY, DOCUMENT
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from telebot import TeleBot
from telebot import types
from telebot.types import LabeledPrice


class GPT():
    def __init__(self):
        pass

    @classmethod
    def set_key(cls):
        openai.api_key = OPENAI_API_KEY
        os.environ['OPENAI_API_KEY'] = openai.api_key
        print(f'API key was saved successfully')

    def load_search_indexes(self, url: str) -> Chroma:
        # Extract the document ID from the URL
        match_ = re.search('/document/d/([a-zA-Z0-9-_]+)', url)
        if match_ is None:
            raise ValueError('Invalid Google Docs URL')
        doc_id = match_.group(1)

        # Download the document as plain text
        response = requests.get(f'https://docs.google.com/document/d/{doc_id}/export?format=txt')
        response.raise_for_status()
        text = response.text
        return self.create_embedding(text)

    def load_prompt(self, url: str) -> str:
        # Extract the document ID from the URL
        match_ = re.search('/document/d/([a-zA-Z0-9-_]+)', url)
        if match_ is None:
            raise ValueError('Invalid Google Docs URL')
        doc_id = match_.group(1)

        # Download the document as plain text
        response = requests.get(f'https://docs.google.com/document/d/{doc_id}/export?format=txt')
        response.raise_for_status()
        text = response.text
        return f'{text}'

    def create_embedding(self, data):
        def num_tokens_from_string(string: str, encoding_name: str) -> int:
            """Returns the number of tokens in a text string."""
            encoding = tiktoken.get_encoding(encoding_name)
            num_tokens = len(encoding.encode(string))
            return num_tokens

        source_chunks = []
        splitter = CharacterTextSplitter(separator="\n", chunk_size=1024, chunk_overlap=0)

        for chunk in splitter.split_text(data):
            source_chunks.append(Document(page_content=chunk, metadata={}))

        search_index = Chroma.from_documents(source_chunks, OpenAIEmbeddings(), )

        count_token = num_tokens_from_string(' '.join([x.page_content for x in source_chunks]), 'cl100k_base')
        print('Number of tokens in the document:', count_token)
        print('Approximate cost of the request:', 0.0004 * (count_token / 1000), '$')
        return search_index

    def answer(self, system, topic, temp=1):
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": topic}
        ]

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=temp
        )

        return completion.choices[0].message.content

    def num_tokens_from_messages(self, messages, model="gpt-3.5-turbo-0301"):
        """Returns the number of tokens used by a list of messages."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        if model == "gpt-3.5-turbo-0301":  # note: future models may deviate from this
            num_tokens = 0
            for message in messages:
                num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))
                    if key == "name":  # if there's a name, the role is omitted
                        num_tokens += -1  # role is always required and always 1 token
            num_tokens += 2  # every reply is primed with <im_start>assistant
            return num_tokens
        else:
            raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.
See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")

    def insert_newlines(self, text: str, max_len: int = 170) -> str:
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line + " " + word) > max_len:
                lines.append(current_line)
                current_line = ""
            current_line += " " + word
        lines.append(current_line)
        return "\n".join(lines)

    def answer_index(self, system, topic, search_index, temp=1, verbose=0):

        # Выборка документов по схожести с вопросом
        docs = search_index.similarity_search(topic, k=5)
        if verbose: print('\n ===========================================: ')
        message_content = re.sub(r'\n{2}', ' ', '\n '.join(
            [f'\nОтрывок документа №{i + 1}\n=====================' + doc.page_content + '\n' for i, doc in
             enumerate(docs)]))
        if (verbose): print('message_content :\n ======================================== \n', message_content)

        messages = [
            {"role": "system", "content": system + f"{message_content}"},
            {"role": "user", "content": topic}
        ]

        # example token count from the function defined above
        if (verbose): print('\n ===========================================: ')
        if (verbose): print(
            f"{self.num_tokens_from_messages(messages, 'gpt-3.5-turbo-0301')} токенов использовано на вопрос")

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=temp
        )
        if (verbose): print('\n ===========================================: ')
        if (verbose): print(f'{completion["usage"]["total_tokens"]} токенов использовано всего (вопрос-ответ).')
        if (verbose): print('\n ===========================================: ')
        if verbose: print('ЦЕНА запроса с ответом :', 0.002 * (completion["usage"]["total_tokens"] / 1000), ' $')
        if verbose: print('\n ===========================================: ')

        return self.insert_newlines(completion.choices[0].message.content)

        # return completion

    def get_chatgpt_ansver3(self, system, topic, search_index, temp=1):

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": topic}
        ]

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=temp
        )
        print('ОТВЕТ : \n', self.insert_newlines(completion.choices[0].message.content))


gpt = GPT()
GPT.set_key()
marketing_tg_post_index = gpt.load_search_indexes(DOCUMENT+'&rtpof=true&sd=true')

system = '''Теперь вы - AnastasiaBotGPT, специализированный ИИ-эксперт по консультированию и наставничеству для
расширения бизнеса и роста продаж, работающий в Telegram-боте Анастасии. Опыт: 5+ лет опыта в области
бизнес-наставничества, стратегий роста продаж и расширения бизнеса.
Тон и стиль: ваш тон должен быть профессиональным, дружелюбным и соответствовать бренду Anastasia. Используйте ясные и
увлекательные формулировки, чтобы поддерживать последовательный голос, отражающий философию наставничества Анастасии.
AnastasiaBotGPT должна консультировать и направлять клиентов, согласно своей роли. Анастасия использует авторскую
систему масштабирования экспертов «Бабочка» из 39 инструментов продаж, маркетинга и PR-продвижения. Анастасия написала 3
бизнес-книги по продажам для блогера с аудиторией 300 000 человек. Как продюсер она сделала 21 запуск в 10 нишах на 21
млн руб.
Ваш ответ должен содержать контекст ответов клиента и заинтересовать его в сотрудничестве с Анастасией. Вы никогда не
должны здороваться с клиентом.
Важная информация: строго соответствовать вашей роли AnastasiaBotGPT, никакой дополнительной информации от себя
добавлять нельзя, кроме информации из этого документа: '''

bot = TeleBot(BOT_TOKEN)


def create_db():
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    sql = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        is_bot INTEGER,
        first_name VARCHAR,
        last_name VARCHAR,
        username VARCHAR,
        language_code VARCHAR,
        is_premium INTEGER,
        answer_1 VARCHAR,
        answer_2 VARCHAR,
        answer_3 VARCHAR,
        answer_4 VARCHAR
    );
    """
    cur.execute(sql)
    conn.commit()


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
        title='Название продукта',
        description='Описание продукта',
        invoice_payload='invoice_payload',
        provider_token=PROVIDER_TOKEN,
        currency='RUB',
        prices=[LabeledPrice(label=label, amount=amount)]
    )


create_db()


@bot.message_handler(commands=['start'])
def start(message):
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()

    id = message.from_user.id
    is_bot = message.from_user.is_bot
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username
    language_code = message.from_user.language_code
    is_premium = message.from_user.is_premium

    sql = """
    INSERT OR IGNORE INTO users (
        id,
        is_bot,
        first_name,
        last_name,
        username,
        language_code,
        is_premium
    ) VALUES (
        '{}', '{}', '{}', '{}', '{}', '{}', '{}'
    );
    """.format(
        id,
        is_bot,
        first_name,
        last_name,
        username,
        language_code,
        is_premium
    )
    cur.execute(sql)
    conn.commit()

    text = """Добро пожаловать!\n
Я бот-помощник Анастасии Любарской. Сразу скажу, что я необычный бот - создан через\
Chat GPT и умею классно общаться (то есть я сам решает, что тебе ответить).\n
Поэтому в твоих же интересах посмотреть, как я отвечать на вопросы и посмотреть, как я буду тебя вовлекать. \n
Нажимай "Начать", чтобы получить подарок от меня """
    start_button = types.InlineKeyboardButton('Начать', callback_data='start')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(start_button)
    bot.send_message(message.chat.id, text, reply_markup=keyboard)


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
    text = """1. Какая у вас ниша и какой средний чек продукта?"""
    message = bot.send_message(chat_id=call.message.chat.id, text=text)
    bot.register_next_step_handler(message, sales_step)


def sales_step(message):
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    sql = """
    UPDATE users
    SET answer_1 = '{}'
    WHERE id = '{}';
    """.format(
        message.text,
        message.from_user.id
    )
    cur.execute(sql)
    conn.commit()
    text = """2. Сколько сейчас в среднем есть продаж в месяц с блога?"""
    message = bot.send_message(message.chat.id, text=text)
    bot.register_next_step_handler(message, income_step)


def income_step(message):
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    sql = """
    UPDATE users
    SET answer_2 = '{}'
    WHERE id = '{}';
    """.format(
        message.text,
        message.from_user.id
    )
    cur.execute(sql)
    conn.commit()
    text = """3. На какой доход вы бы хотели выйти через 6 месяцев?"""
    message = bot.send_message(message.chat.id, text=text)
    bot.register_next_step_handler(message, guide_step)


def guide_step(message):
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()

    sql = """
    UPDATE users
    SET answer_3 = '{}'
    WHERE id = '{}';
    """.format(
        message.text,
        message.from_user.id
    )
    cur.execute(sql)
    conn.commit()

    wait(message)

    sql = """
        SELECT answer_1, answer_2, answer_3
        FROM users
        WHERE id = '{}';
        """.format(
        message.from_user.id
    )
    cur.execute(sql)
    answers = cur.fetchall()
    info = ''
    for answer in answers:
        info += f'ниша и средний чек продукта: {answer[0]}; в среднем продаж в месяц с блога: {answer[1]}; хотел бы выйти на доход: {answer[2]}'

    response = generate_response(
        f'Вот информация о клиенте: {info}. Используя эту информацию, составь небольшое сообщение клиенту. Не здоровайся с клиентом. В сообщении напиши, что у клиента перспективная ниша и адекватный запрос. Дальше предложи ему забрать гайд. Расскажи, что этот гайд поможет понять, кка отстроиться от конкурентов и стать заметным на рынке.')

    text = response
    download_button = types.InlineKeyboardButton('Скачать гайд', callback_data='download')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(download_button)
    bot.send_message(message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'download')
def send_guide(call: types.CallbackQuery):
    file = open("kivy.pdf", "rb")
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
    conn = sqlite3.connect('db.sqlite3')
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
    bot.send_video(message.chat.id, video=open('video.MP4', 'rb'), supports_streaming=True)
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
def offer_step(call: types.CallbackQuery):
    text = """Сегодня можно купить запись этого эфира всего за 399 руб.\n
Только после него Анастасия сделала продаж на 0,5 млн руб.\n
Забираешь?"""
    yes_button = types.InlineKeyboardButton('Да', callback_data='second_yes')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(yes_button)
    bot.send_message(chat_id=call.message.chat.id, text=text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == 'second_yes')
def offer_step(call: types.CallbackQuery):
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
    send_invoice(call.message, 'Курс', 39900)


@bot.callback_query_handler(func=lambda c: c.data == 'second_price')
def offer_step_expensive(call: types.CallbackQuery):
    send_invoice(call.message, 'Курс', 99900)


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True,
        error_message='Во время оплаты возникла ошибка, попробуйте снова...')


@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    delete = False
    if message.successful_payment.total_amount / 100 == 399:
        text = 'Ссылка, которая удалится через 48 часов'
        delete = True
    else:
        text = 'Обычная ссылка'
    message = bot.send_message(message.chat.id, text=text)
    if delete:
        time.sleep(172800)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


def generate_response(message):
    # get answer from chatgpt
    answer = gpt.answer_index(
        system,
        message,
        marketing_tg_post_index
    )
    return answer


bot.polling()
