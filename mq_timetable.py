#!/usr/bin/env python

import requests
from bs4 import BeautifulSoup

DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
LOGIN_URL = 'https://student1.mq.edu.au/T1SMProd/WebApps/eStudent/login.aspx'
TIMETABLE_URL = 'https://student1.mq.edu.au/T1SMProd/WebApps/eStudent/SM/StudentTtable10.aspx?f=MQ.EST.TIMETBL.WEB'


class LoginFailedError(Exception):
    def __init__(self, response):
        self.response = response


def to_timetable_dict(page):
    soup = BeautifulSoup(page)
    timetable = {}

    for day in DAYS:
        classes = []
        col = soup.find(id='ctl00_Content_ctlTimetableMain_%sDayCol_Body' % day)

        for cls in col.find_all(class_='cssClassInnerPanel'):
            classes.append({
                'start': cls.find(class_='cssHiddenStartTm')['value'],
                'end': cls.find(class_='cssHiddenEndTm')['value'],
                'what': cls.find(class_='cssTtableClsSlotWhat').string,
                'where': cls.find(class_='cssTtableClsSlotWhere').string,
                'subject': cls.find(class_='cssTtableHeaderPanel').string.strip(),
            })

        timetable[day] = classes

    return timetable


def make_login_happy(page):
    values = {}
    soup = BeautifulSoup(page)

    for name in '__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION':
        values[name] = soup.find(id=name)['value']

    return values


def get_timetable(studentid, password):
    sess = requests.Session()

    # this dance isn't fun
    r = sess.get(LOGIN_URL)
    data = make_login_happy(r.text)
    data.update({
        '__EVENTTARGET': 'ctl00$Content$cmdLogin',
        '__EVENTARGUMENT': '',
        'ctl00$Content$txtUserName$txtText': studentid,
        'ctl00$Content$txtPassword$txtText': password,
    })

    r = sess.post(LOGIN_URL, data=data, allow_redirects=False)
    # we'll get redirected iff login was successful
    if r.status_code != requests.codes.found:
        raise LoginFailedError(r)

    r = sess.get(TIMETABLE_URL)
    return to_timetable_dict(r.text)


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
