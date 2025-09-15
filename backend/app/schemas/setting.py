from pydantic import BaseModel, ConfigDict

class SettingBase(BaseModel):
    key: str
    value: str

class SettingCreate(SettingBase):
    pass

class Setting(SettingBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
