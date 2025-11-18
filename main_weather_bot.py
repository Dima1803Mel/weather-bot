import requests
import datetime
import asyncio
import math
from  config import open_weather_token, tg_bot_token
from aiogram import Bot, types, Dispatcher
from aiogram.filters.command import Command

bot = Bot(token=tg_bot_token)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.reply("Привет! Напиши мне название города и я пришлю тебе сводку погоды")
    
@dp.message()
async def get_weather(message: types.Message):
    
    code_to_smile = {
        "Clear": "Ясно \U00002600",
        "Clouds": "Облачно \U00002601",
        "Rain": "Дождь \U00002614",
        "Drizzle": "Дождь \U00002614",
        "Thunderstorm": "Гроза \U000026A1",
        "Snow": "Снег \U0001F328",
        "Mist": "Туман \U0001F32B",
    }
    
    try:
        r = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?q={message.text}&appid={open_weather_token}&units=metric"
        )
        data = r.json()
        #pprint(data)
        
        weather_description = data["weather"][0]["main"]
        if weather_description in code_to_smile:
            wd = code_to_smile[weather_description]
        
        
        city = data["name"]
        cur_weather = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        pressure = data["main"]["pressure"]
        wind = data["wind"]["speed"]
        
        await message.answer(f"***{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}***\nПогода в городе: {city}\nТемпература: {cur_weather} C {wd}\nВлажность: {humidity} %\nДавление: {math.ceil(pressure / 1.333)} мм. рт. ст.\nВетер: {wind} м/с")
        
    except Exception as ex:
        await message.answer("\U00002620 Проверьте название города \U00002620")

async def main():
    await dp.start_polling(bot)
    
if __name__ == "__main__":
    asyncio.run(main())