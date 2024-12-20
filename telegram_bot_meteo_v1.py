import json
import requests
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

# Файл для хранения данных пользователей
DATA_FILE = "user_data.json"

# Функции для работы с JSON
def load_data():
    try:
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    data = load_data()

    if user_id not in data:
        data[user_id] = {
            "name": user_name,
            "cities": ["null", "null", "null"]
        }
        save_data(data)
        await update.message.reply_text(
            f"Привет, {user_name}! Вы добавлены в систему.\n"
            "Команда /weather для погоды, а /settings для настройки городов."
        )
    else:
        await update.message.reply_text("Вы уже зарегистрированы!\nКоманда /weather для погоды, а /settings для настройки городов.")

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data:
        await update.message.reply_text("Сначала используйте команду /start.")
        return ConversationHandler.END

    cities = data[user_id]["cities"]
    keyboard = [[KeyboardButton(cities[i])] for i in range(3)]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите ячейку для изменения:", reply_markup=reply_markup)
    return 1

async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data:
        await update.message.reply_text("Сначала используйте команду /start.")
        return ConversationHandler.END

    user_message = update.message.text
    for i in range(3):
        if data[user_id]["cities"][i] == user_message:
            context.user_data["city_index"] = i
            await update.message.reply_text("Введите название нового города:")
            return 2

    await update.message.reply_text("Произошла ошибка. Попробуйте ещё раз.")
    return ConversationHandler.END

async def save_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    city_index = context.user_data.get("city_index")

    if city_index is None:
        await update.message.reply_text("Произошла ошибка. Попробуйте ещё раз.")
        return ConversationHandler.END

    new_city = update.message.text
    old_city = data[user_id]["cities"][city_index]
    data[user_id]["cities"][city_index] = new_city
    save_data(data)

    await update.message.reply_text(f"В ячейку с номером {city_index+1} был записан {new_city} вместо {old_city}.")
    return ConversationHandler.END

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data:
        await update.message.reply_text("Сначала используйте команду /start.")
        return ConversationHandler.END

    cities = data[user_id]["cities"]
    keyboard = [[KeyboardButton(city)] for city in cities if city != "null"]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите город:", reply_markup=reply_markup)
    return 1

async def fetch_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text
    try:
        # Получение координат города
        headers = {
            "User-Agent": "WeatherBot/1.0 (your_email@example.com)"
        }
        geocode_url = f"https://nominatim.openstreetmap.org/search?city={city}&format=json"
        response = requests.get(geocode_url, headers=headers, timeout=10)
        response.raise_for_status()
        geocode_data = response.json()

        if not geocode_data:
            await update.message.reply_text("Город не найден. Попробуйте другой.")
            return ConversationHandler.END

        lat, lon = geocode_data[0]["lat"], geocode_data[0]["lon"]

        # Получение данных о погоде
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode&timezone=auto"
        weather_response = requests.get(weather_url, timeout=10)
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        # Проверка данных
        if "daily" not in weather_data or not weather_data["daily"].get("temperature_2m_min") or not weather_data["daily"].get("temperature_2m_max"):
            await update.message.reply_text("Не удалось получить данные о погоде для данного города.")
            return ConversationHandler.END

        daily = weather_data["daily"]

        # Словарь для расшифровки погодного кода
        weather_code_map = {
            0: "Ясно ☀️",
            1: "Преимущественно ясно 🌤️",
            2: "Переменная облачность ⛅",
            3: "Пасмурно ☁️",
            45: "Туман 🌫️",
            48: "Туман с изморозью 🌫️❄️",
            51: "Слабая морось 🌦️",
            61: "Слабой интенсивности дождь 🌧️",
            71: "Слабой интенсивности снегопад 🌨️",
            80: "Грозы 🌩️",
        }

        # Формирование сообщения с погодой
        weather_message = f"Погода в {city} на 3 дня:\n"
        for i in range(3):
            temp_min = daily['temperature_2m_min'][i]
            temp_max = daily['temperature_2m_max'][i]
            precipitation = daily.get('precipitation_sum', [0])[i]  # Осадки
            weather_code = daily.get('weathercode', [0])[i]  # Код погоды
            weather_description = weather_code_map.get(weather_code, "Неизвестные условия 🌈")

            weather_message += (
                f"День {i+1}:\n"
                f"Температура: {temp_min}°C - {temp_max}°C\n"
                f"Осадки: {precipitation} мм\n"
                f"Условия: {weather_description}\n\n"
            )

        await update.message.reply_text(weather_message)
    except requests.exceptions.HTTPError as http_err:
        await update.message.reply_text(f"HTTP ошибка: {http_err}")
        print(f"HTTP ошибка: {http_err}")
    except requests.exceptions.RequestException as req_err:
        await update.message.reply_text("Ошибка сети. Попробуйте ещё раз позже.")
        print(f"Ошибка сети: {req_err}")
    except IndexError as index_err:
        await update.message.reply_text("Ошибка данных. Проверьте название города.")
        print(f"Ошибка данных: {index_err}")
    except Exception as e:
        await update.message.reply_text("Произошла ошибка при получении данных о погоде.")
        print(f"Неизвестная ошибка: {e}")
    return ConversationHandler.END


# Основная функция
def main():
          application = Application.builder().token("***************").build()

    settings_handler = ConversationHandler(
        entry_points=[CommandHandler("settings", settings)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_city)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_city)],
        },
        fallbacks=[]
    )

    weather_handler = ConversationHandler(
        entry_points=[CommandHandler("weather", weather)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_weather)],
        },
        fallbacks=[]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(settings_handler)
    application.add_handler(weather_handler)

    application.run_polling()

if __name__ == "__main__":
    main()
