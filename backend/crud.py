import random
from sqlalchemy.orm import Session
import models, schemas, printer


def generate_unique_location_id(db: Session) -> int:
    while True:
        candidate_id = random.randint(100000, 999999)
        existing = db.query(models.Location).filter(models.Location.id == candidate_id).first()
        if not existing:
            return candidate_id

def get_location(db: Session, location_id: int):
    return db.query(models.Location).filter(models.Location.id == location_id).first()

def get_location_by_qr(db: Session, qr_code: str):
    loc = db.query(models.Location).filter(models.Location.qr_code == qr_code).first()
    if loc:
        return loc

    normalized_id = qr_code.replace("BOX-", "").replace("LOC-", "").strip()
    if normalized_id.isdigit():
        return db.query(models.Location).filter(models.Location.id == int(normalized_id)).first()

    return None

def get_locations(db: Session, skip: int = 0, limit: int = 200):
    return db.query(models.Location).offset(skip).limit(limit).all()

def create_location(db: Session, location: schemas.LocationCreate):
    loc_data = location.model_dump()
    db_location = models.Location(**loc_data)
    db_location.id = generate_unique_location_id(db)

    if not db_location.qr_code:
        prefix = "BOX" if db_location.location_type in ["box", "drawer"] else "LOC"
        db_location.qr_code = f"{prefix}-{db_location.id}"

    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location

def update_location(db: Session, location_id: int, location: schemas.LocationUpdate):
    db_location = get_location(db, location_id)
    if db_location:
        update_data = location.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_location, key, value)
        db.commit()
        db.refresh(db_location)
    return db_location

def delete_location(db: Session, location_id: int):
    db_location = get_location(db, location_id)
    if db_location:
        printer.delete_label_image(location_id, prefix="loc")
        db.query(models.Item).filter(models.Item.location_id == location_id).update({"location_id": None})
        db.delete(db_location)
        db.commit()
    return db_location


def generate_unique_item_id(db: Session) -> int:
    while True:
        candidate_id = random.randint(100000, 999999)
        existing = db.query(models.Item).filter(models.Item.id == candidate_id).first()
        if not existing:
            return candidate_id

def get_item(db: Session, item_id: int):
    return db.query(models.Item).filter(models.Item.id == item_id).first()

def get_item_by_qr(db: Session, qr_code: str):
    item = db.query(models.Item).filter(models.Item.qr_code == qr_code).first()
    if item:
        return item

    normalized_id = qr_code.replace("ITM-", "").strip()
    if normalized_id.isdigit():
        return db.query(models.Item).filter(models.Item.id == int(normalized_id)).first()

    return None

def get_items(db: Session, skip: int = 0, limit: int = 500):
    return db.query(models.Item).offset(skip).limit(limit).all()

def get_items_by_location(db: Session, location_id: int):
    return db.query(models.Item).filter(models.Item.location_id == location_id).all()

def create_item(db: Session, item: schemas.ItemCreate):
    item_data = item.model_dump()
    db_item = models.Item(**item_data)
    db_item.id = generate_unique_item_id(db)

    if not db_item.qr_code:
        db_item.qr_code = f"ITM-{db_item.id}"

    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def update_item(db: Session, item_id: int, item: schemas.ItemUpdate):
    db_item = get_item(db, item_id)
    if db_item:
        update_data = item.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_item, key, value)
        db.commit()
        db.refresh(db_item)
    return db_item

def delete_item(db: Session, item_id: int):
    db_item = get_item(db, item_id)
    if db_item:
        printer.delete_label_image(item_id, prefix="item")
        db.delete(db_item)
        db.commit()
    return db_item

def search_items(db: Session, query: str):
    search_term = f"%{query}%"
    return db.query(models.Item).filter(
        models.Item.name.ilike(search_term) |
        models.Item.description.ilike(search_term) |
        models.Item.qr_code.ilike(search_term)
    ).all()


def get_setting_value(db: Session, key: str, default: str = "") -> str:
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    return setting.value if setting and setting.value else default

def set_setting_value(db: Session, key: str, value: str):
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    if not setting:
        setting = models.Setting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value
    db.commit()
    db.refresh(setting)
    return setting