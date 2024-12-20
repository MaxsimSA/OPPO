import json
import requests
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

class SettingsHandler:
    def __init__(self):
        self.data_file = "user_data.json"

    def load_data(self):
        try:
            with open(self.data_file, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def save_data(self, data):
        with open(self.data_file, "w") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Инициализация пользователя при вызове команды /start."""
        user_id = str(update.effective_user.id)
        user_name = update.effective_user.first_name
        data = self.load_data()

        if user_id not in data:
            data[user_id] = {
                "name": user_name,
                "cities": ["null", "null", "null"]
            }
            self.save_data(data)
            await update.message.reply_text(
                f"Привет, {user_name}! Вы добавлены в систему.\n"
                "Команда /weather для погоды, а /settings для настройки городов."
            )
        else:
            await update.message.reply_text(
                "Вы уже зарегистрированы!\nКоманда /weather для погоды, а /settings для настройки городов."
            )

    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор города для изменения."""
        user_id = str(update.effective_user.id)
        data = self.load_data()

        if user_id not in data:
            await update.message.reply_text("Сначала используйте команду /start.")
            return ConversationHandler.END

        cities = data[user_id]["cities"]
        keyboard = [[KeyboardButton(cities[i])] for i in range(3)]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Выберите ячейку для изменения:", reply_markup=reply_markup)
        return 1

    async def set_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка изменения города."""
        user_id = str(update.effective_user.id)
        data = self.load_data()

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

    async def save_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранение нового города."""
        user_id = str(update.effective_user.id)
        data = self.load_data()
        city_index = context.user_data.get("city_index")

        if city_index is None:
            await update.message.reply_text("Произошла ошибка. Попробуйте ещё раз.")
            return ConversationHandler.END

        new_city = update.message.text
        old_city = data[user_id]["cities"][city_index]
        data[user_id]["cities"][city_index] = new_city
        self.save_data(data)

        await update.message.reply_text(f"В ячейку с номером {city_index+1} был записан {new_city} вместо {old_city}.")
        return ConversationHandler.END

class WeatherHandler:
    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--disable-software-rasterizer")   
        self.chrome_options.add_argument("--ignore-certificate-errors")
        self.chrome_options.add_argument("--allow-insecure-localhost")
        self.chrome_options.add_argument("--disable-extensions")

        self.service = Service('C://chrome/chromedriver.exe')

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса выбора города для отображения погоды."""
        user_id = str(update.effective_user.id)
        data = SettingsHandler().load_data()

        if user_id not in data:
            await update.message.reply_text("Сначала используйте команду /start.")
            return ConversationHandler.END

        cities = data[user_id]["cities"]
        keyboard = [[KeyboardButton(city)] for city in cities if city != "null"]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Выберите город:", reply_markup=reply_markup)
        return 1

    async def fetch_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение погоды для выбранного города."""
        city = update.message.text
        driver = webdriver.Chrome(service=self.service, options=self.chrome_options)

        try:
            url = 'https://yandex.ru/pogoda/search'
            driver.get(url)

            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, 'request'))
            )
            search_input.send_keys(city)
            search_input.send_keys(Keys.RETURN)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'place-list__item-name'))
            )

            if "pogoda" in driver.current_url and "lat" in driver.current_url:
                pass
            else:
                options = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, 'place-list__item-name'))
                )
                if options:
                    options[0].click()

            temp = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'fact__temp'))
            ).text
            feels_like = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.fact__feels-like .temp__value'))
            ).text
            condition = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'link__condition'))
            ).text
            name_city = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.title.title_level_1.header-title__title'))
            ).text
            await update.message.reply_text(
                f"Текущая температура в {name_city}: {temp}°C\nОщущается как: {feels_like}°C\nУсловия: {condition}"
            )
        except Exception as e:
            await update.message.reply_text("Произошла ошибка при получении данных о погоде.")
            print(f"Ошибка: {e}")
        finally:
            driver.quit()
        return ConversationHandler.END

# Основная функция
def main():
    load_dotenv()
    application = Application.builder().token(os.getenv("TOKEN")).build()

    # Создаём объект SettingsHandler
    settings_handler = SettingsHandler()

    # Создаём объект WeatherHandler
    weather_handler = WeatherHandler()

    # Команда /start
    application.add_handler(CommandHandler("start", settings_handler.start))

    # Обработчик для настроек
    settings_conversation = ConversationHandler(
        entry_points=[CommandHandler("settings", settings_handler.settings)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, settings_handler.set_city)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, settings_handler.save_city)],
        },
        fallbacks=[]
    )

    application.add_handler(settings_conversation)

    # Обработчик для погоды
    weather_conversation = ConversationHandler(
        entry_points=[CommandHandler("weather", weather_handler.weather)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, weather_handler.fetch_weather)],
        },
        fallbacks=[]
    )

    application.add_handler(weather_conversation)

    application.run_polling()

if __name__ == "__main__":
    main()
