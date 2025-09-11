from pydantic import BaseModel

class SettingBase(BaseModel):
    key: str
    value: str

class SettingCreate(SettingBase):
    pass

class Setting(SettingBase):
    id: int

    class Config:
        orm_mode = True
