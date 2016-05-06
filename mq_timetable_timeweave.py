#!/usr/bin/env python
from __future__ import print_function

import arrow
import json
from mq_timetable import MQeStudentSession, LoginFailedError, DAYS, TZ, get_study_periods, get_unit_names, start_end_arrows


def tupleise_24h(t):
    hour, minute = map(int, t.split(':'))
    return hour, minute


def main():
    import sys
    from bson.objectid import ObjectId
    import save
    import config

    assert len(sys.argv) == 5

    username = sys.argv[1]
    password = sys.argv[2]
    sem_tw_name = sys.argv[3]
    _uid = ObjectId(sys.argv[4])

    conf = config.importers['mq'][sem_tw_name]
    study_period_name = conf['sem_name']  # '2016 Session 1'
    no_class_weeks = conf.get('no_class_weeks', frozenset())  # type: AbstractSet[arrow.Arrow]

    session = MQeStudentSession()
    try:
        session.login(username, password)
    except LoginFailedError:
        print('{"error":"Login failed. Wrong username or password?"}')
        return

    study_periods = get_study_periods(session.get_timetable_page())
    study_periods = {x['name']: x for x in study_periods}

    if study_period_name not in study_periods:
        json.dump({"error": "You are not enrolled in any units in the selected session (%s)." % study_period_name}, sys.stdout)
        return

    study_period_code = study_periods[study_period_name]['code']
    study_period_year = int(study_period_code.split('-')[0])

    if study_periods[study_period_name]['selected']:
        filter_page = session.get_timetable_page()
    else:
        filter_page = session.get_timetable_filter_page(study_period_code)

    unit_names = get_unit_names(filter_page)
    start_end_arws = start_end_arrows(filter_page, year=study_period_year)

    first_class = min(a for a, _ in start_end_arws.values())
    last_class = max(b for _, b in start_end_arws.values())
    week_start = max(first_class, arrow.now(TZ)).floor('week')

    all_classes = process(session, study_period_code, week_start, last_class, unit_names, no_class_weeks)

    save.insertObject({
        'calendar': {
            '_uid': _uid,
            'name': 'MQ_' + sem_tw_name,
            'events': all_classes,
            'type': 'eStudent',
        },
        'user': {},
        '_uid': _uid,
    })


def process(session, study_period_code, week_start, last_class, unit_names, known_no_classes_weeks):
    assert week_start.weekday() == 0
    all_classes = []

    while week_start <= last_class:
        if week_start in known_no_classes_weeks:
            week_start = week_start.replace(weeks=+1)
            continue

        weektable = session.get_timetable_week(study_period_code, week_start)

        for isoweekdaym1, day in enumerate(DAYS):
            this_day = week_start.replace(days=+isoweekdaym1)
            classes = weektable[day]

            for cls in reversed(classes):
                unit_code = cls['subject']
                start_h, start_m = tupleise_24h(cls['start'])
                end_h, end_m = tupleise_24h(cls['end'])
                this_start = this_day.replace(hour=start_h, minute=start_m)
                this_end = this_day.replace(hour=start_h, minute=start_m)

                description = '{0} - {1}'.format(cls['what'], unit_names[unit_code])

                all_classes.append({
                    'name': unit_code,
                    'location': cls['where'],
                    'description': description,
                    'begin': this_start.timestamp,
                    'end': this_end.timestamp,
                })

        week_start = week_start.replace(weeks=+1)

    return all_classes


if __name__ == "__main__":
    main()
