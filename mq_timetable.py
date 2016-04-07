#!/usr/bin/env python
from __future__ import print_function

import requests
from bs4 import BeautifulSoup

DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
LOGIN_URL = 'https://student1.mq.edu.au/T1SMProd/WebApps/eStudent/login.aspx'
TIMETABLE_URL = 'https://student1.mq.edu.au/T1SMProd/WebApps/eStudent/SM/StudentTtable10.aspx?f=MQ.EST.TIMETBL.WEB'


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

        data = make_login_happy(r.text)
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

    def get_timetable_page(self):
        if not self._timetable_page:
            r = self.sess.get(TIMETABLE_URL)
            r.raise_for_status()
            self._timetable_page = r.text
        return self._timetable_page

    def get_timetable(self):
        return to_timetable_dict(self.get_timetable_page())


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


def to_24h(time):
    am_pm = time[-2:].lower()
    hour, minute = time[:-2].split(':')
    hour = int(hour)
    if am_pm == 'pm' and hour != 12:
        hour += 12
    return '{:>02}:{}'.format(hour, minute)


def make_login_happy(page):
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
