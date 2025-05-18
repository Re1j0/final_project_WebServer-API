import asyncio
import logging
import random
import sqlite3
from datetime import datetime

import requests
from aiogram import Bot, Dispatcher, types
from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import api_token, link
from functions import create_table, format_fonts_count

BOT_TOKEN = api_token  # @vladimirlms_bot

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

qst_router = Router()
create_table()

dp = Dispatcher()

bot = Bot(token=BOT_TOKEN)


@dp.message(Command('start'))
async def process_start_command(message: types.Message):
    connect = sqlite3.connect('base/base.db')
    cursor = connect.cursor()
    result = cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (message.from_user.id,)).fetchone()

    if result is None:
        number = random.randint(0, 6)
        way = random.randint(1, 3)
        variant = ['1', '2', '3', '4', '5', '6', '7']

        if way == 2:
            variant = ['один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь']
        elif way == 3:
            variant = ['🐴', '🐮', '🐶', '🐱', '🦈', '⛄️', '🐷']

        reply = await bot.send_message(message.from_user.id, f'<b>Проверка на робота 🤖\n\n'
                                                             f'Нажмите на {variant[number]}</b>', parse_mode='HTML')
        correct = f'{reply.message_id}_robottest_correct'
        incorrect = f'{reply.message_id}_robottest_incorrect'

        inline_kb_list = []
        for i, j in enumerate(variant):
            if int(i) == int(number):
                inline_kb_list.append([InlineKeyboardButton(text=j, callback_data=correct)])
            else:
                inline_kb_list.append([InlineKeyboardButton(text=j, callback_data=incorrect)])
        markup = InlineKeyboardMarkup(inline_keyboard=inline_kb_list)
        await bot.edit_message_reply_markup(chat_id=message.from_user.id, message_id=reply.message_id,
                                            reply_markup=markup)
    else:
        msg = await bot.send_photo(chat_id=message.from_user.id, photo=types.FSInputFile('pictures/menu_picture.png'),
                                   caption='<b>Добро пожаловать!\n\n'
                                           'Выберите действие ниже:</b>',
                                   parse_mode='HTML')
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🔍 Поиск Шрифтов', callback_data=f'{msg.message_id}_searchfont')]])
        await bot.edit_message_reply_markup(chat_id=message.from_user.id, message_id=msg.message_id,
                                            reply_markup=markup)

    connect.close()


@dp.callback_query(F.data.contains("robottest"))
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
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='Перейти в меню', callback_data=f'{message_id}_menu')]])
        await bot.edit_message_text(
            text='<b>✅ Вы прошли проверку на робота, теперь вы можете перейти в меню:</b>',
            chat_id=call.message.chat.id,
            message_id=int(message_id),
            reply_markup=markup,
            parse_mode='HTML')
    if answer == 'incorrect':
        message_id = int(call.data.split('_')[0])
        date = str(datetime.now()).split('.')[0]
        connect = sqlite3.connect('base/base.db')
        cursor = connect.cursor()
        cursor.execute('INSERT INTO users (user_id, register, ban) VALUES (?, ?, 1)', (call.from_user.id, date))
        connect.close()
        markup = InlineKeyboardMarkup(inline_keyboard=[])
        await bot.edit_message_text(
            text='<b>❌ Вы не прошли проверку на робота, система заблокировала вас.</b>',
            chat_id=call.message.chat.id,
            message_id=int(message_id),
            reply_markup=markup,
            parse_mode='HTML')


@dp.callback_query(F.data.contains("searchfont"))
async def findfont(call: types.CallbackQuery):
    delete = int(call.data.split('_')[0])
    count_font = int(requests.get(f'{link}/api/font-count').json()['count'])
    await bot.delete_message(call.from_user.id, delete)
    msg = await bot.send_message(call.from_user.id, f'<b>🔎 Поиск Шрифтов\n'
                                                    f'В нашей базе {format_fonts_count(count_font)}.\n\n'
                                                    f'Для продолжения нажмите кнопку ниже:</b>', parse_mode='HTML')
    kb = list()
    kb.append([InlineKeyboardButton(text='🔍 Найти Шрифт по названию', callback_data=f'{msg.message_id}_findfont')])
    kb.append([InlineKeyboardButton(text='⏹️ Открыть на сайте', url=f'{link}/fonts')])
    kb.append([InlineKeyboardButton(text='◀️ Вернуться в меню', callback_data=f'{msg.message_id}_menu')])
    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    await bot.edit_message_reply_markup(chat_id=call.from_user.id, message_id=msg.message_id, reply_markup=markup)


@dp.callback_query(F.data.contains("menu"))
async def menu(call: types.CallbackQuery):
    try:
        delete = int(call.data.split('_')[0])
        await bot.delete_message(call.from_user.id, delete)
    except Exception as e:
        print(e)
        pass
    msg = await bot.send_photo(chat_id=call.from_user.id, photo=types.FSInputFile('pictures/menu_picture.png'),
                               caption='<b>Добро пожаловать!\n\n'
                                       'Выберите действие ниже:</b>',
                               parse_mode='HTML')
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔍 Поиск Шрифтов', callback_data=f'{msg.message_id}_searchfont')]])
    await bot.edit_message_reply_markup(chat_id=call.from_user.id, message_id=msg.message_id,
                                        reply_markup=markup)


class FindStates(StatesGroup):
    fontname = State()


@dp.callback_query(F.data.contains("findfont"))
async def search(call: types.CallbackQuery, state: FSMContext):
    delete = int(call.data.split('_')[0])
    await bot.delete_message(call.from_user.id, delete)
    markup = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text='◀️ Вернуться в меню')]],
                                       resize_keyboard=True)
    await bot.send_message(call.from_user.id, f'<b>Введите название шрифта:</b>', reply_markup=markup,
                           parse_mode='HTML')
    await state.set_state(FindStates.fontname)


@dp.message(FindStates.fontname)
async def acceptdata(message: Message, state: FSMContext) -> None:
    await state.update_data(fontname=message.text)
    await state.clear()

    msg = await bot.send_message(message.from_user.id, '<b>Загружаю...</b>', reply_markup=types.ReplyKeyboardRemove(),
                                 parse_mode='HTML')
    await asyncio.sleep(3)
    await bot.delete_message(message.from_user.id, msg.message_id)
    if message.text == '◀️ Вернуться в меню':
        msg = await bot.send_photo(chat_id=message.from_user.id, photo=types.FSInputFile('pictures/menu_picture.png'),
                                   caption='<b>Добро пожаловать!\n\n'
                                           'Выберите действие ниже:</b>',
                                   parse_mode='HTML')
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🔍 Поиск Шрифтов', callback_data=f'{msg.message_id}_searchfont')]])
        await bot.edit_message_reply_markup(chat_id=message.from_user.id, message_id=msg.message_id,
                                            reply_markup=markup)
    else:
        try:
            data = requests.get(f'{link}/api/search-font?query={message.text}').json()
            count = int(data['count'])
            if count == 0:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='◀️ Вернуться в меню', callback_data=f'menu')]])
                await message.reply('<b>⛔ По вашему запросу не найдено шрифтов.</b>', reply_markup=markup,
                                    parse_mode='HTML')
            else:
                buttons = list()
                buttons.append([InlineKeyboardButton(text='↖️ Открыть на сайте', url=data['search_link'])])
                buttons.append([InlineKeyboardButton(text='◀️ Вернуться в меню', callback_data='menu')])
                markup = InlineKeyboardMarkup(inline_keyboard=buttons)
                await bot.send_message(message.from_user.id, f'<b>Найденные Шрифты: {count}\n\n'
                                                             f'Перейдите по ссылке ниже для открытия шрифтов.</b>',
                                       reply_markup=markup, parse_mode='HTML')
        except Exception as e:
            print(e)
            await message.reply('<b>❌ Неизвестная ошибка. Введите текст еще раз.</b>', parse_mode='HTML')
            await state.set_state(FindStates.fontname)


if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot))