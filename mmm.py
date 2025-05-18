import random
import sqlite3
import time
from datetime import datetime

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from config import api_token, link
from functions import format_fonts_count, create_table

bot = Bot(token=api_token, parse_mode='HTML')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

create_table()


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    connect = sqlite3.connect('base/base.db')
    cursor = connect.cursor()
    result = cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (message.from_user.id,)).fetchone()
    if result is None:
        number = random.randint(1, 6)
        way = random.randint(1, 3)
        variant = ['1', '2', '3', '4', '5', '6', '7']
        if way == 2:
            variant = ['один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь']
        if way == 3:
            variant = ['🐴', '🐮', '🐶', '🐱', '🦈', '⛄', '🐷']

        reply = await bot.send_message(message.from_user.id, f'<b>Проверка на робота 🤖\n\n'
                                                             f'Нажмите на {variant[number]}</b>')
        correct = f'{reply.message_id}_robottest_correct'
        incorrect = f'{reply.message_id}_robottest_incorrect'
        markup = InlineKeyboardMarkup()
        for i, j in enumerate(variant):
            if int(i) == int(number):
                markup.add(InlineKeyboardButton(text=f'{variant[number]}', callback_data=correct))
            else:
                markup.add(InlineKeyboardButton(text=j, callback_data=incorrect))
        await bot.edit_message_reply_markup(message.from_user.id, reply.message_id, reply_markup=markup)
    else:
        with open('pictures/menu_picture.png', 'rb') as photo:
            markup = InlineKeyboardMarkup()
            msg = await bot.send_photo(message.from_user.id, photo, '<b>Добро пожаловать!\n\n'
                                                                    'Выберите действие ниже:</b>')
            markup.add(InlineKeyboardButton(text='🔍 Поиск Шрифтов', callback_data=f'{msg.message_id}_searchfont'))
            await bot.edit_message_reply_markup(message.from_user.id, msg.message_id, reply_markup=markup)
    connect.close()


@dp.callback_query_handler(lambda call: 'robottest' in call.data)
async def robottest(call: types.CallbackQuery):
    answer = call.data.split('_')[2]
    if answer == 'correct':
        message_id = call.data.split('_')[0]
        date = str(str(datetime.now()).split('.')[0])
        connect = sqlite3.connect('base/base.db')
        cursor = connect.cursor()
        cursor.execute('INSERT INTO users (user_id, register) VALUES (?, ?)', (call.from_user.id, date))
        connect.commit()
        connect.close()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Перейти в меню', callback_data=f'{message_id}_menu'))
        await bot.edit_message_text('<b>✅ Вы прошли проверку на робота, теперь вы можете перейти в меню:</b>',
                                    call.from_user.id, message_id)
        await bot.edit_message_reply_markup(call.from_user.id, message_id,
                                            reply_markup=markup)
    if answer == 'incorrect':
        message_id = call.data.split('_')[0]
        date = str(datetime.now()).split('.')[0]
        connect = sqlite3.connect('base/base.db')
        cursor = connect.cursor()
        cursor.execute('INSERT INTO users (user_id, register, ban) VALUES (?, ?, 1)', (call.from_user.id, date))
        connect.close()
        await bot.delete_message(call.from_user.id, message_id)
        await bot.edit_message_text('<b>❌ Вы не прошли проверку на робота, система заблокировала вас.</b>',
                                    call.from_user.id, message_id)
        await bot.edit_message_reply_markup(call.from_user.id, message_id,
                                            reply_markup=markup)


@dp.callback_query_handler(lambda call: 'menu' in call.data)
async def menu(call: types.CallbackQuery):
    with open('pictures/menu_picture.png', 'rb') as photo:
        try:
            delete = int(call.data.split('_')[0])
            await bot.delete_message(call.from_user.id, delete)
        except:
            pass
        markup = InlineKeyboardMarkup()
        msg = await bot.send_photo(call.from_user.id, photo, '<b>Добро пожаловать!\n\n'
                                                             'Выберите действие ниже:</b>')
        markup.add(InlineKeyboardButton(text='🔍 Поиск Шрифтов', callback_data=f'{msg.message_id}_searchfont'))
        await bot.edit_message_reply_markup(call.from_user.id, msg.message_id, reply_markup=markup)


@dp.callback_query_handler(lambda call: 'searchfont' in call.data)
async def searchfont(call: types.CallbackQuery):
    delete = int(call.data.split('_')[0])
    count_font = int(requests.get(f'{link}/api/font-count').json()['count'])
    await bot.delete_message(call.from_user.id, delete)
    msg = await bot.send_message(call.from_user.id, f'<b>🔎 Поиск Шрифтов\n'
                                                    f'В нашей базе {format_fonts_count(count_font)}.\n\n'
                                                    f'Для продолжения нажмите кнопку ниже:</b>')
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text='🔍 Найти Шрифт по названию', callback_data=f'{msg.message_id}_findfont'))
    markup.add(InlineKeyboardButton(text='⏹️ Открыть на сайте', url=f'{link}/fonts'))
    markup.add(InlineKeyboardButton(text='◀️ Вернуться в меню', callback_data=f'{msg.message_id}_menu'))
    await bot.edit_message_reply_markup(call.from_user.id, msg.message_id, reply_markup=markup)


class FindStates(StatesGroup):
    fontname = State()


@dp.callback_query_handler(lambda call: 'findfont' in call.data)
async def findfont(call: types.CallbackQuery):
    delete = int(call.data.split('_')[0])
    await bot.delete_message(call.from_user.id, delete)
    markup = ReplyKeyboardMarkup(resize_keyboard=True, b)
    markup.add(KeyboardButton('◀️ Вернуться в меню'))
    await bot.send_message(call.from_user.id, f'<b>Введите название шрифта:</b>', reply_markup=markup)
    await FindStates.fontname.set()



@dp.message_handler(state=FindStates.fontname)
async def namefontstate(message: types.Message, state: FSMContext):
    await state.finish()
    msg = await bot.send_message(message.from_user.id, '<b>Загружаю...</b>', reply_markup=types.ReplyKeyboardRemove())
    time.sleep(3)
    await bot.delete_message(message.from_user.id, msg.message_id)
    if message.text == '◀️ Вернуться в меню':
        with open('pictures/menu_picture.png', 'rb') as photo:
            markup = InlineKeyboardMarkup()
            msg = await bot.send_photo(message.from_user.id, photo, '<b>Добро пожаловать!\n\n'
                                                                    'Выберите действие ниже:</b>')
            markup.add(InlineKeyboardButton(text='🔍 Поиск Шрифтов', callback_data=f'{msg.message_id}_searchfont'))
            await bot.edit_message_reply_markup(message.from_user.id, msg.message_id, reply_markup=markup)
    else:
        try:
            data = requests.get(f'{link}/api/search-font?query={message.text}').json()
            count = int(data['count'])
            if count == 0:
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(text='◀️ Вернуться в меню', callback_data='menu'))
                await message.reply('<b>⛔ По вашему запросу не найдено шрифтов.</b>', reply_markup=markup)
            else:
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(text='↖️ Открыть на сайте', url=data['search_link']))
                markup.add(InlineKeyboardButton(text='◀️ Вернуться в меню', callback_data='menu'))
                await bot.send_message(message.from_user.id, f'<b>Найденные Шрифты: {count}\n\n'
                                                             f'Перейдите по ссылке нмже для открытия шрифтов.</b>',
                                       reply_markup=markup)
        except Exception as e:
            print(e)
            await message.reply('<b>❌ Неизвестная ошибка. Введите текст еще раз.</b>')
            await FindStates.fontname.set()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
