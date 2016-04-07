#!/usr/bin/env python
from mq_timetable import get_timetable, LoginFailedError, DAYS


def main():
    import getpass
    import sys

    username = sys.argv[1] if len(sys.argv) > 1 else input('Student ID: ')
    password = sys.argv[2] if len(sys.argv) > 2 else getpass.getpass()

    try:
        timetable = get_timetable(username, password)
    except LoginFailedError:
        print('Login failed. Wrong username or password?')
    else:
        for day in DAYS:
            print('\n' + day)
            # eStudent seems to render later classes in the day first
            for cls in reversed(timetable[day]):
                print('* {subject} {what}\n  {start}-{end}\n  {where}'.format(**cls))


if __name__ == "__main__":
    main()
