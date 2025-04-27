import os
import requests
from dotenv import load_dotenv
import telebot
from geopy import geocoders
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Загрузка переменных окружения
load_dotenv()

# Получение токенов из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YANDEX_WEATHER_TOKEN = os.getenv('YANDEX_WEATHER_TOKEN')

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
            print(f"Координаты для города {city}: {location.latitude}, {location.longitude}")
            return str(location.latitude), str(location.longitude)
        else:
            raise ValueError("Город не найден")
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        raise ValueError(f"Ошибка геокодирования: {str(e)}")

def yandex_weather(latitude, longitude, token_yandex: str):
    """
    Получает данные о погоде из API Яндекс.Погода.
    """
    url = f"https://api.weather.yandex.ru/v2/forecast?lat={latitude}&lon={longitude}&lang=ru_RU"
    headers = {
        'X-Yandex-API-Key': token_yandex
    }
    response = requests.get(url, headers=headers)
    data = response.json()

    print("API Response:", data)  # Логируем полный ответ

    # Проверка на ошибки от API
    if 'error' in data:
        raise ValueError(f"Ошибка API: {data['error']['message']}")

    # Проверка структуры ответа
    required_keys = ['fact', 'info']
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

    return {
        "condition": conditions.get(data['fact'].get('condition'), 'неизвестно'),
        "temp": data['fact'].get('temp', 'N/A'),
        "wind_dir": data['fact'].get('wind_dir', 'N/A'),
        "pressure_mm": data['fact'].get('pressure_mm', 'N/A'),
        "humidity": data['fact'].get('humidity', 'N/A'),
        "link": data.get('info', {}).get('url', 'N/A')
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
    try:
        lat, lon = geo_pos(city)
        weather_data = yandex_weather(lat, lon, YANDEX_WEATHER_TOKEN)
        response = (
            f"Погода в {city}:\n"
            f"Температура: {weather_data['temp']}°C\n"
            f"Описание: {weather_data['condition']}\n"
            f"Давление: {weather_data['pressure_mm']} мм рт.ст.\n"
            f"Влажность: {weather_data['humidity']}%\n"
            f"Подробнее: {weather_data['link']}"
        )
        bot.reply_to(message, response)
    except ValueError as e:
        bot.reply_to(message, f"Ошибка: {str(e)}. Проверьте название города.")
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)