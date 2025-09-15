import json
from PIL import Image, ImageOps
import pandas as pd, re
import hashlib
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from datetime import datetime, timedelta
import copy
import os
import aiofiles
from uuid import uuid4

from sqlalchemy import RowMapping
from starlette.concurrency import run_in_threadpool

MD5_PATTERN = re.compile(r'^[a-fA-F0-9]{32}$')

def is_md5(s: str) -> bool:
    return bool(MD5_PATTERN.fullmatch(s))

def md5_hash_once(text: str) -> str:
    # Nếu đã là MD5 thì trả nguyên
    if is_md5(text):
        return text.lower()
    return md5_hash(text)

def md5_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def verify_password(raw_password: str, hashed_password: str) -> bool:
    try:
        return await run_in_threadpool(pwd_context.verify, raw_password, hashed_password)
    except UnknownHashError:
        return hashed_password == md5_hash(raw_password)

async def hash_password(password: str) -> str:
    return await run_in_threadpool(pwd_context.hash, password)
def to_dict(obj):
    if isinstance(obj, RowMapping) or isinstance(obj, dict):
        return {
            k: (v.isoformat() if isinstance(v, datetime) else v)
            for k, v in dict(obj).items()
        }

    if hasattr(obj, "__table__"):
        result = {}
        for c in obj.__table__.columns:
            v = getattr(obj, c.name)
            if isinstance(v, datetime):
                v = v.isoformat()
            result[c.name] = v
        return result

    return dict(obj)


def build_response(
    status_code = 200,
    detail: dict | list | None = None
):
    return {
        'statusCode': status_code,
        "detail": detail,
    }

def response_json(
    status: bool = True,
    message: str = "",
    data: dict | list | None = None
):
    return {
        "status": status,
        "message": message,
        "data": data
    }

def extract_form_fields(form):
    form_data = {}
    for input_tag in form.find_all('input'):
        name = input_tag.get('name')
        if not name: continue
        input_type = input_tag.get('type', 'text')
        value = input_tag.get('value', '')
        if input_type in ['checkbox', 'radio']:
            if input_tag.has_attr('checked'):
                form_data[name] = value
        else:
            form_data[name] = value
    for select in form.find_all('select'):
        name = select.get('name')
        if not name: continue
        selected_option = select.find('option', selected=True)
        form_data[name] = selected_option.get('value', '') if selected_option else \
            (select.find('option').get('value', '') if select.find('option') else '')
    for textarea in form.find_all('textarea'):
        name = textarea.get('name')
        if name:
            form_data[name] = textarea.text or ''
    return form_data

def find_text_positions(df: pd.DataFrame, search_text: str, case_sensitive=False):
    matches = []
    for row_idx, row in df.iterrows():
        for col_idx, cell in enumerate(row):
            if pd.notna(cell):
                cell_str = str(cell)
                if (cell_str == search_text) if case_sensitive else (cell_str.lower() == search_text.lower()):
                    matches.append({"row": row_idx, "col": col_idx, "value": cell})
    return matches

def convert_time_to_minutes(time_range):
    if not time_range or not isinstance(time_range, str): return -1
    match = re.match(r'(\d{2}):(\d{2})', time_range)
    return int(match.group(1)) * 60 + int(match.group(2)) if match else -1


def parse_period_range(period_raw: str):
    if not period_raw:
        return None, None, ""
    s = str(period_raw).strip()

    # Dạng "1-->3"
    m = re.match(r'^(\d+)\s*-->\s*(\d+)$', s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        rng = list(range(min(a, b), max(a, b) + 1))
        return min(rng), max(rng), ",".join(str(x) for x in rng)

    # Dạng "1-3"
    m = re.match(r'^(\d+)\s*-\s*(\d+)$', s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        rng = list(range(min(a, b), max(a, b) + 1))
        return min(rng), max(rng), ",".join(str(x) for x in rng)

    # Dạng "1,2,3" hoặc "2" hoặc "2, 3"
    nums = re.findall(r'\d+', s)
    if nums:
        nums = [int(x) for x in nums]
        start = min(nums)
        end = max(nums)
        return start, end, ",".join(str(x) for x in nums)

    return None, None, ""


def clean_full_name(value):
    value = str(value).strip()
    value = re.sub(r'\s*\([^)]*\)\s*$', '', value)
    return value


def build_navigate_payload(route: str, params: dict | None = None) -> str:
    data = {
        "action": "navigate",
        "route": route,
        "params": params or {}
    }
    return json.dumps(data, ensure_ascii=False)

def normalize_name(name: str) -> str:
    if not name or not isinstance(name, str):
        return ""
    name = " ".join(name.strip().split())
    name = re.sub(r"[^0-9A-Za-zÀ-ỹà-ỹ\s]", "", name)
    return " ".join(w.capitalize() for w in name.split())

def normalize_phone(phone: str) -> str:
    if not phone or not isinstance(phone, str):
        return ""

    # Bỏ hết ký tự không phải số
    digits = re.sub(r"\D", "", phone)

    # Chỉ lấy 10 số cuối cùng
    if len(digits) >= 10:
        return digits[-10:]

    return ""

def duplicate_by_date(item, start_date, end_date, weekday=None):
    start = datetime.strptime(start_date, "%d/%m/%Y").date()
    end = datetime.strptime(end_date, "%d/%m/%Y").date()
    result = []
    current = start
    while current <= end:
        dow = current.weekday() + 1  # 1..7 (Mon=1 ... Sun=7)
        if weekday is None or dow == weekday:
            new_it = copy.deepcopy(item)
            new_it["date"] = current.strftime("%d/%m/%Y")
            new_it["dayOfWeek"] = dow
            result.append(new_it)
        current += timedelta(days=1)
    return result

async def save_upload_file(file, upload_folder: str, max_size: int, allowed_exts: set):
    ext = os.path.splitext(file.filename)[-1].lower()

    if ext not in allowed_exts:
        return None, "File type not allowed"

    content = await file.read()

    if len(content) > max_size:
        return None, f"File exceeds {max_size // (1024 * 1024)}MB limit"

    os.makedirs(upload_folder, exist_ok=True)
    filename = f"{uuid4().hex}{ext}"
    saved_path = os.path.join(upload_folder, filename)

    async with aiofiles.open(saved_path, "wb") as out_file:
        await out_file.write(content)

    return {
        "filename": filename,
        "saved_path": saved_path,
        "size": len(content),
        "mime_type": file.content_type,
        "original_name": file.filename
    }, None


def is_outdated(current: str, latest: str) -> bool:
    try:
        c = list(map(int, current.split(".")))
        l = list(map(int, latest.split(".")))
        for i in range(len(l)):
            if i >= len(c):
                return True
            if c[i] < l[i]:
                return True
            if c[i] > l[i]:
                return False
        return False
    except Exception:
        return False


def compress_image(path: str, max_dim: int = 2048, quality: int = 85) -> int:
    try:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        img_format = img.format

        # Resize nếu kích thước quá lớn
        w, h = img.size
        if max(w, h) > max_dim:
            ratio = max_dim / float(max(w, h))
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # Nếu PNG mà quá nặng, convert sang JPEG
        if img_format == "PNG":
            img = img.convert("RGB")
            new_path = os.path.splitext(path)[0] + ".jpg"
            img.save(new_path, "JPEG", quality=quality, optimize=True)
            os.remove(path)
            path = new_path
        else:
            img.save(path, img_format, quality=quality, optimize=True)

        return os.path.getsize(path)
    except Exception as e:
        print(f"Compression error: {e}")
        return os.path.getsize(path)