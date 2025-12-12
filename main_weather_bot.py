import requests
import datetime
import asyncio
import math
from  config import open_weather_token, tg_bot_token
from aiogram import Bot, types, Dispatcher
from aiogram.filters.command import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
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
        text = f"Сегодня({today.strftime('%Y-%m-%d')})",
        callback_data=f"weather_date:{today.strftime('%Y-%m-%d')}:city_name:{city_name}"
    ))
    
    builder.add(InlineKeyboardButton(
        text = f"Завтра({(today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")})",
        callback_data=f"weather_date:{(today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")}:city_name:{city_name}"
    ))
    
    builder.add(InlineKeyboardButton(
        text = f"{(today + datetime.timedelta(days=2)).strftime("%Y-%m-%d")}",
        callback_data=f"weather_date:{(today + datetime.timedelta(days=2)).strftime("%Y-%m-%d")}:city_name:{city_name}"
    ))
    
    builder.add(InlineKeyboardButton(
        text = f"{(today + datetime.timedelta(days=3)).strftime("%Y-%m-%d")}",
        callback_data=f"weather_date:{(today + datetime.timedelta(days=3)).strftime("%Y-%m-%d")}:city_name:{city_name}"
    ))
    
    builder.add(InlineKeyboardButton(
        text = f"{(today + datetime.timedelta(days=4)).strftime("%Y-%m-%d")}",
        callback_data=f"weather_date:{(today + datetime.timedelta(days=4)).strftime("%Y-%m-%d")}:city_name:{city_name}"
    ))
    
    builder.add(InlineKeyboardButton(
        text = f"{(today + datetime.timedelta(days=5)).strftime("%Y-%m-%d")}",
        callback_data=f"weather_date:{(today + datetime.timedelta(days=5)).strftime("%Y-%m-%d")}:city_name:{city_name}"
    ))
    
    builder.adjust(3) # 3 кнопки в первом ряду, 3 во втором
    return builder.as_markup()
    

def extract_and_normalize_city(text):
    """
    Извлекает и нормализует название города из текста
    """
    text = re.sub(r'[^\w\s,]', '', text.lower())
    
    doc = Doc(text)
    doc.segment(segmenter) # Разбиваем на токены
    doc.tag_morph(morph_tagger) # Морфологический разбор
    doc.parse_syntax(syntax_parser) # Синтаксический анализ
    doc.tag_ner(ner_tagger)  # Распознавание именованных сущностей
    
    for span in doc.spans:
        if span.type == PER: # PER = Person/Place (в Natasha это и люди, и места)
            city_candidate = span.text.strip()
            if (len(city_candidate.split()) > 1 or city_candidate[0].isupper()):
                # Приводим к нормальной форме
                parsed = morph.parse(city_candidate)[0]
                return parsed.normal_form.title()

    # Если Natasha не нашел, пробуем извлечь первое существительное
    words = text.split()
    for word in words:
        if len(word) > 2:  # Слишком короткие слова игнорируем
            parsed = morph.parse(word)[0]
            if 'NOUN' in parsed.tag:
                return parsed.normal_form.title()
    
    # Если не нашли, возвращаем весь текст как есть (но в нормализованном виде)
    if words:
        parsed = morph.parse(words[0])[0]
        return parsed.normal_form.title()
    
    return None
            
            
def get_city_coordinates(city_name):
    response = requests.get(f"https://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={open_weather_token}")
    
    data = response.json()
    
    lat = data[0]['lat']
    lon = data[0]['lon']
    actual_city_name = data[0]['name']
    
    return lat, lon, actual_city_name
    
async def get_weather_forecast(city_name, date_str):
    lat, lon, actual_city_name = get_city_coordinates(city_name)
    
    response = requests.get(f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={open_weather_token}&units=metric&lang=ru")
    
    data = response.json()
    
    target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    forecast_for_date = []
    
    for forecast in data['list']:
        forecast_date = datetime.datetime.fromtimestamp(forecast['dt']).date()
        if forecast_date == target_date:
            forecast_for_date.append(forecast)
            
        if forecast_for_date:
            # Берем прогноз на 12:00 или первый доступный
            forecast = None
            for f in forecast_for_date:
                forecast_time = datetime.datetime.fromtimestamp(f['dt']).hour
                if forecast_time == 12:  # Предпочитаем полдень
                    forecast = f
                    break
            
            if not forecast:
                forecast = forecast_for_date[0]  # Или первый доступный
            
            # Анализируем погоду на весь день
            weather_description = forecast["weather"][0]["main"]
            wd = code_to_smile.get(weather_description, forecast["weather"][0]["description"])
            
            cur_weather = forecast["main"]["temp"]
            humidity = forecast["main"]["humidity"]
            pressure = forecast["main"]["pressure"]
            wind = forecast["wind"]["speed"]
            feels_like = forecast["main"]["feels_like"]
            
            forecast_time = datetime.datetime.fromtimestamp(forecast['dt']).strftime('%H:%M')
            
            date_formatted = target_date.strftime('%d.%m.%Y')
            
            message = (
                f"***Прогноз погоды на {date_formatted} ({forecast_time})***\n"
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
async def handle_date_callback(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    date_str = parts[1]
    name_city = parts[3]
    
    weather = await get_weather_forecast(name_city, date_str)
    
    _, message = weather
    
    await callback.message.answer(
        message,
        parse_mode="Markdown"
    )
            

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("Привет! Напиши мне название города и я пришлю тебе сводку погоды")
    
@dp.message()
async def handle_weather_request(message: types.Message):
    user_text = message.text.strip()
    city_name = extract_and_normalize_city(user_text)
    
    if not city_name:
        await message.answer("Не могу понять, какой город вы имеете в виду")
    
    await message.answer(
        reply_markup=get_dates_keyboard(city_name)
    )    
    #city, weather_message = await get_weather_forecast(city_name)
    
# @dp.message()
# async def get_weather(message: types.Message):
#     try:
#         r = requests.get(
#             f"https://api.openweathermap.org/data/2.5/weather?q={message.text}&appid={open_weather_token}&units=metric&lang=ru"
#         )
#         data = r.json()
#         #pprint(data)
        
#         weather_description = data["weather"][0]["main"]
#         if weather_description in code_to_smile:
#             wd = code_to_smile[weather_description]
        
        
#         city = data["name"]
#         cur_weather = data["main"]["temp"]
#         humidity = data["main"]["humidity"]
#         pressure = data["main"]["pressure"]
#         wind = data["wind"]["speed"]
        
#         await message.answer(
#             f"***{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}***\n"
#             f"Погода в городе: {city}\nТемпература: {cur_weather} C {wd}\n"
#             f"Влажность: {humidity} %\nДавление: {math.ceil(pressure / 1.333)} мм. рт. ст.\n"
#             f"Ветер: {wind} м/с"
#         )
        
#     except Exception as ex:
#         await message.answer("\U00002620 Проверьте название города \U00002620")

async def main():
    await dp.start_polling(bot)
    
if __name__ == "__main__":
    asyncio.run(main())