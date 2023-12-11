import asyncio
import logging

import redis.asyncio as red
from pydantic.v1 import BaseSettings, BaseConfig
from telegram import Update, CallbackQuery

from handlers import TelegramHandlers
from shedule_parser import ScheduleParser, Schedule

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, InlineQueryHandler, \
    CallbackQueryHandler


class Settings(BaseSettings):
    token: str
    REDIS_HOST: str
    REDIS_PORT: int


if __name__ == '__main__':
    logging.getLogger('root').setLevel(logging.INFO)
    logging.getLogger('httpx').setLevel(logging.CRITICAL)

    cache_pool = red.ConnectionPool(host=Settings().REDIS_HOST, port=Settings().REDIS_PORT, db=0)
    cache = red.Redis(connection_pool=cache_pool)
    state_pool = red.ConnectionPool(host=Settings().REDIS_HOST, port=Settings().REDIS_PORT, db=1)
    state = red.Redis(connection_pool=state_pool)

    parser = ScheduleParser(cache)

    handlers = TelegramHandlers(state, parser)

    logging.info('building a bot')

    application = ApplicationBuilder().token(Settings().token).build()

    application.add_handler(CommandHandler('start', handlers.start))
    application.add_handler(MessageHandler(filters.Regex('\d{3,5}[а-я]{1,2}'), handlers.set_user_group))
    application.add_handler(MessageHandler(filters.Regex('Текущая неделя'), handlers.current_week_schedule))
    application.add_handler(MessageHandler(filters.Regex('Следующая неделя'), handlers.next_week))
    application.add_handler(MessageHandler(filters.Regex('Сегодня'), handlers.today_schedule))
    application.add_handler(MessageHandler(filters.Regex('Завтра'), handlers.tomorrow_schedule))
    application.add_handler(MessageHandler(filters.Regex('Группа не задана'), handlers.unset_group))
    application.add_handler(MessageHandler(filters.Regex('Конкретная неделя'), handlers.offset_schedule_menu))
    application.add_handler(MessageHandler(filters.ALL, handlers.unset_group))
    application.add_handler(CallbackQueryHandler(handlers.offset_schedule))

    asyncio.run(parser.fetch_groups())
    logging.info('reset event loop')
    asyncio.set_event_loop(asyncio.new_event_loop())

    logging.info('start polling')
    application.run_polling()
