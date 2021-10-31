import requests
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
MESSAGE_ERROR_SAVE = "Ошибка сохранена"
ERROR_CHAT = "1474614285"
URL_PATTERN = r'/^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/'

URL_TG_API = "http://194.50.24.4:8000/api/"


def gen_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 3
    markup.add(
        InlineKeyboardButton("Распарсить статью", callback_data="news"),
        InlineKeyboardButton("Сообщить об ошибке", callback_data="error"),

    )
    return markup


def gen_markup_message(text):
    markup = InlineKeyboardMarkup()
    markup.row_width = 3
    markup.add(
        InlineKeyboardButton(u'\u2705', callback_data="ok"),
        InlineKeyboardButton(u'\u274c', callback_data="bad"),

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

        elif call.data == "ok":
            urls = get_url(call.message.json['entities'][0]['url'])
            res = requests.post(URL_TG_API + "add_parsing_site", json={"urls": urls})
            if res.ok:
                bot.send_message(chat_id, text="ok")
            else:
                bot.send_message(chat_id, text="не могу добавить урл, поытайтесь позже")

        elif call.data == "bad":
            # bot.send_message(ERROR_CHAT, call.message.json['entities'][0]['url'])
            bot.send_message(chat_id,
                             text=f"Опишите проблему [Link]({call.message.json['entities'][0]['url']}) \n",
                             parse_mode="Markdown",
                             reply_markup=types.ForceReply())

        @bot.message_handler()
        def proc_reply(message):
            try:
                if message.reply_to_message.text == MESSAGE_NEW:
                    send_message_new(message)
                elif message.reply_to_message.text == MESSAGE_KEY:
                    send_message_error(message)
                elif "Опишите проблему" in message.reply_to_message.text:
                    bot.forward_message(ERROR_CHAT, message.chat.id, message.message_id)
                    bot.send_message(ERROR_CHAT, message.reply_to_message.json['entities'][0]['url'])
                    try:
                        urls = get_url(message.reply_to_message.json['entities'][0]['url'])
                        res = requests.post(URL_TG_API + "check_parsing_site", json={"urls": urls})
                        if int(res.text) > 0:
                            res = requests.post(URL_TG_API + "deactivate_parsing_site", json={"urls": urls})
                            bot.send_message(message.chat.id,
                                             "Этот сайт раньше работал правильно, сейчас мы деактивировали его")

                        else:
                            bot.send_message(message.chat.id, MESSAGE_ERROR_SAVE)

                    except Exception:
                        bot.send_message(message.chat.id, MESSAGE_ERROR_SAVE)




            except Exception:
                bot.send_message(message.chat.id, "Отправьте сообщение ответом")
    except Exception:
        pass


def get_url(ful_url):
    from urllib.parse import urlparse
    parse_url = urlparse(ful_url)
    url = f"{parse_url.scheme}://{parse_url.hostname}"
    return [url, url + "/"]


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
            bot.send_message(ERROR_CHAT, message.text)

            bot.send_message(message.chat.id, MESSAGE_ERROR_SAVE)

    except Exception:
        bot.send_message(message.chat.id, "Не могу записать ошибку")


def chunkstring(string, length):
    return (string[0 + i:length + i] for i in range(0, len(string), length))


def send_message_new(message):
    try:
        if not check_url(message.text):
            bot.send_message(message.chat.id, MESSAGE_ERROR_URL)
        else:
            article = Article(message.text)
            article.download()
            article.parse()
            title = article.title
            text = article.text or ""
            text_first_part = text[:len(title) * 3]
            if title in text_first_part:
                if len(text_first_part.replace(title + "\n", "")) != len(text_first_part):
                    text = text.replace(title + "\n", "", 1)
                else:
                    try:
                        first_par = text.split('\n')[0]
                        first_par_without_par = first_par.replace(title, "")
                        if "." not in first_par_without_par and "!" not in first_par_without_par and "?" not in first_par_without_par:
                            text = text.replace(title, "", 1)
                    except Exception:
                        pass
            text = re.sub("\n\n+", "\n\n", text)
            message_text = ""
            message_text += "Title: \n" + (article.title or "") + "\n"
            message_text += "Meta: \n" + (article.meta_description or "") + "\n"
            message_text += "Text: \n" + text + "\n"
            message_text += "Date: \n" + str(article.publish_date or "") + "\n"
            message_text += f"[Link]({message.text}) \n"

            messages_list = chunkstring(message_text, 4095)
            m_list = list(messages_list)
            for i in range(len(m_list)):
                if i == len(m_list) - 1:

                    bot.send_message(message.chat.id, m_list[i], reply_markup=gen_markup_message(message.text),
                                     parse_mode="Markdown")
                else:
                    bot.send_message(message.chat.id, m_list[i],
                                     parse_mode="Markdown")

    except Exception:
        bot.send_message(message.chat.id, MESSAGE_ERROR)


def check_url(text):
    urls = re.findall(r'http(?:s)?://\S+', text)
    return len(urls) == 1


if __name__ == '__main__':
    while True:
        bot.polling(none_stop=True, timeout=100, long_polling_timeout=10000000)
