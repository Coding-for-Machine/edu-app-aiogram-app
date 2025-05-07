import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import requests
from decouple import config

TOKEN = config("TOKEN")
API_URL_SEND = config("API_URL_SEND")  # /send-code/ uchun URL
API_URL_VERIFY = config("API_URL_VERIFY")  # /verify-code/ uchun URL
API_URL = config("API_URL")
dp = Dispatcher()

# Har bir user uchun vaqtincha ma'lumot saqlash
user_temp_data = {}

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    phone_button = KeyboardButton(text='Telefon raqam yuborish 📱', request_contact=True)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[phone_button]],
        resize_keyboard=True, 
        one_time_keyboard=True
    )

    await message.answer(
        f"Assalomu alaykum! Telefon raqamingizni yuboring: {html.bold(message.from_user.full_name)}",
        reply_markup=keyboard
    )

@dp.message(F.contact | (F.text == "/login"))
async def handle_contact(message: Message):
    contact = message.contact
    phone_number = contact.phone_number

    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            API_URL_SEND,
            json={"phone_number": phone_number},
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            # Kod yuborilgan, endi foydalanuvchidan kod so‘raymiz
            user_temp_data[message.from_user.id] = phone_number
            await message.answer(
                    f"✅ Kod yuborildi! Endi kodni kiriting:\n`{dict(response.json())['code']}`", 
                    parse_mode="Markdown"
                )
        else:
            error_msg = response.json().get('detail', 'Noma\'lum xato')
            await message.answer(f"⚠️ Xato: {error_msg}")

    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {str(e)}")
        await message.answer("🔌 Server bilan aloqada muammo. Iltimos, keyinroq urinib ko'ring.")

@dp.message()
async def handle_code(message: Message):
    if message.from_user.id in user_temp_data:
        phone_number = user_temp_data[message.from_user.id]
        code = message.text.strip()

        try:
            # Session ID ni olish uchun alohida endpoint
            session_response = requests.get(
                API_URL_SEND,
                params={"phone_number": phone_number},
                timeout=5
            )
            
            if session_response.status_code != 200:
                await message.answer("⚠️ Session topilmadi. Qayta urinib ko'ring /start")
                return

            session_id = session_response.json().get('session_id')
            
            # OTP tekshirish
            verify_response = requests.post(
                f"{API_URL}/verify-code/",
                json={
                    "session_id": session_id,
                    "code": code
                },
                timeout=10
            )

            if verify_response.status_code == 200:
                data = verify_response.json()
                await message.answer("✅ Muvaffaqiyatli tasdiqlandi!")
                del user_temp_data[message.from_user.id]
            else:
                error = verify_response.json().get('detail', 'Xato')
                await message.answer(f"⚠️ {error}")

        except Exception as e:
            logging.error(f"Error: {str(e)}")
            await message.answer("🔌 Server xatosi. Iltimos, keyinroq urinib ko'ring.")
async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
