from pydantic import BaseModel

class SenderRegisterRequest(BaseModel):
    full_name: str
    phone_number: str
    default_address: str
