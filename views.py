import datetime

from shedule_parser import Schedule


def get_num_emoji(num: str) -> str:
    return {
        '1': '1⃣',
        '2': '2⃣',
        '3': '3⃣',
        '4': '4⃣',
        '5': '5⃣'
    }.get(num)


def get_day_name(date: str) -> str:
    d = datetime.datetime.strptime(date, '%Y-%m-%d')
    return {
        1: "Понедельник",
        2: "Вторник",
        3: "Среда",
        4: "Четверг",
        5: "Пятница",
        6: "Суббота",
        7: "Воскресенье"
    }.get(d.isoweekday())


def message_schedule_week(schedule: Schedule) -> dict[str, str]:

    days = {}
    for date, day in schedule.TIMETABLE.items():
        m = f'🔴 {date} {get_day_name(date)}\n\n'

        if day.CHILD.get('FULL') is not None:
            for _, full in day.CHILD.get('FULL').CHILD.items():
                m += f"<b>[{full.VIDDISC.SHORT}]</b> {full.NAME}\n"

        for pair_id in schedule.PAIR:

            if day.CHILD.get(pair_id) is None:
                continue

            m += f'{get_num_emoji(pair_id)} <b>{schedule.PAIR[pair_id].NAME}</b>\n'

            time_ = day.CHILD.get(pair_id)
            for _, pair in time_.CHILD.items():
                m += f'<b>[{pair.VIDDISC.SHORT}]  </b>'

                if pair.SUBGROUP:
                    m += f'<b>[{pair.SUBGROUP} пг]</b> [ауд. <b>{schedule.AUD.get(pair.IDAUD).NAME}</b>] {pair.NAME} '

                m += f'{schedule.TEACHER.get(pair.IDTEACHER).SHORTNAME}'
                m += '\n'

        m += '\n'
        days[date] = m

    return days
