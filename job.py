import schedule
from sqlalchemy import select, delete
import requests as r
from telebot import TeleBot
from database import sync_session, UsersOrm
from config import settings

bot = TeleBot(settings.TOKEN)


def job():
    with sync_session() as session:
        query = (
            select(UsersOrm)
        )
        data = session.execute(query).scalars().all()
    for user in data:
        coin = user.coin
        price_check = user.price_check
        user_id = user.user_id
        higher = user.higher
        currency = r.get(
            f'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?symbol={coin}',
            headers={
                'X-CMC_PRO_API_KEY': settings.CMC_API_KEY
            }
        ).json()
        current_price = currency['data'][coin][0]['quote']['USD']['price']
        if current_price > price_check and higher:
            with sync_session() as session:
                query = (
                    delete(UsersOrm).
                    filter_by(id=user.id)
                )
                session.execute(query)
                session.commit()
            send_notification(chat_id=user_id, price=current_price, coin=coin)
        elif current_price < price_check and not higher:
            with sync_session() as session:
                query = (
                    delete(UsersOrm).
                    filter_by(id=user.id)
                )
                session.execute(query)
                session.commit()
            send_notification(chat_id=user_id, price=current_price, coin=coin)


schedule.every(10).seconds.do(job)


@bot.message_handler()
def send_notification(price: int, coin: str, chat_id: int):
    bot.send_message(text=f'Цена {coin} достигла {price}$', chat_id=chat_id)


while True:
    schedule.run_pending()
