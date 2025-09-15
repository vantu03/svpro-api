import httpx
import re
from datetime import datetime, timedelta
from app.utils import convert_time_to_minutes

class Tnut:
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=30.0,
            follow_redirects=True,
        )
        self.today = datetime.today()
        self.token = None
        self.result = {"schedule": []}

    async def login(self, username, password):
        url = "https://portal.tnut.edu.vn/api/auth/login"
        data = {
            "username": username,
            "password": password,
            "grant_type": "password"
        }

        res = await self.session.post(url, data=data)
        res_json = res.json()

        if res_json.get("code") != 200:
            return {"error": res_json.get("message", "Đăng nhập thất bại")}

        self.token = res_json["access_token"]
        return {
            "success": True,
            "full_name": res_json.get("name"),
            "password": password
        }

    async def get_hoc_ky_list(self):
        url = "https://portal.tnut.edu.vn/api/sch/w-locdshockytkbuser"
        headers = {"authorization": f"Bearer {self.token}"}
        body = {
            "filter": {"is_tieng_anh": None},
            "additional": {
                "paging": {"limit": 100, "page": 1},
                "ordering": [{"name": "hoc_ky", "order_type": 1}]
            }
        }
        res = await self.session.post(url, json=body, headers=headers)
        return res.json()

    async def get_lich_hoc(self):
        hoc_ky_data = await self.get_hoc_ky_list()
        ds_hoc_ky = hoc_ky_data["data"]["ds_hoc_ky"]
        current_hk = hoc_ky_data["data"]["hoc_ky_theo_ngay_hien_tai"]

        headers = {"authorization": f"Bearer {self.token}"}
        session_counter = {}
        thu_map = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 1: 7}

        for hk in ds_hoc_ky:
            if hk["hoc_ky"] > current_hk:
                continue

            body = {"hoc_ky": hk["hoc_ky"], "loai_doi_tuong": 1, "id_du_lieu": None}
            res = await self.session.post(
                "https://portal.tnut.edu.vn/api/sch/w-locdstkbhockytheodoituong",
                json=body, headers=headers
            )
            data = res.json()

            for item in data["data"]["ds_nhom_to"]:
                class_name = f"{item['ten_mon']} ({item['nhom_to']})"

                # Parse khoảng ngày học
                m = re.match(r"(\d{2}/\d{2}/\d{4}) đến (\d{2}/\d{2}/\d{4})", item["tooltip"])
                if not m:
                    continue
                start_date = datetime.strptime(m.group(1), "%d/%m/%Y")
                end_date = datetime.strptime(m.group(2), "%d/%m/%Y")

                thu = item["thu"]
                day_of_week = thu_map.get(thu)
                if not day_of_week:
                    continue

                # Sinh ra từng buổi học
                current_date = start_date
                while current_date <= end_date:
                    if current_date.weekday() + 1 == day_of_week:
                        date_str = current_date.strftime("%d/%m/%Y")

                        # Đếm buổi học
                        session_counter.setdefault(class_name, 0)
                        session_counter[class_name] += 1

                        tiet_start = item["tbd"]
                        tiet_end = tiet_start + item["so_tiet"] - 1

                        lichhoc = {
                            "date": date_str,
                            "dayOfWeek": day_of_week,
                            "className": class_name,
                            "scheduleType": "Lịch học",
                            "timeRange": f"{item['tu_gio']} - {item['den_gio']}",
                            "detail": {
                                "Tiết": ", ".join(str(t) for t in range(tiet_start, tiet_end + 1)),
                                "Địa điểm": item["phong"],
                                "Buổi": session_counter[class_name],
                            },
                            "hidden": {
                                "Giảng viên": item.get("gv") or "",
                                "Kiểu": "LT" if item.get("so_tiet_lt", 0) > 0 else "TH"
                            },
                        }
                        self.result["schedule"].append(lichhoc)
                    current_date += timedelta(days=1)

    async def get_lich_thi(self):
        hoc_ky_data = await self.get_hoc_ky_list()
        ds_hoc_ky = hoc_ky_data["data"]["ds_hoc_ky"]
        current_hk = hoc_ky_data["data"]["hoc_ky_theo_ngay_hien_tai"]

        headers = {"authorization": f"Bearer {self.token}"}

        for hk in ds_hoc_ky:
            if hk["hoc_ky"] > current_hk:
                continue

            body = {"filter": {"hoc_ky": hk["hoc_ky"], "is_giua_ky": False}}
            res = await self.session.post(
                "https://portal.tnut.edu.vn/api/epm/w-locdslichthisvtheohocky",
                json=body, headers=headers
            )
            data = res.json().get("data", {})
            ds_thi = data.get("ds_lich_thi", [])
            if not ds_thi:
                continue

            for item in ds_thi:
                try:
                    date_obj = datetime.strptime(item["ngay_thi"], "%d/%m/%Y")
                    date_str = date_obj.strftime("%d/%m/%Y")
                    day_of_week = date_obj.weekday() + 1
                except:
                    date_str, day_of_week = None, None

                start_time = item.get("gio_bat_dau")
                so_phut = int(item.get("so_phut", 0))
                if start_time and so_phut:
                    end_time = (datetime.strptime(start_time, "%H:%M") +
                                timedelta(minutes=so_phut)).strftime("%H:%M")
                    time_range = f"{start_time} - {end_time}"
                else:
                    time_range = start_time or ""

                lichthi = {
                    "date": date_str,
                    "dayOfWeek": day_of_week,
                    "className": item["ten_mon"].strip(),
                    "scheduleType": "Lịch thi",
                    "timeRange": time_range,
                    "detail": {
                        "Ca thi": f"Tiết {item.get('tiet_bat_dau')}, {item.get('so_tiet')} tiết",
                        "Địa điểm": item.get("dia_diem_thi", "")
                    },
                    "hidden": {
                        "Hình thức": item.get("hinh_thuc_thi", ""),
                        "Số báo danh": item.get("so_bao_danh", ""),
                        "Số tín chỉ": ""
                    }
                }
                self.result["schedule"].append(lichthi)

    async def get_schedule(self):
        await self.get_lich_hoc()
        await self.get_lich_thi()

        # Sort theo ngày và giờ
        self.result["schedule"].sort(key=lambda x: (
            datetime.strptime(x["date"], "%d/%m/%Y") if x.get("date") else datetime.max,
            convert_time_to_minutes(x.get("timeRange", ""))
        ))

        return self.result
