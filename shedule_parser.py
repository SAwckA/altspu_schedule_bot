import asyncio
import logging

import httpx
from pydantic import BaseModel
import redis.asyncio as red


class Aud(BaseModel):
    """ Аудитория """
    ID: str
    NAME: str


class Teacher(BaseModel):
    """ Преподаватель """
    ID: str
    NAME: str
    SHORTNAME: str


class Pair(BaseModel):
    """ Пара и время её проведения """
    ID: str
    NAME: str


class Date(BaseModel):
    """ Неделя """
    FROM: str
    TO: str


class VIDDISC(BaseModel):
    NAME: str | None
    SHORT: str | None



class TimeTablePair(BaseModel):
    """ Пара в расписании """
    ID: str | None
    NAME: str | None
    IDTEACHER: str | None
    IDAUD: str | None
    SUBGROUP: str | None
    VIDDISC: VIDDISC | None


class TimeTableChild(BaseModel):
    """ Информация о парах в текущий день """
    CHILD: dict[str, TimeTablePair] | None


class TimeTable(BaseModel):
    """ Расписание """
    CHILD: dict[str, TimeTableChild] | None


class Schedule(BaseModel):
    AUD: dict[str, Aud] | list | None
    TEACHER: dict[str, Teacher] | list | None
    PAIR: dict[str, Pair] | list | None
    DATE: Date | list | None
    TIMETABLE: dict[str, TimeTable] | None


class ScheduleParser:

    def __init__(self, cache: red.Redis = None):
        self._client = httpx.AsyncClient(
            headers={
                # 'User-Agent': 'Python/ScheduleChatBot (contacts; @sawcka)'
            }
        )
        self._cache = cache
        self.groups = {}

    def get_groups(self):
        return self.groups

    async def fetch_group_schedule(self, group_id, year, week) -> Schedule:
        logging.info(f'not found in cache; fetching group schedule: {group_id}:{year}:{week}')

        url = f'https://www.altspu.ru/api/schedule/students_schedule/?year={year}&week={week}&idgroup={group_id}'
        res = await self._client.get(url)
        return Schedule(**res.json())

    @staticmethod
    def decode_redis_index(group_id, year, week):
        return f'{group_id}:{year}:{week}'

    @staticmethod
    def encode_redis_index(index: str) -> list[str, str, str]:
        return index.split(":")

    async def get_group_schedule(self, group_id, year, week):
        if await self._cache.exists(self.decode_redis_index(group_id, year, week)):
            logging.info(f'found in cache: {group_id}:{year}:{week}')
            return Schedule.model_validate_json(
                await self._cache.get(self.decode_redis_index(group_id, year, week))
            )

        res = await self.fetch_group_schedule(group_id, year, week)
        await self._cache.set(self.decode_redis_index(group_id, year, week), res.model_dump_json())
        return res

    async def get_group_ids(self, fak, progrpod, forma, client):
        while True:
            try:
                res = await client.get(
                    f'https://www.altspu.ru/api/schedule/students_groups/?fac={fak}&npk={progrpod}&form={forma}'
                )

                if res.status_code != 200:
                    return
                for el in res.json():
                    self.groups[el.get('NAME')] = el.get('ID')
                return

            except:
                pass

    async def fetch_groups(self):
        logging.info('start fetching all groups')
        res = httpx.get('https://www.altspu.ru/api/schedule/students_tree/')
        json = res.json()
        client = httpx.AsyncClient()

        tasks = []
        for fak in json.get('FAK'):
            for forma in json.get('FORMA'):
                for progrpod in json.get('PROGRPOD'):
                    tasks.append(self.get_group_ids(fak, forma, progrpod, client))

        logging.info('group successful fetched')
        await asyncio.gather(*tasks)
