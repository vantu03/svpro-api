import pandas as pd, re
import hashlib
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

def md5_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(raw_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(raw_password, hashed_password)
    except UnknownHashError:
        return hashed_password == md5_hash(raw_password)

def to_dict(model):
    result = {}
    for c in model.__table__.columns:
        value = getattr(model, c.name)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        result[c.name] = value
    return result

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

def convert_time_to_minutes(time_range):
    if not time_range or not isinstance(time_range, str): return -1
    match = re.match(r'(\d{2}):(\d{2})', time_range)
    return int(match.group(1)) * 60 + int(match.group(2)) if match else -1

