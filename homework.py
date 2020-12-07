import logging
import os
import time
import json

import requests
import telegram
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
                logger.info('Работа ещё не проверена')
            current_timestamp = new_homework.get(
                'current_date', int(time.time())
                )
            time.sleep(SLEEP_GET)

        except Exception as e:
            logger.error(f'Бот столкнулся с ошибкой: {e}')
            time.sleep(SLEEP_ERROR)


if __name__ == '__main__':
    main()
