
import httpx, re
from bs4 import BeautifulSoup
from datetime import datetime
from app.utils import duplicate_by_date, extract_form_fields, convert_time_to_minutes, clean_full_name, parse_period_range

class Tnus:

    @staticmethod
    def get_study_time(tiet_start, tiet_end):
        tiet_map = {
            1: ("07:00", "07:50"),
            2: ("07:55", "08:45"),
            3: ("08:50", "09:40"),
            4: ("09:50", "10:40"),
            5: ("10:45", "11:35"),
            6: ("11:40", "12:30"),
            7: ("13:00", "13:50"),
            8: ("13:55", "14:45"),
            9: ("14:50", "15:40"),
            10: ("15:50", "16:40"),
            11: ("16:45", "17:35"),
            12: ("17:40", "18:30"),
        }
        start = tiet_map.get(tiet_start, ("", ""))[0]
        end = tiet_map.get(tiet_end, ("", ""))[1]
        return f"{start} - {end}" if start and end else ""

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
            res = await self.session.get('https://sinhvien.tnus.edu.vn/DangNhap/Login')
            soup = BeautifulSoup(res.text, 'html.parser')
            form_data = extract_form_fields(soup.find('form'))

            form_data['Username'] = tk
            form_data['password'] = mk

            res = await self.session.post("https://sinhvien.tnus.edu.vn/DangNhap/CheckLogin", data=form_data)
            soup = BeautifulSoup(res.text, 'html.parser')

            if "DangNhap/Login" in str(res.url):
                return {"error": "Đăng nhập thất bại hãy kiểm tra lại tài khoản mật khẩu"}

            res = await self.session.get('https://sinhvien.tnus.edu.vn/SinhVien/ThongTinSinhVien')
            soup = BeautifulSoup(res.text, 'html.parser')
            full_name_tag = soup.find(id="lblHoTen")
            return {
                'success': '',
                'full_name': clean_full_name(full_name_tag.get_text(strip=True)) if full_name_tag else None,
                'password': mk}
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
        res = await self.session.get('https://sinhvien.tnus.edu.vn/TraCuuLichHoc/Index')
        soup = BeautifulSoup(res.text, 'html.parser')

        table = soup.find('table', {'class': 'table'})
        if not table:
            return

        rows = table.find_all('tr')
        for row in rows[1:]:  # bỏ header
            cols = [c.get_text(strip=True) for c in row.find_all('td')]
            if not cols or len(cols) < 9:
                continue

            class_name = cols[1]
            credits = cols[2]
            class_code = cols[3]
            time_range = cols[4]
            weekday = cols[5]
            periods = cols[6]
            room = cols[7]
            teacher = cols[8]

            match = re.search(r"(\d{2}/\d{2}/\d{4})-(\d{2}/\d{2}/\d{4})", time_range)
            if not match:
                continue
            start_date, end_date = match.groups()

            tiet_start, tiet_end, tiet_str = parse_period_range(periods)

            lichhoc = {
                'date': None,
                'dayOfWeek': int(weekday) if weekday.isdigit() else None,
                'className': class_name,
                'scheduleType': 'Lịch học',
                'timeRange': Tnus.get_study_time(tiet_start, tiet_end),
                'detail': {
                    'Tiết': tiet_str,
                    'Địa điểm': room,
                },
                'hidden': {
                    'Giảng viên': teacher,
                    'Số tín chỉ': credits,
                    'Mã lớp': class_code,
                },
            }
            items = duplicate_by_date(lichhoc, start_date, end_date, int(weekday))
            self.result['schedule'].extend(items)

    async def get_lich_thi(self):
        res = await self.session.get("https://sinhvien.tnus.edu.vn/TraCuuLichThi/Index")
        soup = BeautifulSoup(res.text, "html.parser")

        table = soup.find("table", {"class": "table"})
        if not table:
            return

        rows = table.find_all("tr")
        for row in rows[1:]:  # bỏ header
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if not cols or len(cols) < 11:
                continue

            stt, ma_hp, ten_hp, so_tc, ngay_thi, gio_thi, lan_thi, dot_thi, sbd, phong, hinh_thuc = cols

            lichthi = {
                "date": ngay_thi if ngay_thi else None,
                "dayOfWeek": None,
                "className": ten_hp,
                "scheduleType": "Lịch thi",
                "timeRange": gio_thi,
                "detail": {
                    "Mã học phần": ma_hp,
                    "Phòng": phong,
                    "Hình thức": hinh_thuc,
                },
                "hidden": {
                    "Số tín chỉ": so_tc,
                    "Lần thi": lan_thi,
                    "Đợt thi": dot_thi,
                    "SBD": sbd,
                },
            }

            self.result["schedule"].append(lichthi)
