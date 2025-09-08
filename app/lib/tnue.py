import httpx, pandas as pd, re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from io import BytesIO
from app.utils import duplicate_by_date

from app.utils import extract_form_fields, convert_time_to_minutes, find_text_positions, get_study_time, \
    clean_full_name, md5_hash_once, parse_period_range


class Tnue:
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
            timeout=30.0,
            follow_redirects=True,
        )
        self.today = datetime.today()
        self.result = {
            'startDate': self.today.strftime("%d/%m/%Y"),
            'endDate': (self.today + timedelta(days=7)).strftime("%d/%m/%Y"),
            'schedule': []
        }

    async def login(self, tk, mk):
        try:
            res = await self.session.get('http://daotao.dhsptn.edu.vn/dhsp/login.aspx')
            soup = BeautifulSoup(res.text, 'html.parser')
            form_data = extract_form_fields(soup.find('form'))

            form_data['txtUserName'] = tk
            form_data['txtPassword'] = md5_hash_once(mk)

            res = await self.session.post(url=res.url, data=form_data)
            soup = BeautifulSoup(res.text, 'html.parser')
            lbl_error = soup.find(id="lblErrorInfo")
            if lbl_error and lbl_error.text.strip():
                return {'error': lbl_error.text.strip()}

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

        # Cập nhật startDate và endDate theo lịch thực tế
        dates = [x['date'] for x in self.result['schedule'] if x.get('date')]
        if dates:
            self.result['startDate'] = dates[0]
            self.result['endDate'] = dates[-1]
        return self.result

    async def get_lich_hoc(self):
        res = await self.session.get('http://daotao.dhsptn.edu.vn/dhsp/Reports/Form/StudentTimeTable.aspx')
        soup = BeautifulSoup(res.text, 'html.parser')
        form_data = extract_form_fields(soup.find('form'))

        form_data['drpType'] = 'B'
        res = await self.session.post(url=res.url, data=form_data)

        if not res.headers['Content-Type'].startswith('application/vnd.ms-excel') :
            return

        df = pd.read_excel(BytesIO(res.content), engine='xlrd')
        class_pos = find_text_positions(df, 'Lớp học phần')
        col_class = class_pos[0]['col']
        row_start = class_pos[0]['row'] + 1
        current_week_start = None
        session_counter = {}

        col_teacher = find_text_positions(df, 'CBGD')[0]['col']
        col_day = find_text_positions(df, 'Thứ')[0]['col']
        col_period = find_text_positions(df, 'Tiết học')[0]['col']
        col_room = find_text_positions(df, 'Phòng học')[0]['col']

        col_time = find_text_positions(df, 'Thời gian học')[0]['col']

        for i in range(row_start, len(df)):
            class_name = str(df.iloc[i, col_class]).strip()
            if not class_name or class_name.lower().startswith("nan"):
                continue

            # Lấy thứ trong tuần
            weekday = int(str(df.iloc[i, col_day]).strip())

            # Lấy tiết học
            period_raw = str(df.iloc[i, col_period]).strip()

            # Lấy thời gian học (dạng dd/MM/yyyy-dd/MM/yyyy)
            time_range = str(df.iloc[i, col_time]).strip()
            match = re.search(r"(\d{2}/\d{2}/\d{4})-(\d{2}/\d{2}/\d{4})", time_range)
            if match:
                start_date = match.group(1)  # string dd/MM/yyyy
                end_date = match.group(2)  # string dd/MM/yyyy

                tiet_start, tiet_end, tiet_str = parse_period_range(str(df.iloc[i, col_period]).strip())
                lichhoc = {
                    'date': None,  # sẽ được duplicate_by_date gán lại
                    'dayOfWeek': weekday,
                    'className': class_name,
                    'scheduleType': 'Lịch học',
                    'timeRange': get_study_time(tiet_start, tiet_end),
                    'detail': {
                        'Tiết': tiet_str,
                        'Địa điểm': str(df.iloc[i, col_room]).strip(),
                    },
                    'hidden': {
                        'Giảng viên': str(df.iloc[i, col_teacher]).strip(),
                        'Thời gian học': time_range
                    },
                }

                # duplicate_by_date trả về list
                items = duplicate_by_date(lichhoc, start_date, end_date, weekday)
                self.result['schedule'].extend(items)

    async def get_lich_thi(self):
        res = await self.session.get('http://daotao.dhsptn.edu.vn/dhsp/StudentViewExamList.aspx')
        soup = BeautifulSoup(res.text, 'html.parser')
        form_data = extract_form_fields(soup.find('form'))
        # Lấy ngày hiện tại trừ đi 4 năm
        tu_ngay = datetime.today() - timedelta(days=365 * 4)
        form_data['txtTuNgay'] = tu_ngay.strftime('%d/%m/%Y')
        res = await self.session.post(url=res.url, data=form_data)

        if not res.headers['Content-Type'].startswith('application/vnd.ms-excel'):
            return

        df = pd.read_excel(BytesIO(res.content), engine='xlrd')
        class_pos = find_text_positions(df, 'Tên Học phần')
        col_class = class_pos[0]['col']
        row_start = class_pos[0]['row'] + 1

        col_tc = find_text_positions(df, 'Số TC')[0]['col']
        col_day = find_text_positions(df, 'Ngày thi')[0]['col']
        col_period = find_text_positions(df, 'Ca thi')[0]['col']
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
