import httpx
import re
from datetime import datetime, timedelta
import json

from app.utils import convert_time_to_minutes

class Tnut:
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
            timeout=30.0,
            follow_redirects=True,
        )
        self.today = datetime.today()
        self.token = None
        self.result = {
            'startDate': self.today.strftime("%d/%m/%Y"),
            'endDate': (self.today + timedelta(days=7)).strftime("%d/%m/%Y"),
            'schedule': []
        }

    async def login(self, tk, mk):
        try:
            url = 'https://portal.tnut.edu.vn/api/auth/login'

            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'vi,vi-VN;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
                'content-type': 'application/x-www-form-urlencoded',
                'idpc': '0',
                'origin': 'https://portal.tnut.edu.vn',
                'priority': 'u=1, i',
                'referer': 'https://portal.tnut.edu.vn/',
                'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'ua': 'LEzYQnWNUS7xNexI3UpxiVIqhlOPMMU/DfgsVQ==',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            }

            data = {
                'username': tk,
                'password': mk,
                'grant_type': 'password'
            }

            response = await self.session.post(url, headers=headers, data=data)
            res = response.json()
            if int(res['code']) != 200:
                return {'error': res.get('message', 'Unknown error')}
            self.token = res['access_token']
            return {
                'success': '',
                'full_name': res.get("name"),
                'password': mk
            }
        except Exception as e:
            return {'error': str(e)}

    async def gethocky(self):
        url = 'https://portal.tnut.edu.vn/api/sch/w-locdshockytkbuser'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'vi,vi-VN;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
            'authorization': f'Bearer {self.token}',
            'content-type': 'application/json',
        }
        json_data = {
            'filter': {
                'is_tieng_anh': None,
            },
            'additional': {
                'paging': {
                    'limit': 100,
                    'page': 1,
                },
                'ordering': [
                    {
                        'name': 'hoc_ky',
                        'order_type': 1,
                    },
                ],
            },
        }
        res = await self.session.post(url, json=json_data, headers=headers)
        return res.json()

    async def list_kyhoc(self):
        url = 'https://portal.tnut.edu.vn/api/sch/w-locdshockytkbuser'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'vi,vi-VN;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
            'authorization': f'Bearer {self.token}',
            'content-type': 'application/json',
        }
        json_data = {
            'filter': {
                'is_tieng_anh': None,
            },
            'additional': {
                'paging': {
                    'limit': 100,
                    'page': 1,
                },
                'ordering': [
                    {
                        'name': 'hoc_ky',
                        'order_type': 1,
                    },
                ],
            },
        }
        res = await self.session.post(url, json=json_data, headers=headers)
        return res.json()

    async def get_lich_hoc(self):
        try:
            gethockyz = await self.gethocky()
            list_kyhoc = await self.list_kyhoc()
            hocky = gethockyz['data']['hoc_ky_theo_ngay_hien_tai']
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'vi,vi-VN;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
                'authorization': f'Bearer {self.token}',
                'content-type': 'application/json',
            }
            for item in list_kyhoc['data']['ds_hoc_ky']:
                if item['hoc_ky'] > hocky:
                    continue
                json_data = {
                    'hoc_ky': item['hoc_ky'],
                    'loai_doi_tuong': 1,
                    'id_du_lieu': None,
                }
                res = await self.session.post('https://portal.tnut.edu.vn/api/sch/w-locdstkbhockytheodoituong',
                                              json=json_data, headers=headers)
                data = res.json()
                ds_nhom_to = data['data']['ds_nhom_to']
                session_counter = {}
                thu_map = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 1: 7}  # Map 'thu' to dayOfWeek (1=Mon)

                for item in ds_nhom_to:
                    class_name = f"{item['ten_mon']} ({item['nhom_to']})"
                    tooltip = item['tooltip']
                    match = re.match(r'(\d{2}/\d{2}/\d{4}) đến (\d{2}/\d{2}/\d{4})', tooltip)
                    if not match:
                        continue
                    start_str, end_str = match.groups()
                    start_date = datetime.strptime(start_str, '%d/%m/%Y')
                    end_date = datetime.strptime(end_str, '%d/%m/%Y')
                    thu = item['thu']
                    day_of_week = thu_map.get(thu, None)
                    if day_of_week is None:
                        continue

                    current_date = start_date
                    while current_date <= end_date:
                        if (current_date.weekday() + 1) == day_of_week:
                            date_str = current_date.strftime('%d/%m/%Y')
                            session_counter.setdefault(class_name, 0)
                            session_counter[class_name] += 1
                            tiet_start = item['tbd']
                            tiet_end = tiet_start + item['so_tiet'] - 1
                            time_range = f"{item['tu_gio']} - {item['den_gio']}"
                            lichhoc = {
                                'date': date_str,
                                'dayOfWeek': day_of_week + 1,
                                'className': class_name,
                                'scheduleType': 'Lịch học',
                                'timeRange': time_range,
                                'detail': {
                                    'Tiết': ", ".join(str(t) for t in range(tiet_start, tiet_end + 1)),
                                    'Địa điểm': item['phong'],
                                    'Buổi': session_counter[class_name],
                                },
                                'hidden': {
                                    'Giảng viên': item.get('gv') if item.get('gv') else None,
                                    'Kiểu': 'LT' if item.get('so_tiet_lt', 0) > 0 else 'TH'
                                },
                            }
                            self.result['schedule'].append(lichhoc)
                        current_date += timedelta(days=1)

        except FileNotFoundError:
            print("Error: lich.json not found")
        except json.JSONDecodeError:
            print("Error: Invalid JSON format in lich.json")
        except Exception as e:
            print(f"Error in get_lich_hoc: {str(e)}")

    async def get_lich_thi(self):
        try:
            gethockyz = await self.gethocky()
            list_kyhoc = await self.list_kyhoc()
            hocky = gethockyz['data']['hoc_ky_theo_ngay_hien_tai']
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'vi,vi-VN;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
                'authorization': f'Bearer {self.token}',
                'content-type': 'application/json',
            }
            for item in list_kyhoc['data']['ds_hoc_ky']:
                if item['hoc_ky'] > hocky:
                    continue
                json_data = {
                    'filter': {
                        'hoc_ky': item['hoc_ky'],
                        'is_giua_ky': False,
                    },
                    'additional': {
                        'paging': {
                            'limit': 100,
                            'page': 1,
                        },
                        'ordering': [
                            {
                                'name': None,
                                'order_type': None,
                            },
                        ],
                    },
                }
                res = await self.session.post('https://portal.tnut.edu.vn/api/epm/w-locdslichthisvtheohocky',
                                              json=json_data, headers=headers)
                res_data = res.json()
                if res_data.get("data", {}).get("ds_lich_thi") is None:
                    continue
                for item in res_data["data"]["ds_lich_thi"]:
                    class_name = item["ten_mon"].strip()
                    if not class_name or class_name.lower().startswith("nan"):
                        continue

                    try:
                        date_obj = datetime.strptime(item["ngay_thi"].strip(), "%d/%m/%Y")
                        date = date_obj.strftime("%d/%m/%Y")
                        day_of_week = date_obj.weekday() + 1
                    except:
                        date = None
                        day_of_week = None

                    # Lấy khung giờ
                    start_time = item.get("gio_bat_dau", "").strip()
                    so_phut = int(item.get("so_phut", 0))
                    if start_time and so_phut:
                        try:
                            end_time = (datetime.strptime(start_time, "%H:%M") + timedelta(minutes=so_phut)).strftime(
                                "%H:%M")
                            time_range = f"{start_time} - {end_time}"
                        except:
                            time_range = start_time
                    else:
                        time_range = ""

                    self.result["schedule"].append({
                        "date": date,
                        "dayOfWeek": day_of_week + 1,
                        "className": class_name,
                        "scheduleType": "Lịch thi",
                        "timeRange": time_range,
                        "detail": {
                            "Ca thi": f"Tiết {item.get('tiet_bat_dau', '')}, {item.get('so_tiet', '')} tiết",
                            "Địa điểm": item.get("dia_diem_thi", "").strip()
                        },
                        "hidden": {
                            "Hình thức": item.get("hinh_thuc_thi", "").strip(),
                            "Số báo danh": item.get("so_bao_danh", "").strip() if "so_bao_danh" in item else "",
                            "Số tín chỉ": ""  # Không có trong JSON gốc
                        }
                    })
        except Exception as e:
            print(f"Error in get_lich_thi: {str(e)}")

    async def get_schedule(self):
        await self.get_lich_hoc()
        await self.get_lich_thi()

        self.result['schedule'].sort(key=lambda x: (
            datetime.strptime(x['date'], '%d/%m/%Y') if x['date'] else datetime.max,
            convert_time_to_minutes(x.get('timeRange', ''))
        ))

        return self.result