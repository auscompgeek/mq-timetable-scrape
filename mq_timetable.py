from bs4 import BeautifulSoup

DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']


def to_timetable_dict(page):
    soup = BeautifulSoup(page)
    timetable = {}
    for day in DAYS:
        classes = []
        col = soup.find(id="ctl00_Content_ctlTimetableMain_%sDayCol_Body" % day)
        for cls in col.find_all(class_='cssClassInnerPanel'):
            start = cls.find(class_='cssHiddenStartTm')['value']
            end = cls.find(class_='cssHiddenEndTm')['value']
            what = cls.find(class_='cssTtableClsSlotWhat').string
            where = cls.find(class_='cssTtableClsSlotWhere').string
            classes.append({
                'start': start,
                'end': end,
                'what': what,
                'where': where,
            })
        timetable[day] = classes
    return timetable
