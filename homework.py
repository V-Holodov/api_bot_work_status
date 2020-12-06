import logging
import os
import time
import json

import requests
import telegram
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format=('%(asctime)s: [%(levelname)s]: %(name)s: %(message)s')
    )
logger = logging.getLogger(__name__)

load_dotenv()

PRAKTIKUM_TOKEN = os.getenv("PRAKTIKUM_TOKEN")
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
SLEEP_GET = 1200
SLEEP_ERROR = 5

bot = telegram.Bot(token=TELEGRAM_TOKEN)
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dispatcher = updater.dispatcher
updater.start_polling()


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Привет, я твой ассистент проверки домашки")


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


def echo(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
dispatcher.add_handler(echo_handler)


def recent_homwork():
    params = {'from_date': 0}
    headers = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
    try:
        homework_statuses = requests.get(
            URL,
            params=params,
            headers=headers)
        response = homework_statuses.json()
        name = response.get('homeworks')[0]['homework_name']
        comment = response.get('homeworks')[0]['reviewer_comment']
        date = response.get('homeworks')[0]['date_updated']
        return f'Домашняя работа: {name},\n{comment},\nДата: {date}'
    except RequestException as e:
        logger.error(f'ошибка соединения - {e}')
    except json.JSONDecodeError as e:
        logger.error(f'ошибка файла JSON - {e}')


def check_recent_homwork(update, context):
    text = recent_homwork()
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    logger.info('Запрос комментария последней работы')


check_recent_homwork_handler = CommandHandler('check', check_recent_homwork)
dispatcher.add_handler(check_recent_homwork_handler)


def parse_homework_status(homework):
    try:
        homework_name = homework['homework_name']
        if homework['status'] == 'rejected':
            verdict = 'К сожалению в работе нашлись ошибки.'
        elif homework['status'] == 'approved':
            verdict = (
                'Ревьюеру всё понравилось, '
                'можно приступать к следующему уроку.'
                )
        else:
            logger.info('Cтатус домашней работы неизвестного типа')
        return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'
    except KeyError as e:
        logger.error(f'Сервис не вернул ожидаемый ответ: {e}')


def get_homework_statuses(current_timestamp):
    params = {'from_date': current_timestamp}
    headers = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
    try:
        homework_statuses = requests.get(
            URL,
            params=params,
            headers=headers)
        response = homework_statuses.json()
        return response
    except RequestException as e:
        logger.error(f'ошибка соединения - {e}')
    except json.JSONDecodeError as e:
        logger.error(f'ошибка файла JSON - {e}')


def send_message(message, bot_client):
    return bot_client.send_message(chat_id=CHAT_ID, text=message)


def main():
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            if new_homework.get('homeworks'):
                send_message(
                    parse_homework_status(new_homework['homeworks'][0]),
                    bot
                    )
                logger.info('Сообщение отправлено')
            else:
                logger.info('Работа не проверена')
            current_timestamp = new_homework.get(
                'current_date', int(time.time())
                )
            time.sleep(SLEEP_GET)

        except Exception as e:
            logger.error(f'Бот столкнулся с ошибкой: {e}')
            time.sleep(SLEEP_ERROR)


if __name__ == '__main__':
    main()
