import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Настройка Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

service = Service('C://chromedriver/chromedriver.exe')
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    url = 'https://yandex.ru/pogoda/search'
    driver.get(url)
    print(f"Открыт URL: {url}")

    zapros = input('Введите город и район: ')
    search_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, 'request'))
    )
    search_input.send_keys(zapros)
    search_input.send_keys(Keys.RETURN)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'place-list__item-name'))
    )

#проверка нас сразу перекинуло на сайт с погодой или на список городов
    if "pogoda" in driver.current_url and "lat" in driver.current_url:
        print(f"переходим по ссылке: {driver.current_url}")
        pass
    else:
        options = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'place-list__item-name'))
        )
        if options:
            print(f"Переходим по ссылке: {options[0].text}")
            options[0].click()

    try:
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
            EC.presence_of_element_located((By.CLASS_NAME, 'title title_level_1 header-title__title'))
        ).text

        print(f"В {name_city} Текущая температура: {temp}°C, Ощущается как: {feels_like}°C, Условия: {condition}")
    except Exception as e:
        print(f"Ошибка: {e}")

finally:
    driver.quit()
