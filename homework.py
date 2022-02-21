import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YANDEX_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
LIST_ERRORS = []
BOT = telegram.Bot(token=TELEGRAM_TOKEN)
logger = logging.getLogger(__name__)

HOMEWORK_VERDICTES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def send_message(bot, message):
    """Функция отправки сообщения."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        err_message = f'Ошибка при отправке сообщения: {error}'
        logger.error(err_message)
        if err_message not in LIST_ERRORS:
            send_message(BOT, err_message)
            LIST_ERRORS.append(err_message)


def get_api_answer(current_timestamp):
    """Проверяет ответ API Яндекс Практикум."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logger.error('Статус код != OK')
            raise ConnectionError('Ошибка статуса ответа от API')
    except Exception as error:
        err_message = f'Ошибка при запросе к основному API: {error}'
        logger.error(err_message)
        if err_message not in LIST_ERRORS:
            send_message(BOT, err_message)
            LIST_ERRORS.append(err_message)
        raise ConnectionError(err_message)
    response = response.json()
    return response


def check_response(response):
    """Проверка ответа от сервера Яндекс Практикума."""
    if response is None:
        logger.error('Ответ сервера не соответствует ожиданиям')
        raise ValueError('Ошибка ответа сервера')
    try:
        homeworks = response['homeworks']
    except Exception as error:
        err_message = f'Работ по ключу homeworks не найдено {error}'
        logger.error(err_message)
        if err_message not in LIST_ERRORS:
            send_message(BOT, err_message)
            LIST_ERRORS.append(err_message)
        raise KeyError(err_message)
    if not isinstance(response['homeworks'], list):
        logger.error('Неверный тип данных')
        raise TypeError('под ключом `homeworks`'
                        ' домашки приходят не в виде списка')
    if response['homeworks'] != []:
        return homeworks


def parse_status(homework):
    """Проверка статуса работ на сервере."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None or homework_status is None:
        err_message = 'Ответ сервера не соответствует ожиданиям'
        logger.error(err_message)
        if err_message not in LIST_ERRORS:
            send_message(BOT, err_message)
            LIST_ERRORS.append(err_message)
        raise ValueError(err_message)
    if homework_status not in HOMEWORK_VERDICTES.keys():
        err_message = 'Неверное значение статуса работы'
        logger.error(err_message)
        if err_message not in LIST_ERRORS:
            send_message(BOT, err_message)
            LIST_ERRORS.append(err_message)
        raise KeyError(err_message)
    verdict = HOMEWORK_VERDICTES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов на локальном сервере."""
    tokens = all([
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ])
    return tokens


def main():
    """Основная функция запуска."""
    if not check_tokens():
        err_message = 'Проверка токенов не прошла'
        logger.error(err_message)
        if err_message not in LIST_ERRORS:
            send_message(BOT, err_message)
            LIST_ERRORS.append(err_message)
        raise KeyError(err_message)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                send_message(BOT, parse_status(homework[0]))
            current_timestamp = response.get('current_date',
                                             current_timestamp)
            time.sleep(RETRY_TIME)

        except Exception as error:
            err_message = f'Сбой в работе программы: {error}'
            logger.error(err_message)
            if err_message not in LIST_ERRORS:
                send_message(BOT, err_message)
                LIST_ERRORS.append(err_message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
