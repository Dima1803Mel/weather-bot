import requests
import datetime
import asyncio
import math
from  config import open_weather_token, tg_bot_token
from aiogram import Bot, types, Dispatcher
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton,
    ReplyKeyboardRemove
)
import re
from pymorphy3 import MorphAnalyzer
from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    NewsNERTagger,
    PER,
    DatesExtractor,
    Doc
)

bot = Bot(token=tg_bot_token)
dp = Dispatcher()
morph = MorphAnalyzer()  # Инициализация морфологического анализатора

segmenter = Segmenter()  # Разбивает текст на токены (слова)
morph_vocab = MorphVocab()  # Морфологический словарь
emb = NewsEmbedding()  # Векторные представления слов
morph_tagger = NewsMorphTagger(emb)  # Морфологический разбор
syntax_parser = NewsSyntaxParser(emb)  # Синтаксический анализ
ner_tagger = NewsNERTagger(emb)  # Распознавание именованных сущностей
dates_extractor = DatesExtractor(morph_vocab)  # Извлечение дат

code_to_smile = {
        "Clear": "Ясно \U00002600",
        "Clouds": "Облачно \U00002601",
        "Rain": "Дождь \U00002614",
        "Drizzle": "Дождь \U00002614",
        "Thunderstorm": "Гроза \U000026A1",
        "Snow": "Снег \U0001F328",
        "Mist": "Туман \U0001F32B",
    }

def get_dates_keyboard(city_name: str):
    builder = InlineKeyboardBuilder()
    
    today = datetime.datetime.today()

    builder.add(InlineKeyboardButton(
        text = f"Сегодня",
        callback_data=f"weather_date:{today.strftime('%Y-%m-%d')}:{city_name}"
    ))
    
    builder.add(InlineKeyboardButton(
        text = f"Завтра({(today + datetime.timedelta(days=1)).strftime("%d-%m-%Y")})",
        callback_data=f"weather_date:{(today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")}:{city_name}"
    ))
    
    builder.add(InlineKeyboardButton(
        text = f"{(today + datetime.timedelta(days=2)).strftime("%d-%m-%Y")}",
        callback_data=f"weather_date:{(today + datetime.timedelta(days=2)).strftime("%Y-%m-%d")}:{city_name}"
    ))
    
    builder.add(InlineKeyboardButton(
        text = f"{(today + datetime.timedelta(days=3)).strftime("%d-%m-%Y")}",
        callback_data=f"weather_date:{(today + datetime.timedelta(days=3)).strftime("%Y-%m-%d")}:{city_name}"
    ))
    
    builder.add(InlineKeyboardButton(
        text = f"{(today + datetime.timedelta(days=4)).strftime("%d-%m-%Y")}",
        callback_data=f"weather_date:{(today + datetime.timedelta(days=4)).strftime("%Y-%m-%d")}:{city_name}"
    ))
    
    builder.add(InlineKeyboardButton(
        text = f"{(today + datetime.timedelta(days=5)).strftime("%d-%m-%Y")}",
        callback_data=f"weather_date:{(today + datetime.timedelta(days=5)).strftime("%Y-%m-%d")}:{city_name}"
    ))
    
    builder.adjust(3) # 3 кнопки в первом ряду, 3 во втором
    return builder.as_markup()
    

def extract_and_normalize_city(text):
    """
    Извлекает и нормализует название города из текста
    """
    
    doc = Doc(text)
    doc.segment(segmenter) # Разбиваем на токены (слова, знаки препинания)
    doc.tag_morph(morph_tagger) # Морфологический разбор - части речи, падеж, число и т.д.
    doc.parse_syntax(syntax_parser) # Синтаксический анализ - связи между словами
    doc.tag_ner(ner_tagger)  # Распознавание именованных сущностей
    
    city = dict()
    
    for span in doc.spans: # Проходим по всем найденным сущностям
        span.normalize(morph_vocab) # Приводим к нормальной форме
        if span.type == 'LOC': # Если сущность - локация (город, страна и т.д.)
            city = {
                'text':span.text, # Как написано в тексте
                'normalized': span.normal, # Нормальная форма
                'start': span.start, # Начальная позиция в тексте
                'stop': span.stop, # Конечная операция
                'type': span.type # Тип сущности
            }
            break # Нашли первый город - выходим из цикла
    
    if len(city) != 0:
        return city['normalized'] # Возвращаем нормальзированные название города
    else:
        return None # Город не найден
            
            
def get_city_coordinates(city_name):
    response = requests.get(f"https://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={open_weather_token}&lang=ru")
    
    data = response.json()
    
    lat = data[0]['lat']
    lon = data[0]['lon']
    actual_city_name = data[0]['name']
    
    return lat, lon, actual_city_name


async def get_weather_forecast(city_name, date_str):
    lat, lon, actual_city_name = get_city_coordinates(city_name)
    
    response = requests.get(f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={open_weather_token}&units=metric&lang=ru")
    
    data = response.json()
    
    target_date = datetime.datetime.strptime(f"{date_str} 12:00:00", "%Y-%m-%d %H:%M:%S")
    
    for forecast in data['list']:
        forecast_date = datetime.datetime.fromtimestamp(forecast['dt'])
        
        # Если нету нужной даты, то берем первый прогноз
        if forecast_date != target_date and forecast == data['list'][39]:
            forecast_date = data['list'][0]
            target_date = data['list'][0]
            forecast = data['list'][0]
        
        if forecast_date == target_date:
            weather_description = forecast["weather"][0]["main"]
            wd = code_to_smile.get(weather_description, forecast["weather"][0]["description"])
            
            cur_weather = forecast["main"]["temp"]
            humidity = forecast["main"]["humidity"]
            pressure = forecast["main"]["pressure"]
            wind = forecast["wind"]["speed"]
            feels_like = forecast["main"]["feels_like"]
            
            forecast_time = datetime.datetime.fromtimestamp(forecast['dt']).strftime('%d.%m.%Y %H:%M')
            
            message = (
                f"***Прогноз погоды на {forecast_time}***\n"
                f"📍 Город: {actual_city_name}\n"
                f"🌡 Температура: {cur_weather:.1f}°C (ощущается как {feels_like:.1f}°C)\n"
                f"☁️ Погода: {wd}\n"
                f"💧 Влажность: {humidity}%\n"
                f"📊 Давление: {math.ceil(pressure / 1.333)} мм рт. ст.\n"
                f"💨 Ветер: {wind} м/с"
            )
            
            return actual_city_name, message
        
    return actual_city_name, "Прогноз на эту дату не найден"
       
            
@dp.callback_query(lambda callback: callback.data.startswith("weather_date:"))
async def handle_weather(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    date_str = parts[1]
    name_city = parts[2]
    
    weather = await get_weather_forecast(name_city, date_str)
    
    _, message_weather = weather
    
    await callback.message.answer(
        message_weather
    )       

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("Привет!\n"
                        "Я чат-бот погоды\n"
                        "Просто напиши мне в каком городе тебя интересует погода и на какой день\n"
                        "P.S. Прогноз погоды доступен для городов не более чем на 5 дней вперед от текущей даты")
    
@dp.message()
async def handle_weather_request(message: types.Message):
    user_text = message.text.strip()
    city_name = extract_and_normalize_city(user_text)
    
    if not city_name:
        await message.answer("Не могу понять, какой город вы имеете в виду")
        return 
    
    await message.answer(
        text=f"На какой день вам интересно узнать про погоду в городе '{city_name}'",
        reply_markup=get_dates_keyboard(city_name)
    )    
    

async def main():
    await dp.start_polling(bot)
    
if __name__ == "__main__":
    asyncio.run(main())