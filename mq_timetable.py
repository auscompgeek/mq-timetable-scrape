#!/usr/bin/env python
from __future__ import print_function

import arrow
import requests
from bs4 import BeautifulSoup

DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
LOGIN_URL = 'https://student1.mq.edu.au/T1SMProd/WebApps/eStudent/login.aspx'
TIMETABLE_URL = 'https://student1.mq.edu.au/T1SMProd/WebApps/eStudent/SM/StudentTtable10.aspx?f=MQ.EST.TIMETBL.WEB'
TZ = 'Australia/Sydney'


class LoginFailedError(Exception):
    def __init__(self, response):
        self.response = response


class MQeStudentSession(object):
    def __init__(self):
        self.sess = requests.Session()
        self._timetable_page = None

    def login(self, studentid, password):
        # this is disgusting.
        r = self.sess.get(LOGIN_URL)

        data = make_estudent_happy(r.text)
        data.update({
            '__EVENTTARGET': 'ctl00$Content$cmdLogin',
            '__EVENTARGUMENT': '',
            'ctl00$Content$txtUserName$txtText': studentid,
            'ctl00$Content$txtPassword$txtText': password,
        })

        r = self.sess.post(LOGIN_URL, data=data, allow_redirects=False)

        # we'll get redirected iff login was successful
        if r.status_code != requests.codes.found:
            raise LoginFailedError(r)

    def get_start_end_arrows(self):
        return get_start_end_arrows(self.get_start_end_dates())

    def get_start_end_dates(self):
        return get_start_end_dates(self.get_timetable_page())

    def get_timetable_page(self):
        if not self._timetable_page:
            r = self.sess.get(TIMETABLE_URL, allow_redirects=False)
            r.raise_for_status()
            self._timetable_page = r.text
        return self._timetable_page

    def get_timetable_week_page(self, study_period, arw):
        tt_page = self.get_timetable_page()
        data = make_estudent_happy(tt_page)
        data.update({
            'ctl00$Content$ctlFilter$CboStudyPeriodFilter$elbList': study_period,
            'ctl00$Content$ctlFilter$TxtStartDt': arw.format('DD-MMM-YYYY'),
            'ctl00$Content$ctlFilter$BtnSearch': 'Refresh',
        })
        r = self.sess.post(TIMETABLE_URL, data=data, allow_redirects=False)
        r.raise_for_status()
        return r.text

    def get_timetable(self):
        return to_timetable_dict(self.get_timetable_page())

    def get_timetable_week(self, study_period, arw):
        return to_timetable_dict(self.get_timetable_week_page(study_period, arw))

    def get_unit_names(self):
        return get_unit_names(self.get_timetable_page())


def get_start_end_dates(page):
    dates = {}
    soup = BeautifulSoup(page)
    units = soup.find_all(class_='cssTtableSspNavContainer')

    for unit in units:
        unit_code = unit.find(class_='cssTtableSspNavMasterSpkInfo2').find('span').string
        classes = unit.find_all(class_='cssTtableNavActvTop')

        for cls in classes:
            class_type = cls.find(class_='cssTtableSspNavActvNm').string.strip()

            what = cls.find(class_='cssTtableNavMainWhat')
            if not what:
                # the user isn't enrolled in this class
                continue

            what = what.string
            assert what.startswith('Class ')
            class_num = int(what[len('Class '):])

            when = cls.find(class_='cssTtableNavMainWhen')
            start_date = when.contents[1]
            end_date = when.contents[3]

            dates[unit_code, '%s (%d)' % (class_type, class_num)] = start_date, end_date

    return dates


def get_start_end_arrows(dates, year=None):
    arws = {}

    for key, (start, end) in dates.items():
        start_arw = estudent_date_to_arrow(start, year=year)
        end_arw = estudent_date_to_arrow(end, year=year)
        arws[key] = start_arw, end_arw

    return arws


def get_selected_session(page):
    soup = BeautifulSoup(page)
    study_period_select = soup.find(id='ctl00_Content_ctlFilter_CboStudyPeriodFilter_elbList')
    selected_option = study_period_select.find(selected='selected')
    return selected_option['value'], selected_option.string


def get_unit_names(page):
    names = {}
    soup = BeautifulSoup(page)
    units = soup.find_all(class_='cssTtableSspNavContainer')

    for unit in units:
        unit_code = unit.find(class_='cssTtableSspNavMasterSpkInfo2').find('span').string
        unit_name = unit.find(class_='cssTtableSspNavMasterSpkInfo3').find('div').string.strip()
        names[unit_code] = unit_name

    return names


def to_timetable_dict(page):
    soup = BeautifulSoup(page)
    timetable = {}

    for day in DAYS:
        classes = []
        col = soup.find(id='ctl00_Content_ctlTimetableMain_%sDayCol_Body' % day)

        for cls in col.find_all(class_='cssClassInnerPanel'):
            classes.append({
                'start': to_24h(cls.find(class_='cssHiddenStartTm')['value']),
                'end': to_24h(cls.find(class_='cssHiddenEndTm')['value']),
                'what': cls.find(class_='cssTtableClsSlotWhat').string,
                'where': cls.find(class_='cssTtableClsSlotWhere').string,
                'subject': cls.find(class_='cssTtableHeaderPanel').string.strip(),
            })

        timetable[day] = classes

    return timetable


def estudent_date_to_arrow(date, year=None):
    day, month = date.split('-')
    month = arrow.locales.EnglishLocale().month_number(month)
    day = int(day)
    if year:
        return arrow.Arrow(year, month, day, tzinfo=TZ)
    else:
        return arrow.get(tzinfo=TZ).floor('day').replace(month=month, day=day)


def conv_12h_to_24h_tuple(time):
    am_pm = time[-2:].lower()
    hour, minute = map(int, time[:-2].split(':'))
    if am_pm == 'pm' and hour != 12:
        hour += 12
    return hour, minute


def to_24h(time):
    am_pm = time[-2:].lower()
    hour, minute = time[:-2].split(':')
    hour = int(hour)
    if am_pm == 'pm' and hour != 12:
        hour += 12
    return '{:>02}:{}'.format(hour, minute)


def make_estudent_happy(page):
    """Extract required form values for POST requests."""
    values = {}
    soup = BeautifulSoup(page)

    for name in '__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION':
        values[name] = soup.find(id=name)['value']

    return values


def get_timetable(studentid, password):
    session = MQeStudentSession()
    session.login(studentid, password)
    return session.get_timetable()


def main():
    import getpass
    import json
    import sys

    username = sys.argv[1] if len(sys.argv) > 1 else input('Student ID: ')
    password = sys.argv[2] if len(sys.argv) > 2 else getpass.getpass()

    try:
        timetable = get_timetable(username, password)
    except LoginFailedError:
        print('{"error":"Login failed. Wrong username or password?"}')
    else:
        json.dump(timetable, sys.stdout)
        print()


if __name__ == "__main__":
    main()
