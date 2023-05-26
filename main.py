import asyncio
import psycopg2
import requests
import json
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
import os

bot_token = os.getenv('API_TOKEN')

API_KEY = 'API'
DB_NAME = 'Name'
DB_USER = 'postgres'
DB_PASSWORD = 'PASSWORD'
DB_HOST = 'localhost'

class Form(StatesGroup):
    ticker = State()

bot = Bot(token=bot_token)
dp = Dispatcher(bot, storage=MemoryStorage())

# Создаем подключение к базе данных
conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)
cur = conn.cursor()


@dp.message_handler(Command('start'))
async def cmd_start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Добавить ценную бумагу"))
    keyboard.add(types.KeyboardButton("Показатели отслеживаемых ценных бумаг"))
    await message.answer("Выберите команду:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text.lower() == 'добавить ценную бумагу', state=Form.ticker)
async def process_add_ticker_intercepted(message: types.Message, state: FSMContext):
    await state.finish()
    await process_add_ticker(message)

@dp.message_handler(lambda message: message.text.lower() == 'добавить ценную бумагу')
async def process_add_ticker(message: types.Message):
    await Form.ticker.set()
    await message.answer("Введите тикер ценной бумаги:")

@dp.message_handler(lambda message: message.text.lower() == 'показатели отслеживаемых ценных бумаг', state=Form.ticker)
async def process_show_profits_intercepted(message: types.Message, state: FSMContext):
    await state.finish()
    await process_show_profits(message)

@dp.message_handler(state=Form.ticker)
async def process_ticker(message: types.Message, state: FSMContext):
    ticker = message.text.upper()
    cur.execute("INSERT INTO stocks (user_id, ticker) VALUES (%s, %s)", (message.from_user.id, ticker))
    conn.commit()
    await state.finish()
    await message.answer(f"Ценная бумага {ticker} добавлена к отслеживаемым")

@dp.message_handler(lambda message: message.text.lower() == 'показатели отслеживаемых ценных бумаг')
async def process_show_profits(message: types.Message):
    cur.execute("SELECT ticker, profit FROM stocks WHERE user_id = %s", (message.from_user.id,))
    rows = cur.fetchall()
    if not rows:
        await message.answer("У вас нет отслеживаемых ценных бумаг")
    else:
        response = ""
        max = -100000000
        name = ""
        for row in rows:
            ticker, profit = row
            if profit is not None:
                if profit > max:
                    max = profit
                    name = ticker
        await message.answer(name + " " + str(max))

async def periodic_task():
    while True:
        cur.execute("SELECT id, ticker FROM stocks")  # обновляем профит для всех акций
        rows = cur.fetchall()
        for row in rows:
            id, ticker = row
            response = requests.get(f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={ticker}&apikey={API_KEY}')
            data = json.loads(response.text)
            if 'Time Series (Daily)' not in data:
                continue
            prices = list(data['Time Series (Daily)'].values())[:30]
            if len(prices) < 30:
                continue
            start_price = float(prices[-1]['1. open'])
            end_price = float(prices[0]['4. close'])
            profit = ((end_price - start_price) / start_price) * 100
            cur.execute("UPDATE stocks SET profit = %s WHERE id = %s", (profit, id))
        conn.commit()
        await asyncio.sleep(24 * 60 * 60)

if __name__ == '__main__':
    from aiogram import executor
    loop = asyncio.get_event_loop()
    loop.create_task(periodic_task())
    executor.start_polling(dp, loop=loop, skip_updates=True)
