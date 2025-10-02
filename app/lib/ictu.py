import httpx, pandas as pd, re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from io import BytesIO

from app.utils import extract_form_fields, convert_time_to_minutes, find_text_positions, \
    clean_full_name, md5_hash_once, parse_period_range


class Ictu:

    @staticmethod
    def get_study_time(tiet_start, tiet_end):
        tiet_map = {
            1: ("6:45", "7:35"), 2: ("7:40", "8:30"), 3: ("8:40", "9:30"),
            4: ("9:40", "10:30"), 5: ("10:35", "11:25"), 6: ("13:00", "13:50"),
            7: ("13:55", "14:45"), 8: ("14:55", "15:45"), 9: ("15:55", "16:45"),
            10: ("16:50", "17:40"), 11: ("18:15", "19:05"), 12: ("19:10", "20:00"),
            13: ("20:10", "21:00"), 14: ("21:10", "22:00"), 15: ("20:30", "21:30")
        }
        start = tiet_map.get(tiet_start, ("", ""))[0]
        end = tiet_map.get(tiet_end, ("", ""))[1]
        return f"{start} - {end}"

    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
            timeout=30.0,
            follow_redirects=True,
        )
        self.today = datetime.today()
        self.result = {
            'schedule': []
        }

    async def login(self, tk, mk):
        try:
            res = await self.session.get('http://dangkytinchi.ictu.edu.vn/kcntt/login.aspx')
            soup = BeautifulSoup(res.text, 'html.parser')
            form_data = extract_form_fields(soup.find('form'))

            form_data['txtUserName'] = tk
            form_data['txtPassword'] = md5_hash_once(mk)

            res = await self.session.post(url=res.url, data=form_data)
            soup = BeautifulSoup(res.text, 'html.parser')

            if "/login.aspx" in str(res.url):
                return {"error": "Đăng nhập thất bại hãy kiểm tra lại tài khoản mật khẩu"}

            full_name_tag = soup.find(id="PageHeader1_lblUserFullName")
            return {
                'success': '',
                'full_name': clean_full_name(full_name_tag.get_text(strip=True)) if full_name_tag else None,
                'password': md5_hash_once(mk)}
        except Exception as e:
            return {'error': str(e)}

    async def get_schedule(self):
        await self.get_lich_hoc()
        await self.get_lich_thi()

        self.result['schedule'].sort(key=lambda x: (
            datetime.strptime(x['date'], '%d/%m/%Y') if x['date'] else datetime.max,
            convert_time_to_minutes(x.get('timeRange', ''))
        ))

        return self.result

    async def get_lich_hoc(self):
        res = await self.session.get('http://dangkytinchi.ictu.edu.vn/kcntt/Reports/Form/StudentTimeTable.aspx')
        soup = BeautifulSoup(res.text, 'html.parser')
        form_data = extract_form_fields(soup.find('form'))
        # Lấy ngày hiện tại trừ đi 4 năm
        tu_ngay = datetime.today() - timedelta(days=365 * 4)
        form_data['txtTuNgay'] = tu_ngay.strftime('%d/%m/%Y')
        res = await self.session.post(url=res.url, data=form_data)

        if not res.headers['Content-Type'].startswith('application/vnd.ms-excel') :
            return

        df = pd.read_excel(BytesIO(res.content), engine='xlrd')
        class_pos = find_text_positions(df, 'Lớp học phần')
        col_class = class_pos[0]['col']
        row_start = class_pos[0]['row'] + 1
        current_week_start = None
        session_counter = {}

        col_teacher = find_text_positions(df, 'Giảng viên/ link meet')[0]['col']
        col_day = find_text_positions(df, 'Thứ')[0]['col']
        col_period = find_text_positions(df, 'Tiết học')[0]['col']
        col_room = find_text_positions(df, 'Địa điểm')[0]['col']

        for i in range(row_start, len(df)):
            cell = df.iloc[i, col_class]

            if isinstance(cell, str) and cell.startswith("Tuần"):
                match = re.search(r"\((\d{2}/\d{2}/\d{4}) đến (\d{2}/\d{2}/\d{4})\)", cell)
                if match:
                    current_week_start = datetime.strptime(match.group(1), "%d/%m/%Y")
            elif pd.notna(cell) and current_week_start:

                weekday = int(str(df.iloc[i, col_day]).strip())
                date = current_week_start + timedelta(days=weekday - 2)

                session_counter.setdefault(cell, 0)
                session_counter[cell] += 1

                tiet_start, tiet_end, tiet_str = parse_period_range(str(df.iloc[i, col_period]).strip())

                lichhoc = {
                    'date': date.strftime("%d/%m/%Y") if date else None,
                    'dayOfWeek': weekday,
                    'className': cell,
                    'scheduleType': 'Lịch học',
                    'timeRange': Ictu.get_study_time(tiet_start, tiet_end),
                    'detail': {
                        'Tiết': tiet_str,
                        'Địa điểm': str(df.iloc[i, col_room]).strip(),
                        'Buổi': session_counter[cell],
                    },
                    'hidden': {
                        'Giảng viên': str(df.iloc[i, col_teacher]).strip(),
                        'Ngày': date.strftime("%d/%m/%Y")
                    },
                }

                self.result['schedule'].append(lichhoc)

    async def get_lich_thi(self):
        res = await self.session.get('http://dangkytinchi.ictu.edu.vn/kcntt/StudentViewExamList.aspx')
        soup = BeautifulSoup(res.text, 'html.parser')
        form_data = extract_form_fields(soup.find('form'))
        # Lấy ngày hiện tại trừ đi 4 năm
        tu_ngay = datetime.today() - timedelta(days=365 * 4)
        form_data['txtTuNgay'] = tu_ngay.strftime('%d/%m/%Y')
        res = await self.session.post(url=res.url, data=form_data)

        if not res.headers['Content-Type'].startswith('application/vnd.ms-excel'):
            return

        df = pd.read_excel(BytesIO(res.content), engine='xlrd')
        class_pos = find_text_positions(df, 'Tên học phần')
        col_class = class_pos[0]['col']
        row_start = class_pos[0]['row'] + 1

        col_tc = find_text_positions(df, 'TC')[0]['col']
        col_day = find_text_positions(df, 'Ngày thi')[0]['col']
        col_period = find_text_positions(df, 'Thời gian thi')[0]['col']
        col_form = find_text_positions(df, 'Hình thức thi')[0]['col']
        col_sbd = find_text_positions(df, 'SBD')[0]['col']
        col_room = find_text_positions(df, 'Phòng thi')[0]['col']

        for i in range(row_start, len(df)):
            class_name = str(df.iloc[i, col_class]).strip()
            if not class_name or class_name.lower().startswith("nan"):
                continue

            try:
                date_obj = datetime.strptime(str(df.iloc[i, col_day]).strip(), "%d/%m/%Y")
                date = date_obj.strftime("%d/%m/%Y")
                day_of_week = date_obj.weekday() + 1
            except:
                date = None
                day_of_week = None

            time_range_match = re.search(r'(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})', str(df.iloc[i, col_period]))
            time_range = f"{time_range_match.group(1)} - {time_range_match.group(2)}" if time_range_match else ""

            self.result['schedule'].append({
                'date': date,
                'dayOfWeek': day_of_week,
                'className': class_name,
                'scheduleType': 'Lịch thi',
                'timeRange': time_range,
                'detail': {
                    'Ca thi': str(df.iloc[i, col_period]).strip(),
                    'Địa điểm': str(df.iloc[i, col_room]).strip()
                },
                'hidden': {
                    'Hình thức': str(df.iloc[i, col_form]).strip(),
                    'Số báo danh': str(df.iloc[i, col_sbd]).strip(),
                    'Số tín chỉ': str(df.iloc[i, col_tc]).strip()
                }
            })
