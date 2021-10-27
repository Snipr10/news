from newspaper import Article
import re
import telebot
from telebot import types
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

bot = telebot.TeleBot('2081961920:AAERnhcfR-cEjw84VKwLG1RGc3Ra22G0v3k')

MESSAGE_NEW = "Отправь ссылку на статью в ответ на это сообщение"
MESSAGE_KEY = "Отправь ссылку на статью и текст ошибки в ответ на это сообщение"
MESSAGE_ERROR_URL = "Не могу найти ссылку, в сообщении должна быть одна ссылка"
MESSAGE_ERROR = "Что-то пошло не так"
MESSAGE_NOT_FOUND_TASK = "Не мог найти таску, похожие:"
MESSAGE_RESET_TASKS = "Таски сброшены"

URL_PATTERN = r'/^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/'


def gen_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 3
    markup.add(
        InlineKeyboardButton("Распарсить статью", callback_data="news"),
        InlineKeyboardButton("Сообщить об ошибке", callback_data="error"),

    )
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        chat_id = call.message.chat.id
        if call.data == "news":
            bot.send_message(chat_id,
                             text=MESSAGE_NEW, reply_markup=types.ForceReply())

        elif call.data == "error":
            bot.send_message(chat_id,
                             text=MESSAGE_KEY, reply_markup=types.ForceReply())

        @bot.message_handler()
        def proc_reply(message):
            try:
                if message.reply_to_message.text == MESSAGE_NEW:
                    send_message_new(message)
                elif message.reply_to_message.text == MESSAGE_KEY:
                    send_message_error(message)
            except Exception:
                bot.send_message(message.chat.id, "Отправьте сообщение ответом")
    except Exception:
        pass


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
                 text=f'Привет, я буду помогать тебе со статьями, перейди в меню: /menu')


@bot.message_handler(commands=['menu'])
def message_handler(message):
    bot.send_message(message.chat.id, "Выбери действие", reply_markup=gen_markup())


def send_message_error(message):
    try:
        if not check_url(message.text):
            bot.send_message(message.chat.id, MESSAGE_ERROR_URL)
        else:
            bot.send_message("1474614285", message.text)

            bot.send_message(message.chat.id, "Ошибка сохранена")

    except Exception:
        bot.send_message(message.chat.id, "Не могу записать ошибку")


def chunkstring(string, length):
    return (string[0+i:length+i] for i in range(0, len(string), length))


def send_message_new(message):
    try:
        if not check_url(message.text):
            bot.send_message(message.chat.id, MESSAGE_ERROR_URL)
        else:
            article = Article(message.text)
            article.download()
            article.parse()
            message_text = ""
            message_text += "Title: \n" + (article.title or "") + "\n"
            message_text += "Meta: \n" + (article.meta_description or "") + "\n"
            message_text += "Text: \n" + (article.text or "") + "\n"
            message_text += "Date: \n" + str(article.publish_date or "") + "\n"
            messages_list = chunkstring(message_text, 4095)
            for m in messages_list:
                bot.send_message(message.chat.id, m)
    except Exception:
        bot.send_message(message.chat.id, MESSAGE_ERROR)


def check_url(text):
    urls = re.findall(r'http(?:s)?://\S+', text)
    return len(urls) == 1


if __name__ == '__main__':
    while True:
        bot.polling(none_stop=True, timeout=100, long_polling_timeout=10000000)
