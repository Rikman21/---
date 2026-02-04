import asyncio
import logging
import json
import urllib.parse
import time
import os
from aiohttp import web
from openpyxl import Workbook, load_workbook
from io import BytesIO

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

import database 

TOKEN = "8451254918:AAHDJ8yIwQ44Stn7vT_s1mmxLDVYwfXUuJU"
# Ссылка на сайт остается прежней
WEB_APP_URL = "https://rikman21.github.io/Gorbushka/?v=2" 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- API СЕРВЕР (ТЕПЕРЬ УМНЫЙ) ---
async def health_check(request):
    return web.Response(text="Alive")

async def get_offers_api(request):
    # Эта функция отправляет цены сайту, когда он просит
    offers = database.get_all_offers_for_web()
    return web.json_response(offers, headers={
        "Access-Control-Allow-Origin": "*",  # Разрешаем доступ с GitHub Pages
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    })

async def start_server():
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    # Два маршрута: проверка жизни и выдача товаров
    app.router.add_get('/', health_check)
    app.router.add_get('/api/offers', get_offers_api)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- EXCEL ---
def generate_excel_template():
    products = database.get_catalog_for_excel()
    wb = Workbook()
    ws = wb.active
    ws.title = "Прайс-лист"
    headers = ["SKU (Не менять!)", "Модель", "Память", "Цвет", "Сим", "ВАША ЦЕНА (Рубли)"]
    ws.append(headers)
    for p in products:
        row = list(p) + [""] 
        ws.append(row)
    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)
    return file_stream.read()

# --- HANDLERS ---
@dp.message(F.document)
async def handle_document(message: types.Message):
    if not message.document.file_name.endswith('.xlsx'):
        return await message.answer("❌ Это не Excel. Пришлите файл .xlsx")

    user_id = message.from_user.id
    username = message.from_user.username or "Продавец"
    wait_msg = await message.answer("⏳ Обрабатываю прайс...")

    try:
        bot_file = await bot.get_file(message.document.file_id)
        file_data = await bot.download_file(bot_file.file_path)
        wb = load_workbook(file_data)
        ws = wb.active
        prices_to_update = []
        
        for row in ws.iter_rows(min_row=2, values_only=True):
            sku = row[0]
            price_raw = row[5]
            price = None
            if price_raw:
                try:
                    price = int(str(price_raw).replace(" ", "").replace("₽", ""))
                except:
                    price = None
            if sku:
                prices_to_update.append((sku, price))
        
        updated_count = database.update_prices_from_excel(user_id, username, prices_to_update)
        await wait_msg.edit_text(f"✅ **Прайс обновлен!**\n\nТоваров в продаже: {updated_count}\n\nТеперь просто откройте WebApp, ссылка обновлять не нужно.")
        
    except Exception as e:
        logging.error(e)
        await wait_msg.edit_text("❌ Ошибка. Проверьте формат файла.")

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    
    # БОЛЬШЕ НЕ ПЕРЕДАЕМ ДАННЫЕ В ССЫЛКЕ
    # Ссылка теперь короткая и вечная
    full_url = f"{WEB_APP_URL}?uid={user_id}"

    kb = [[KeyboardButton(text="📱 ОТКРЫТЬ МАРКЕТ", web_app=WebAppInfo(url=full_url))]]
    await message.answer("👋 Горбушка Онлайн v2.0 (Live)", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.web_app_data)
async def handle_webapp(message: types.Message):
    data = message.web_app_data.data
    user_id = message.chat.id
    username = message.from_user.username or "Клиент"

    if data == "REQ_TEMPLATE":
        file_bytes = generate_excel_template()
        document = BufferedInputFile(file_bytes, filename="Gorbushka_Price_Template.xlsx")
        await message.answer_document(document, caption="📉 **Шаблон для цен**")
        return

    if data.startswith("DELETE_OFFER"):
        sku = data.split("|")[1]
        database.delete_offer_by_sku(user_id, sku)
        # Просто подтверждаем, обновлять ссылку не надо
        return

    if data.startswith("REQ_BUY"):
        parts = data.split("|")
        seller_id = int(parts[1])
        product_name = parts[3]
        price = parts[4]
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ В наличии", callback_data=f"confirm_{user_id}")],
            [InlineKeyboardButton(text="❌ Нет", callback_data=f"reject_{seller_id}")]
        ])
        try:
            await bot.send_message(seller_id, f"🔔 <b>ЗАКАЗ!</b>\n\n📦 {product_name}\n💰 {price}р\n👤 @{username}", reply_markup=kb, parse_mode="HTML")
            await message.answer("⏳ Запрос отправлен продавцу...")
        except:
            await message.answer("Продавец не найден.")

    elif data.startswith("NEW_PRICE"):
        # Формат: NEW_PRICE|Имя товара|Новая цена
        parts = data.split("|")
        if len(parts) < 3:
            await message.answer("Не удалось разобрать данные для изменения цены.")
            return

        product_name = parts[1]
        price_raw = parts[2]

        try:
            new_price = int(str(price_raw).replace(" ", "").replace("₽", ""))
        except ValueError:
            await message.answer("Цена указана неверно.")
            return

        affected = database.update_price_from_web(user_id, product_name, new_price)
        if affected > 0:
            await message.answer(f"✅ Цена для «{product_name}» обновлена на {new_price} ₽.")
        else:
            await message.answer("Товар не найден в вашей базе. Обновите прайс через Excel, а затем попробуйте снова.")

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_order(callback: types.CallbackQuery):
    buyer_id = int(callback.data.split("_")[1])
    await callback.message.edit_text(f"✅ Подтверждено!", reply_markup=None)
    await bot.send_message(buyer_id, f"🎉 Продавец подтвердил!\nКонтакт: @{callback.from_user.username}")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_order(callback: types.CallbackQuery):
    await callback.message.edit_text(f"🚫 Отказ.", reply_markup=None)

async def main():
    database.init_db()
    await start_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

