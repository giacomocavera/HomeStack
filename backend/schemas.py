from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class LocationBase(BaseModel):
    name: str
    location_type: str = "box"
    description: Optional[str] = None
    parent_id: Optional[int] = None
    qr_code: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    location_type: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    qr_code: Optional[str] = None

class Location(LocationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    location_id: Optional[int] = None
    quantity: int = 1
    is_consumable: bool = False
    qr_code: Optional[str] = None
    source_url: Optional[str] = None
    metadata_fields: Optional[Dict[str, Any]] = None

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location_id: Optional[int] = None
    quantity: Optional[int] = None
    is_consumable: Optional[bool] = None
    qr_code: Optional[str] = None
    source_url: Optional[str] = None
    metadata_fields: Optional[Dict[str, Any]] = None

class Item(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    
    print_enabled: Optional[bool] = None
    printer_transport: Optional[str] = None
    printer_language: Optional[str] = None
    label_width: Optional[int] = None
    label_height: Optional[int] = None
    printer_ip: Optional[str] = None
    printer_ble_name_prefix: Optional[str] = None 

class SettingsResponse(BaseModel):
    gemini_api_key: str
    gemini_model: str
    available_models: List[str]
    
    print_enabled: bool
    printer_transport: str
    printer_language: str
    label_width: int
    label_height: int
    printer_ip: str
    printer_ble_name_prefix: str