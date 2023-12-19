import logging
from datetime import datetime, timedelta

import redis.asyncio as red
import telegram.constants
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackContext

from shedule_parser import ScheduleParser, Schedule
from views import message_schedule_week


def default_keyboard(group_id):
    return ReplyKeyboardMarkup(
        (
            (KeyboardButton(f'{group_id}'), KeyboardButton('Сегодня'), KeyboardButton('Завтра')),
            (KeyboardButton('Текущая неделя'), KeyboardButton('Следующая неделя')),
            (KeyboardButton('Конкретная неделя'),)
        ),
        resize_keyboard=True
    )


class TelegramHandlers:
    def __init__(self, state: red.Redis, parser: ScheduleParser):
        self._state = state
        self._parser = parser

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = ("Привет, Я - бот, который берёт расписание с официального сайта https://www.altspu.ru/schedule/\n"
               "и отправляет тебе в телеграмм")

        if await self._state.exists(str(update.effective_message.from_user.id)):
            logging.info(f'New user: {update.effective_message.from_user.id}')
            group = (await self._state.get(str(update.effective_message.from_user.id))).decode()
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=msg,
                                           reply_markup=default_keyboard(group))
            return

        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=msg,
                                       reply_markup=default_keyboard('Группа не задана'))

    async def unset_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Введите название группы',
                                       reply_markup=default_keyboard('Группа не задана'))

    async def set_user_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        if self._parser.get_groups().get(update.message.text) is not None:
            await self._state.set(str(update.effective_message.from_user.id), value=update.effective_message.text)
            msg = f"Я буду показывать расписание для группы: {update.message.text}"
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=msg,
                                           reply_markup=default_keyboard(update.message.text))
            return

        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Группа не найдена")

    async def week_schedule(self, date, update: Update, context: ContextTypes.DEFAULT_TYPE, day_to_send: str = None):
        if not await self._state.exists(str(update.effective_message.from_user.id)):
            await self.unset_group(update, context)
            return

        group = (await self._state.get(str(update.effective_message.from_user.id))).decode()

        schedule = await self._parser.get_group_schedule(self._parser.get_groups().get(group),
                                                         date.year,
                                                         date.week)

        source_url = (f'https://www.altspu.ru/schedule/students/s-{self._parser.get_groups().get(group)}/'
                      f'?year={date.year}'
                      f'&week={date.week}')

        msg = f"""Расписание группы: <b>{group}</b>, неделя: <b>{date.week}</b>\n<a href="{source_url}">Ссылка на источник</a>"""

        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=msg,
                                       parse_mode=telegram.constants.ParseMode.HTML)

        view_schedule = message_schedule_week(schedule)

        if day_to_send is not None:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=view_schedule.get(day_to_send, 'Сегодня пар нет :)'),
                                           parse_mode=telegram.constants.ParseMode.HTML)
            return

        for day in view_schedule.values():
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=day,
                                           parse_mode=telegram.constants.ParseMode.HTML)

    async def current_week_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        now = datetime.now().isocalendar()
        await self.week_schedule(now, update, context)

    async def next_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        now = (datetime.now() + timedelta(weeks=1)).isocalendar()
        await self.week_schedule(now, update, context)

    async def today_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        now = datetime.now()
        date = now.isocalendar()
        await self.week_schedule(date, update, context, now.strftime("%Y-%m-%d"))

    async def tomorrow_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        now = datetime.now() + timedelta(days=1)
        date = now.isocalendar()
        await self.week_schedule(date, update, context, now.strftime("%Y-%m-%d"))

    async def offset_schedule_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = "Выбери неделю из списка "
        now = datetime.now() - timedelta(days=datetime.now().weekday())
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(
                text=f'{(now + timedelta(weeks=x)).strftime("%Y-%m-%d")}',
                callback_data=x,
            ), ] for x in range(-2, 3)]
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=markup)

    async def offset_schedule(self, update: Update, context: CallbackContext):
        offset_week = int(update.callback_query.data)
        date = (datetime.now() + timedelta(weeks=offset_week)).isocalendar()
        await self.week_schedule(date, update, context)
