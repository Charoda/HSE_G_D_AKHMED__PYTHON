import json
import logging
import asyncio
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from io import BytesIO, StringIO
import traceback
from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputFile
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types.input_file import BufferedInputFile
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession # Импортируем AiohttpSession
from aiohttp import ClientSession, ClientTimeout
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton,  InlineKeyboardButton, InlineKeyboardMarkup
import db_migration as db_processor
from activelifeuser import User as ActiveUser 
import foodapi as fa

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Объект бота

load_dotenv()
API_TOKEN=os.getenv("API_TOKEN")
if not API_TOKEN:
    print("API_TOKEN не указан")

PROXY_URL = os.getenv("PROXY_URL")

session = AiohttpSession(proxy=PROXY_URL, timeout=300)

bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

class RegistrationStates(StatesGroup):
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_age = State()
    waiting_for_activity = State()
    waiting_for_city = State()
    waiting_for_water_goal = State()
    waiting_for_calorie_goal = State()

class LoggingStates(StatesGroup):
    logging_water = State()
    logging_food = State()
    logging_food_amount = State()
    logging_activity_type = State()  
    logging_activity_duration = State() 

@dp.message(Command("start"))
async def cmd_start(message: Message):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='Вода', callback_data="water_log"))
    builder.add(InlineKeyboardButton(text='Еда', callback_data="food_log"))
    builder.add(InlineKeyboardButton(text='Активность', callback_data="activity_log"))
    builder.add(InlineKeyboardButton(text='Заполнение профиля', callback_data="set_profile"))
    builder.add(InlineKeyboardButton(text='Профиль', callback_data="profile"))
    builder.adjust(2)  # 2 кнопки в ряду
    
    keyboard = builder.as_markup()
    await message.answer(
        f"Здравствуй, {message.from_user.full_name}, выберите действие!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "set_profile")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Давайте зарегистрируем ваши данные!\n"
        "Введите ваш вес (в кг):")
    await state.set_state(RegistrationStates.waiting_for_weight)
    await callback.answer()

@dp.message(RegistrationStates.waiting_for_weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = int(message.text)
        if weight <= 0 or weight > 300:
            await message.answer("Пожалуйста, введите корректный вес (1-300 кг):")
            return
        
        await state.update_data(weight=weight)
        await message.answer("Отлично! Теперь введите ваш рост (в см):")
        await state.set_state(RegistrationStates.waiting_for_height)
    except ValueError:
        await message.answer("Пожалуйста, введите число для веса:")

@dp.message(RegistrationStates.waiting_for_height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = int(message.text)
        if height <= 0 or height > 250:
            await message.answer("Пожалуйста, введите корректный рост (1-250 см):")
            return
        
        await state.update_data(height=height)
        await message.answer("Хорошо! Теперь введите ваш возраст:")
        await state.set_state(RegistrationStates.waiting_for_age)
    except ValueError:
        await message.answer("Пожалуйста, введите число для роста:")

@dp.message(RegistrationStates.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age <= 0 or age > 120:
            await message.answer("Пожалуйста, введите корректный возраст (1-120 лет):")
            return
        await state.update_data(age=age)

        await message.answer("Введите ваш город проживания:")
        await state.set_state(RegistrationStates.waiting_for_city)
    except ValueError:
        await message.answer("Пожалуйста, введите число для возраста:")

@dp.message(RegistrationStates.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
    city = message.text.strip()
    try:
        if len(city) < 2 or len(city) > 100:
            await message.answer("Пожалуйста, введите корректное название города:")
            return
    
        await state.update_data(city=city)

        await message.answer("Введите желаемую норму воды, либо введите 0, если желаете, чтобы за Вас эта норма была расчитана:")
        await state.set_state(RegistrationStates.waiting_for_water_goal)
    except ValueError:
        await message.answer("Введите пожалуйста норму воды в литрах")
    
@dp.message(RegistrationStates.waiting_for_water_goal)
async def process_water_goal(message: Message, state: FSMContext):
    water_goal = float(message.text)
    try:
        await state.update_data(water_goal=water_goal)
        await message.answer("Введите желаемую норму калорий, в ккал. Либо введите 0, если желаете, чтобы за Вас эта норма была расчитана")
        await state.set_state(RegistrationStates.waiting_for_calorie_goal)
    except ValueError:
        await message.answer("Введите пожалуйста желаемую норму калорий в ккал")


@dp.message(RegistrationStates.waiting_for_calorie_goal)
async def process_calories_goal(message: Message, state: FSMContext):
    try:
        calories_goal = float(message.text)
        await state.update_data(calories_goal=calories_goal)
        data = await state.get_data()
        
        # Получаем норму воды из состояния или 0
        water_goal = data.get('water_goal', 0)
        
        # Создаем объект пользователя
        user1 = ActiveUser(
            name=message.from_user.full_name,
            weight=data['weight'],
            height=data['height'],
            age=data['age'],
            city=data['city'],
            water_norm=water_goal,      # в литрах
            calories_norm=calories_goal # в ккал
        )
        
        # Сохраняем в базу данных, передавая user_id
        await db_processor.save_to_db(user1)
        
        await message.answer(str(user1))

        await state.clear()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
        ])
        await message.answer("Профиль успешно заполнен.\nПредлагаем взглянуть на него.", 
                             reply_markup=keyboard)
        
    except ValueError:
        await message.answer("Введите пожалуйста желаемую норму калорий в ккал")

@dp.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    try:
        user_id = callback.from_user.full_name
        
        # Получаем профиль пользователя из базы данных
        profile = await get_profile(user_id)
        
        if not profile:
            # Если профиль не найден, предлагаем заполнить
            await callback.message.answer(
                "Профиль не найден.\n"
                "Пожалуйста, заполните ваш профиль сначала.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Заполнить профиль", callback_data="set_profile")]
                ])
            )
            await callback.answer()
            return
        
        # Рассчитываем прогресс
        water_goal = profile.get('water_goal', 1) or 1 
        calorie_goal = profile.get('calorie_goal', 1) or 1
        print('calories_goal is {calorie_goal}')
        logged_water = profile.get('logged_water', 0)
        logged_calories = profile.get('logged_calories', 0)
        
        burned_calories = profile.get('burned_calories', 0)
        
        record_date = profile.get('record_date')
        if record_date:
            if hasattr(record_date, 'strftime'):
                last_update_str = record_date.strftime("%d.%m.%Y")
            else:
                last_update_str = str(record_date)
        else:
            last_update_str = "Неизвестно"
        
        profile_text = (
            f" <b>Ваш профиль</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f" <b>Пользователь:</b> {callback.from_user.full_name}\n"
            f" <b>Вес:</b> {profile.get('weight', 'Не указан')} кг\n"
            f" <b>Рост:</b> {profile.get('height', 'Не указан')} см\n"
            f" <b>Возраст:</b> {profile.get('age', 'Не указан')} лет\n"
            f" <b>Город:</b> {profile.get('city', 'Не указан')}\n"
            f" <b>Уровень активности:</b> {profile.get('activity', 'Не указан')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f" <b>Вода сегодня:</b> {logged_water} из {water_goal} мл\n"
            f" <b>Калории сегодня:</b> {logged_calories} из {calorie_goal} ккал\n"
            
            f" <b>Сожжено калорий:</b> {burned_calories} ккал\n"
            f" <b>Последнее обновление:</b> {last_update_str}\n"
        )

        await callback.message.answer(profile_text, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при показе профиля: {e}")
        await callback.message.answer("ошибка при создании профиля")
        await callback.answer()

@dp.callback_query(F.data == "water_log")
async def start_log_water(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💧 Введите количество выпитой воды в мл:")
    await state.set_state(LoggingStates.logging_water)
    await callback.answer()

@dp.message(LoggingStates.logging_water)
async def process_water_log(message: Message, state: FSMContext):
    try:
        water_ml = int(message.text)
        if water_ml <= 0:
            await message.answer("Пожалуйста, введите положительное число.")
            return
        
        # Логируем воду
        success = await db_processor.log_water(message.from_user.full_name, water_ml)
        
        if success:
            profile = await db_processor.get_user_profile(message.from_user.id)
            
            if profile:
                water_goal = profile.get('water_goal', 1) or 1
                logged_water = profile.get('logged_water', 0)
                water_progress = min(int((logged_water / water_goal) * 100), 100) if water_goal > 0 else 0
                
                water_bar = "█" * (water_progress // 10) + "░" * (10 - (water_progress // 10))
                
                response = (
                    f"Добавлено {water_ml} мл воды\n\n"
                    f" <b>Прогресс по воде:</b>\n"
                    f"{logged_water}/{water_goal} мл\n"
                    f"{water_bar} {water_progress}%\n"
                    f"Осталось: {max(water_goal - logged_water, 0)} мл"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="👤 Показать профиль", callback_data="profile")],
                    [InlineKeyboardButton(text="💧 Добавить еще воды", callback_data="water_log")]
                ])
                
                await message.answer(response, parse_mode="HTML", reply_markup=keyboard)
            else:
                await message.answer(f"Добавлено {water_ml} мл воды")
        else:
            await message.answer("Ошибка при сохранении данных")
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите число")


@dp.callback_query(F.data == "food_log")
async def start_log_food(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите название продукта:\n\n"
        "Примеры: green apple, pizza, coffee..."
    )
    await state.set_state(LoggingStates.logging_food)
    await callback.answer()

@dp.message(LoggingStates.logging_food)
async def process_food_name(message: Message, state: FSMContext):
    food_name = message.text.strip()
    
    if len(food_name) < 2:
        await message.answer("Название продукта должно быть не менее 2 символов")
        return
    await state.update_data(food_name=food_name)
    calories = fa.FoodApi.get_calories_by_food_name(food_name)
    
    if calories is not None:
        await state.update_data(calories_per_100g=calories)
        await message.answer(
            f"<b>{food_name.capitalize()}</b>\n"
            f"Калорийность: {calories} ккал/100г\n\n"
            f"Введите количество в граммах:",
            parse_mode="HTML"
        )
        await state.set_state(LoggingStates.logging_food_amount)

@dp.message(LoggingStates.logging_food_amount)
async def process_food_amount(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        food_name = data.get('food_name')
        text = message.text.strip().lower()
        if 'calories_per_100g' not in data:
            calories_per_100g = float(text)
            await state.update_data(calories_per_100g=calories_per_100g)
            
            await message.answer(
                f"Калорийность сохранена: {calories_per_100g} ккал/100г\n\n"
                f"Теперь введите количество в граммах:"
            )
            return
        grams = float(text)
        
        if grams <= 0:
            await message.answer("Количество должно быть положительным числом")
            return
        
        calories_per_100g = data.get('calories_per_100g')
        total_calories = (calories_per_100g / 100) * grams
        success = await db_processor.log_calories(
            message.from_user.full_name, 
            total_calories, 
            food_name
        )
        
        if success:
            # Получаем обновленный профиль
            profile = await db_processor.get_user_profile(message.from_user.id)
            
            if profile:
                # Рассчитываем прогресс
                calorie_goal = profile.get('calorie_goal', 1) or 1
                logged_calories = profile.get('logged_calories', 0)
                calorie_progress = min(int((logged_calories / calorie_goal) * 100), 100) if calorie_goal > 0 else 0
                
                calorie_bar = "█" * (calorie_progress // 10) + "░" * (10 - (calorie_progress // 10))
                
                # Рассчитываем сколько калорий осталось
                calories_left = max(calorie_goal - logged_calories, 0)
                
                # Формируем ответ
                response = (
                    f"<b>{food_name.capitalize()}</b>\n"
                    f"Количество: {grams}г\n"
                    f"Калорийность: {calories_per_100g} ккал/100г\n"
                    f"Итого: <b>{total_calories:.0f} ккал</b>\n\n"
                    f"<b>Прогресс по калориям:</b>\n"
                    f"{logged_calories:.0f}/{calorie_goal} ккал\n"
                    f"{calorie_bar} {calorie_progress}%\n"
                    f"Осталось: {calories_left:.0f} ккал")
                if calorie_progress >= 100:
                    response += "\n<b>Достигнута дневная норма калорий!</b>"
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Профиль", callback_data="profile")],
                        [InlineKeyboardButton(text="Активность", callback_data="activity_log")]
                    ])
                else:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Профиль", callback_data="profile")],
                        [
                            InlineKeyboardButton(text=" Добавить еду", callback_data="food_log"),
                            InlineKeyboardButton(text=" Добавить воду", callback_data="water_log")
                        ]
                    ])
                
                await message.answer(response, parse_mode="HTML", reply_markup=keyboard)
            else:
                await message.answer(
                    f"Добавлено {total_calories:.0f} ккал из {food_name}"
                )
        else:
            await message.answer(" Ошибка при сохранении данных")
        
        await state.clear()
        
    except ValueError:
        await message.answer(" Пожалуйста, введите число")


@dp.callback_query(F.data == "activity_log")
async def start_log_activity(callback: CallbackQuery, state: FSMContext):
    """Начать логирование активности"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=" Бег", callback_data="activity_бег"),
            InlineKeyboardButton(text=" Ходьба", callback_data="activity_ходьба")
        ],
        [
            InlineKeyboardButton(text=" Плавание", callback_data="activity_плавание"),
            InlineKeyboardButton(text=" Тренировка", callback_data="activity_силовая тренировка")
        ],
        [
            InlineKeyboardButton(text=" Велосипед", callback_data="activity_велосипед"),
            InlineKeyboardButton(text=" Йога", callback_data="activity_йога")
        ],
        [
            InlineKeyboardButton(text=" Футбол", callback_data="activity_футбол"),
            InlineKeyboardButton(text=" Теннис", callback_data="activity_теннис")
        ],
        [InlineKeyboardButton(text=" Другая активность", callback_data="activity_custom")]
    ])
    
    await callback.message.answer(
        "🏃 <b>Выберите тип активности:</b>\n\n"
        "<i>Нажмите на одну из кнопок или введите свою активность</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(LoggingStates.logging_activity_type)
    await callback.answer()

# Обработчик для выбора типа активности из кнопок
@dp.callback_query(LoggingStates.logging_activity_type, F.data.startswith("activity_"))
async def select_activity_type(callback: CallbackQuery, state: FSMContext):
    activity_type = callback.data.replace("activity_", "")
    
    if activity_type == "custom":
        await callback.message.answer(
            " <b>Введите название вашей активности:</b>\n\n"
            "<i>Например: бокс, танцы, скалолазание, баскетбол</i>",
            parse_mode="HTML"
        )
        await state.set_state(LoggingStates.logging_activity_type)
    else:
        # Сохраняем тип активности
        await state.update_data(activity_type=activity_type)
        
        await callback.message.answer(
            f" <b>{activity_type.capitalize()}</b>\n\n"
            f"Введите продолжительность активности в <b>минутах</b>:",
            parse_mode="HTML"
        )
        await state.set_state(LoggingStates.logging_activity_duration)
    
    await callback.answer()

# Обработчик для ввода типа активности вручную
@dp.message(LoggingStates.logging_activity_type)
async def process_activity_type(message: Message, state: FSMContext):
    activity_type = message.text.strip()
    
    if len(activity_type) < 2:
        await message.answer(" Название активности должно быть не менее 2 символов")
        return
    
    # Сохраняем тип активности
    await state.update_data(activity_type=activity_type)
    
    await message.answer(
        f" <b>{activity_type.capitalize()}</b>\n\n"
        f"Введите продолжительность активности в <b>минутах</b>:",
        parse_mode="HTML"
    )
    await state.set_state(LoggingStates.logging_activity_duration)

# Обработчик для ввода продолжительности активности
@dp.message(LoggingStates.logging_activity_duration)
async def process_activity_duration(message: Message, state: FSMContext):
    try:
        duration_minutes = int(message.text)
        
        if duration_minutes <= 0:
            await message.answer(" Продолжительность должна быть положительным числом")
            return
        
        if duration_minutes > 600: 
            await message.answer("Продолжительность не может превышать 600 минут (10 часов)")
            return
        data = await state.get_data()
        activity_type = data.get('activity_type')
        
        if not activity_type:
            await message.answer("Ошибка: тип активности не найден")
            await state.clear()
            return
    
        result = await db_processor.log_activity(
            message.from_user.first_name, 
            activity_type, 
            duration_minutes
        )
        
        if result:
            calories_burned = result['calories_burned']
            
            profile = await db_processor.get_user_profile(message.from_user.id)
            
            if profile:
                today_activities = await db_processor.get_today_activities(message.from_user.id)
                activities_text = ""
                total_burned_today = 0
                
                for activity in today_activities:
                    activities_text += (
                        f"• {activity['activity_type'].capitalize()}: "
                        f"{activity['duration_minutes']} мин, "
                        f"{activity['calories_burned']} ккал\n"
                    )
                    total_burned_today += activity['calories_burned']
                
            
                logged_calories = profile.get('logged_calories', 0)
                burned_calories = profile.get('burned_calories', 0)
                net_calories = logged_calories - burned_calories
                
                
                calorie_goal = profile.get('calorie_goal', 1) or 1
                calorie_progress = min(int((logged_calories / calorie_goal) * 100), 100) if calorie_goal > 0 else 0
                calorie_bar = "█" * (calorie_progress // 10) + "░" * (10 - (calorie_progress // 10))
                
                if net_calories > 0:
                    calorie_status = f" <b>Профицит:</b> +{net_calories} ккал"
                elif net_calories < 0:
                    calorie_status = f" <b>Дефицит:</b> {net_calories} ккал"
                else:
                    calorie_status = " <b>Баланс:</b> 0 ккал"
                
                response = (
                    f"<b>{activity_type.capitalize()}</b>\n"
                    f"Продолжительность: {duration_minutes} мин\n"
                    f"Сожжено калорий: <b>{calories_burned} ккал</b>\n\n"
                    f"<b>Сожжено сегодня:</b> {burned_calories} ккал\n\n"
                )
                
                if activities_text:
                    response += f"<b>Сегодняшние активности:</b>\n{activities_text}\n"
                
                response += (
                    f" <b>Калорийный баланс:</b>\n"
                    f"Потреблено: {logged_calories} ккал\n"
                    f"Сожжено: {burned_calories} ккал\n"
                    f"{calorie_status}\n\n"
                    f"{calorie_bar} {calorie_progress}%\n"
                )
                
                # Клавиатура с дополнительными опциями
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text=" Профиль", callback_data="profile"),
                        InlineKeyboardButton(text=" Статистика активности", callback_data="activity_stats")
                    ],
                    [
                        InlineKeyboardButton(text=" Добавить активность", callback_data="activity_log"),
                        InlineKeyboardButton(text=" Добавить еду", callback_data="food_log")
                    ]
                ])
                
                await message.answer(response, parse_mode="HTML", reply_markup=keyboard)
            else:
                await message.answer(
                    f" Активность '{activity_type}' ({duration_minutes} мин) добавлена.\n"
                    f"Сожжено: {calories_burned} ккал"
                )
        else:
            await message.answer(" Ошибка при сохранении активности")
        
        await state.clear()
        
    except ValueError:
        await message.answer(" Пожалуйста, введите число (минуты)")





async def get_profile(user_id):
    print("ищем по user_id")
    return await  db_processor.get_user_profile(user_id)

async def main():
    try:
        await db_processor.create_tables()
        await db_processor.clear_all_tables()

        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())