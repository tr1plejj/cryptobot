import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler, \
    CallbackContext, ConversationHandler
from config import settings
from http_client import cmc_client
from database import async_session, UsersOrm

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
GET_PRICE = 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    listings = await cmc_client.get_listings()
    kb = []
    row = []
    count = 0
    for crypto in listings:
        if count <= 3:
            symbol = crypto.get('symbol')
            row.append(symbol)
            count += 1
        else:
            kb.append(row)
            row = []
            count = 1
            symbol = crypto.get('symbol')
            row.append(symbol)
    for row in kb:
        for button in range(len(row)):
            row[button] = InlineKeyboardButton(row[button], callback_data=f'info/{row[button]}')
    crypto_kb = InlineKeyboardMarkup(inline_keyboard=kb)
    if update.callback_query:
        await update.callback_query.edit_message_text('Выберите валютную пару', reply_markup=crypto_kb)
    else:
        await update.message.reply_text('Выберите валютную пару', reply_markup=crypto_kb)


async def cryptocurrency(update: Update, context: CallbackContext):
    symbol = update.callback_query.data.split('/')[1]
    currency = await cmc_client.get_currency(symbol)
    name = currency[0].get('name')
    data = currency[0].get('quote').get('USD')
    price = data.get('price')
    volume_24h = data.get('volume_24h')
    percent_change_1h = data.get('percent_change_1h')
    percent_change_24h = data.get('percent_change_24h')
    percent_change_30d = data.get('percent_change_30d')
    text = f'''
    <b>Криптовалюта: {symbol}</b>\n
    Текущая цена: {price}$\n
    Объемы продаж за 24ч: {volume_24h}\n
    Изменение цены за 1ч: {percent_change_1h}%\n
    Изменение цены за 24ч: {percent_change_24h}%\n
    Изменение цены за 30д: {percent_change_30d}%
    '''
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('Назад', callback_data='start')],
        [InlineKeyboardButton('Подробная информация', web_app=WebAppInfo(f'https://coinmarketcap.com/currencies/{name}/'))],
        [InlineKeyboardButton('Поставить уведомление', callback_data=f'subscribe/{symbol}')]
    ])
    await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode='HTML')


async def subscribe(update: Update, context: CallbackContext):
    coin = update.callback_query.data.split('/')[1]
    context.user_data['coin'] = coin
    cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton('Вернуться на главную', callback_data='start')]])
    await update.callback_query.edit_message_text('При какой цене вас уведомить?', reply_markup=cancel_kb)
    return GET_PRICE


async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        user_id = int(update.message.from_user.id)
        coin = context.user_data.get('coin')
        current_price = await cmc_client.get_currency(coin)
        current_price = current_price[0].get('quote').get('USD').get('price')
        if price > current_price:
            higher = True
        else:
            higher = False
        async with async_session() as session:
            user = UsersOrm(user_id=user_id, coin=coin, price_check=price, higher=higher)
            session.add(user)
            await session.commit()
        await update.message.reply_text(f'Отлично, вам придет уведомление, когда цена {coin} достигнет {price}$.\nЧтобы продолжить, нажмите /start')
        return ConversationHandler.END
    except:
        cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton('Вернуться на главную', callback_data='start')]])
        await update.message.reply_text('Пожалуйста, введите число', reply_markup=cancel_kb)
        return GET_PRICE


def main() -> None:
    TOKEN = settings.TOKEN
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start, 'start'))
    application.add_handler(CallbackQueryHandler(cryptocurrency, '^' + 'info/'))
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(subscribe, '^' + 'subscribe/')],
        states={
            GET_PRICE: [MessageHandler(filters.TEXT, get_price)],
        },
        fallbacks=[CommandHandler("start", start), CallbackQueryHandler(start, 'start')]
    )
    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
