import os
import logging
import requests
from dotenv import load_dotenv
import telebot
from geopy import geocoders
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
load_dotenv()

# Получение токенов из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YANDEX_WEATHER_TOKEN = os.getenv('YANDEX_WEATHER_TOKEN')

if not TELEGRAM_BOT_TOKEN or not YANDEX_WEATHER_TOKEN:
    raise ValueError("Не установлены необходимые переменные окружения: TELEGRAM_BOT_TOKEN или YANDEX_WEATHER_TOKEN")

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def geo_pos(city: str):
    """
    Получает координаты города с помощью геокодера Nominatim.
    """
    geolocator = geocoders.Nominatim(user_agent="telebot")
    try:
        location = geolocator.geocode(city)
        if location:
            logging.info(f"Координаты для города {city}: {location.latitude}, {location.longitude}")
            return str(location.latitude), str(location.longitude)
        else:
            raise ValueError("Город не найден")
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        raise ValueError(f"Ошибка геокодирования: {str(e)}")

def yandex_weather(latitude, longitude, token_yandex: str):
    """
    Получает данные о погоде из API Яндекс.Погода.
    """
    url = f"https://api.weather.yandex.ru/v2/informers?lat={latitude}&lon={longitude}&lang=ru_RU"
    headers = {
        'X-Yandex-API-Key': token_yandex
    }
    response = requests.get(url, headers=headers)
    logging.info(f"API Request: {url}")
    logging.info(f"API Response Status Code: {response.status_code}")
    logging.info(f"API Response Body: {response.text}")

    if response.status_code != 200:
        logging.error(f"Ошибка API: Код ответа {response.status_code}. Ответ: {response.text}")
        raise ValueError(f"Ошибка API: Код ответа {response.status_code}. Ответ: {response.text}")
    
    data = response.json()

    required_keys = ['fact', 'forecast']
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Некорректная структура данных: отсутствует ключ '{key}'")

    conditions = {
        'clear': 'ясно', 'partly-cloudy': 'малооблачно', 'cloudy': 'облачно с прояснениями',
        'overcast': 'пасмурно', 'drizzle': 'морось', 'light-rain': 'небольшой дождь',
        'rain': 'дождь', 'moderate-rain': 'умеренно сильный дождь', 'heavy-rain': 'сильный дождь',
        'continuous-heavy-rain': 'длительный сильный дождь', 'showers': 'ливень',
        'wet-snow': 'дождь со снегом', 'light-snow': 'небольшой снег', 'snow': 'снег',
        'snow-showers': 'снегопад', 'hail': 'град', 'thunderstorm': 'гроза',
        'thunderstorm-with-rain': 'дождь с грозой', 'thunderstorm-with-hail': 'гроза с градом'
    }

    fact = data['fact']
    forecast_hours = data['forecast']['hours']

    return {
        "condition": conditions.get(fact.get('condition'), 'Данные отсутствуют'),
        "temp_c": fact.get('temp', 'Данные отсутствуют'),
        "temp_f": round((fact.get('temp', 0) * 9/5) + 32, 2),
        "icon": fact.get('icon', 'Данные отсутствуют'),
        "forecast": [
            {
                "timestamp": hour.get('hour_ts', 'Данные отсутствуют'),
                "temperature": hour.get('temp', 'Данные отсутствуют')
            }
            for hour in forecast_hours[:48]  # Первые 48 часов
        ]
    }

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """
    Обработчик команд /start и /help.
    """
    bot.reply_to(
        message,
        f"Привет, {message.from_user.first_name}! Напиши название города для прогноза погоды."
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """
    Обработчик текстовых сообщений.
    """
    city = message.text.strip()
    if not city:
        bot.reply_to(message, "Вы не указали город. Пожалуйста, введите название города.")
        return
    try:
        lat, lon = geo_pos(city)
        weather_data = yandex_weather(lat, lon, YANDEX_WEATHER_TOKEN)
        response = (
            f"Погода в {city}:\n"
            f"Температура: {weather_data['temp_c']}°C / {weather_data['temp_f']}°F\n"
            f"Описание: {weather_data['condition']}\n"
            f"Иконка: {weather_data['icon']}\n"
            f"Прогноз на 48 часов:\n"
        )
        for hour in weather_data['forecast']:
            response += f"  Время: {hour['timestamp']}, Температура: {hour['temperature']}°C\n"
        bot.reply_to(message, response)
    except ValueError as e:
        if "403" in str(e):
            bot.reply_to(message, "Произошла ошибка авторизации к API. Проверьте токен.")
        else:
            bot.reply_to(message, f"Ошибка: {str(e)}. Проверьте название города.")
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)