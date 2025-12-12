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
