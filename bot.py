
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import BOT_TOKEN, ADMIN_ID

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

class ExchangeForm(StatesGroup):
    amount = State()
    paypal = State()
    wallet = State()
    proof = State()

def calculate_usdt(amount):
    commission = max(8, 15 - (amount // 100) * 0.5)
    received = round(amount * (1 - commission / 100), 2)
    return received, commission

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📄 Создать заявку"))
    await message.answer(
        "👋 Добро пожаловать! Здесь ты можешь обменять PayPal → USDT (TRC20).

"
        "💰 Комиссия: регрессивная 
📈 От 15% до 8%
📅 Минимум: 30$

"
        "Нажми кнопку ниже, чтобы начать.",
        reply_markup=kb
    )

@dp.message_handler(lambda m: m.text == "📄 Создать заявку")
async def create_request(message: types.Message):
    await message.answer("💵 Введи сумму в долларах, которую хочешь обменять:")
    await ExchangeForm.amount.set()

@dp.message_handler(state=ExchangeForm.amount)
async def get_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount < 30:
            return await message.answer("Минимум 30$. Введи сумму заново.")
        usdt, commission = calculate_usdt(amount)
        await state.update_data(amount=amount, usdt=usdt, commission=commission)
        await message.answer(
            f"🔢 Комиссия: {commission:.1f}%
🤑 К получению: {usdt} USDT

Введи свой PayPal e-mail:")
        await ExchangeForm.next()
    except:
        await message.answer("Некорректная сумма. Введи число.")

@dp.message_handler(state=ExchangeForm.paypal)
async def get_paypal(message: types.Message, state: FSMContext):
    await state.update_data(paypal=message.text)
    await message.answer("🦙 Введи адрес своего TRC20 кошелька:")
    await ExchangeForm.next()

@dp.message_handler(state=ExchangeForm.wallet)
async def get_wallet(message: types.Message, state: FSMContext):
    await state.update_data(wallet=message.text)
    await message.answer("📌 Пришли скриншот, подтверждающий перевод:")
    await ExchangeForm.next()

@dp.message_handler(state=ExchangeForm.proof, content_types=types.ContentTypes.ANY)
async def get_proof(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("❌ Нужно отправить фото, а не файл. Попробуй снова.")
        return
    data = await state.get_data()
    caption = (
        f"🔍 Новая заявка на обмен
"
        f"💰 Сумма: {data['amount']}$
"
        f"📅 Комиссия: {data['commission']:.1f}%
"
        f"📆 К выдаче: {data['usdt']} USDT
"
        f"📥 PayPal: {data['paypal']}
"
        f"🦙 Кошелёк: {data['wallet']}"
    )
    proof_photo = message.photo[-1].file_id
    await bot.send_photo(ADMIN_ID, proof_photo, caption=caption,
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton(f"✅ Подтвердить {message.from_user.id}"),
            KeyboardButton(f"❌ Отклонить {message.from_user.id}")
        )
    )
    await message.answer("Заявка отправлена! Ожидай подтверждения.")
    await state.finish()

@dp.message_handler(lambda m: m.text.startswith("✅ Подтвердить"))
async def confirm_exchange(message: types.Message):
    user_id = int(message.text.split()[-1])
    await bot.send_message(user_id, "✅ Перевод завершён. Спасибо за обмен!")

@dp.message_handler(lambda m: m.text.startswith("❌ Отклонить"))
async def decline_exchange(message: types.Message):
    user_id = int(message.text.split()[-1])
    await bot.send_message(user_id, "❌ Заявка отклонена. Проверь данные и попробуй ещё раз.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
