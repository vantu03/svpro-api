import base64, json
import httpx, re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from app.utils import extract_form_fields, convert_time_to_minutes, clean_full_name


class Tnue:
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
        self.me = None

    async def login(self, tk, mk):
        try:
            res = await self.session.get("https://qldaotao.tnue.edu.vn/congthongtin/login.aspx")
            soup = BeautifulSoup(res.text, 'html.parser')
            form_data = extract_form_fields(soup.find("form", {"id": "formLoginSSO"}))

            form_data['username'] = tk
            form_data['password'] = mk

            res = await self.session.post("https://qldaotao.tnue.edu.vn/congthongtin/login.aspx", data=form_data)
            soup = BeautifulSoup(res.text, 'html.parser')

            if "login.aspx" in str(res.url):
                return {"error": "Đăng nhập thất bại hãy kiểm tra lại tài khoản mật khẩu"}

            full_name_tag = soup.find(id="lblHoTenNguoiDangNhap")

            m = re.search(r'AXYZCLRVN\s*=\s*\(\)\s*=>\s*"([^"]+)"', res.text)
            if m:
                encrypted_str = m.group(1)
                self.me = json.loads(Tnue.ad(encrypted_str, "AzzS"))
            return {
                'success': '',
                'full_name': clean_full_name(full_name_tag.get_text(strip=True)) if full_name_tag else None,
                'password': mk}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def ad(data_b64, key) -> str:
        s = base64.b64decode(data_b64).decode("utf-8", errors="ignore")
        out_chars = []
        klen = len(key)
        for i, ch in enumerate(s):
            out_chars.append(chr(ord(ch) ^ ord(key[i % klen])))
        return "".join(out_chars)

    @staticmethod
    def ae(plaintext, key) -> str:
        xored = []
        klen = len(key)
        for i, ch in enumerate(plaintext):
            xored.append(chr(ord(ch) ^ ord(key[i % klen])))
        xored_str = "".join(xored)
        return xored_str

    async def get_schedule(self):
        await self.get_lich_hoc()
        #await self.get_lich_thi()

        self.result['schedule'].sort(key=lambda x: (
            datetime.strptime(x['date'], '%d/%m/%Y') if x['date'] else datetime.max,
            convert_time_to_minutes(x.get('timeRange', ''))
        ))

        return self.result

    async def get_lich_hoc(self, start_date=None, end_date=None):
        if not self.me:
            raise Exception("Chưa đăng nhập hoặc chưa có thông tin user")


        url = "https://qldaotao.tnue.edu.vn/sinhvienapi/api/SV_ThongTin/LayDSLichCaNhan"
        params = {
            "action": "SV_ThongTin/LayDSLichCaNhan",
            "type": "GET",
            "strQLSV_NguoiHoc_Id": self.me["userId"],
            "strNgayBatDau": (self.today - timedelta(days=365 * 4)).strftime("%d/%m/%Y"),
            "strNgayKetThuc": (self.today + timedelta(days=365 * 1)).strftime("%d/%m/%Y"),
            "strChucNang_Id": '',
            "strNguoiThucHien_Id": self.me["userId"],
        }

        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "authorization": f"Bearer {self.me['tokenJWT']}"
        }

        res = await self.session.get(url, params=params, headers=headers)
        data = res.json()

        if not data.get("Success"):
            return

        for item in data.get("Data", []):


            lichhoc = {
                "date": item.get("NGAYHOC"),
                "dayOfWeek": int(item["THU"]) if item.get("THU") else None,
                "className": item.get("TENHOCPHAN"),
                "scheduleType": "Lịch học",
                "timeRange": f"{int(item['GIOBATDAU']):02d}:{int(item['PHUTBATDAU']):02d} - "
                             f"{int(item['GIOKETTHUC']):02d}:{int(item['PHUTKETTHUC']):02d}",
                "detail": {
                    "Phòng": item.get("TENPHONGHOC"),
                    "Tiết": ", ".join(str(i) for i in range(int(item["TIETBATDAU"]), int(item["TIETKETTHUC"]) + 1))
                    if item.get("TIETBATDAU") and item.get("TIETKETTHUC") else "Không xác định",
                    "Buổi": item.get("THUOCTINH_TEN"),
                },
                "hidden": {
                    "Số tiết": int(item.get("SOTIET"))
                }
            }
            if item.get("GIANGVIEN"):
                lichhoc['hidden']["Giảng viên"] = item["GIANGVIEN"]
            self.result["schedule"].append(lichhoc)

    async def get_lich_thi(self):
        pass
