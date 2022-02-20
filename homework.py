import logging
import os
import telegram
import time
import requests
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('YANDEX_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
logger = logging.getLogger(__name__)

HOMEWORK_STATUSES = {
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
        logger.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Проверяет ответ API Яндекс Практикум."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            logger.error('Статус код != 200')
            raise ConnectionError('Ошибка статуса ответа от API')
    except Exception as error:
        logger.error(f'Ошибка при запросе к основному API: {error}')
        raise ConnectionError('Ошибка подключения')
    response = response.json()
    return response


def check_response(response):
    """Проверка ответа от сервера Яндекс Практикума."""
    if response.get('homeworks') is None:
        logger.error('Ответ сервера не соответствует ожиданиям')
        raise ValueError('Ошибка ответа сервера')
    if type(response) != list:
        logger.error('Ответ сервера не список')
        raise TypeError('Неверный тип данных')
    try:
        response['homeworks']
    except Exception as error:
        logger.error(f'Работ по ключу homeworks не найдено {error}')
        raise KeyError('Работы не найдены')
    if response['homeworks'] != []:
        return response['homeworks']


def parse_status(homework):
    """Проверка статуса работ на сервере."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES.keys():
        logger.error('Неверное значение статуса работы')
        raise KeyError('Неверное значение статуса работы')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов на локальном сервере."""
    check = 1
    tokens = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    for i in tokens:
        if i is None:
            check = 0
    return check

# print(check_tokens())


def main():
    """Основная функция запуска."""
    if check_tokens() != 1:
        logger.error('Проверка токенов не прошла')
        raise KeyError('Проверка токенов не прошла')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                send_message(bot, parse_status(homework[0]))
            current_timestamp = response.get('current_date', current_timestamp)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
