#!/usr/bin/env python

# NOTICE: assumes all classes run on all weeks

import arrow
import getpass
import sys
from mq_timetable import MQeStudentSession, DAYS

TZ = 'Australia/Sydney'
ICAL_TIME_FORMAT = 'YYYYMMDDTHHmmss'

CAL_HEADER = '''\
BEGIN:VCALENDAR
VERSION:2.0
CALSCALE:GREGORIAN
'''

CAL_FOOTER = 'END:VCALENDAR'

EV_FORMAT = '''\
BEGIN:VEVENT
DTSTART;TZID={tz}:{start}
DTEND;TZID={tz}:{end}
RRULE:FREQ=WEEKLY;COUNT={rrule_count};BYDAY={rrule_day}
EXDATE;TZID={tz}:{midsem1}
EXDATE;TZID={tz}:{midsem2}
LOCATION:{where}
SUMMARY:{subject} {what}
END:VEVENT
'''

midsem_w1 = arrow.Arrow(2016, 4, 11, tzinfo=TZ)
midsem_w2 = midsem_w1.replace(weeks=+1)


def tupleise_24h(t):
    hour, minute = map(int, t.split(':'))
    return hour, minute


def make_estudent_date_arrow(date):
    day, month = date.split('-')
    month = arrow.locales.EnglishLocale().month_number(month)
    day = int(day)
    arw = arrow.now(TZ)
    return arw.replace(month=month, day=day).floor('day')


def main():
    session = MQeStudentSession()
    sys.stderr.write('Username: ')
    session.login(input(), getpass.getpass())
    timetable = session.get_timetable()
    start_end_dates = session.get_start_end_dates()
    process(timetable, start_end_dates)


def process(timetable, start_end_dates):
    start_end_arws = {}

    for key, (start, end) in start_end_dates.items():
        start_arw = make_estudent_date_arrow(start)
        end_arw = make_estudent_date_arrow(end)
        start_end_arws[key] = start_arw, end_arw

    sys.stdout.write(CAL_HEADER)

    for isoweekdaym1, day in enumerate(DAYS):
        classes = timetable[day]
        rrule_day = day[:2].upper()

        for cls in reversed(classes):
            subject = cls['subject']
            what = cls['what']
            start_h, start_m = tupleise_24h(cls['start'])
            end_h, end_m = tupleise_24h(cls['end'])
            start_date, end_date = start_end_arws[subject, what]
            rrule_count = (end_date - start_date).days // 7 + 1

            event_start = start_date.replace(hour=start_h, minute=start_m, tzinfo=TZ)
            event_end = start_date.replace(hour=end_h, minute=end_m, tzinfo=TZ)

            midsem1 = midsem_w1.replace(days=+isoweekdaym1, hour=start_h, minute=start_m)
            midsem2 = midsem_w2.replace(days=+isoweekdaym1, hour=start_h, minute=start_m)

            sys.stdout.write(EV_FORMAT.format(
                subject=subject,
                what=what,
                where=cls['where'],
                rrule_day=rrule_day,
                rrule_count=rrule_count,
                tz=TZ,
                start=event_start.format(ICAL_TIME_FORMAT),
                end=event_end.format(ICAL_TIME_FORMAT),
                midsem1=midsem1.format(ICAL_TIME_FORMAT),
                midsem2=midsem2.format(ICAL_TIME_FORMAT),
            ))

    print(CAL_FOOTER)


if __name__ == "__main__":
    main()
