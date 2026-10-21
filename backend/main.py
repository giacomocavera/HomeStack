from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import os

import models, schemas, crud, ai, printer
from database import engine, get_db

from dotenv import load_dotenv
load_dotenv()

models.Base.metadata.create_all(bind=engine)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE locations ADD COLUMN location_type VARCHAR DEFAULT 'box'"))
        conn.commit()
    except Exception:
        pass

app = FastAPI(
    title="HomeStack Inventory API",
    version="1.0.0",
    root_path="/api",
)

cors_env = os.getenv("CORS_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()] if cors_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/locations/", response_model=schemas.Location, tags=["Locations"])
def create_location(location: schemas.LocationCreate, db: Session = Depends(get_db)):
    return crud.create_location(db=db, location=location)

@app.get("/locations/", response_model=List[schemas.Location], tags=["Locations"])
def read_locations(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    return crud.get_locations(db, skip=skip, limit=limit)

@app.put("/locations/{location_id}", response_model=schemas.Location, tags=["Locations"])
def update_location(location_id: int, location: schemas.LocationUpdate, db: Session = Depends(get_db)):
    db_location = crud.update_location(db=db, location_id=location_id, location=location)
    if db_location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return db_location

@app.delete("/locations/{location_id}", tags=["Locations"])
def delete_location(location_id: int, db: Session = Depends(get_db)):
    db_location = crud.delete_location(db=db, location_id=location_id)
    if db_location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return {"message": "Location deleted successfully"}

@app.get("/locations/{location_id}/items", response_model=List[schemas.Item], tags=["Locations"])
def get_location_items(location_id: int, db: Session = Depends(get_db)):
    return crud.get_items_by_location(db=db, location_id=location_id)

@app.get("/locations/{location_id}/print-payload/", tags=["Hardware"])
def get_location_print_payload(location_id: int, db: Session = Depends(get_db)):
    db_loc = crud.get_location(db=db, location_id=location_id)
    if db_loc is None:
        raise HTTPException(status_code=404, detail="Location not found")

    parent_name = ""
    if db_loc.parent_id:
        parent = crud.get_location(db=db, location_id=db_loc.parent_id)
        if parent:
            parent_name = f"In: {parent.name}"

    qr_data = db_loc.qr_code or f"BOX-{db_loc.id}"
    return printer.get_print_payload(
        db=db,
        entity_id=db_loc.id,
        entity_name=db_loc.name,
        qr_data=qr_data,
        subtitle=parent_name or db_loc.location_type.upper(),
        prefix="loc"
    )


@app.post("/items/", response_model=schemas.Item, tags=["Items"])
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    return crud.create_item(db=db, item=item)

@app.get("/items/", response_model=List[schemas.Item], tags=["Items"])
def read_items(skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    return crud.get_items(db, skip=skip, limit=limit)

@app.get("/items/search/", response_model=List[schemas.Item], tags=["Items"])
def search_items(q: str, db: Session = Depends(get_db)):
    return crud.search_items(db=db, query=q)

@app.put("/items/{item_id}", response_model=schemas.Item, tags=["Items"])
def update_item(item_id: int, item: schemas.ItemUpdate, db: Session = Depends(get_db)):
    db_item = crud.update_item(db=db, item_id=item_id, item=item)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@app.delete("/items/{item_id}", tags=["Items"])
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = crud.delete_item(db=db, item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}

@app.get("/items/{item_id}/print-payload/", tags=["Hardware"])
def get_item_print_payload(item_id: int, db: Session = Depends(get_db)):
    db_item = crud.get_item(db=db, item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    qr_data = db_item.qr_code or f"ITM-{db_item.id}"
    return printer.get_print_payload(
        db=db,
        entity_id=db_item.id,
        entity_name=db_item.name,
        qr_data=qr_data,
        subtitle=f"Qty: {db_item.quantity}",
        prefix="item"
    )


@app.get("/scan/{qr_code}", tags=["Search"])
def scan_lookup(qr_code: str, db: Session = Depends(get_db)):
    item = crud.get_item_by_qr(db, qr_code)
    if item:
        return {"entity_type": "item", "data": item}

    location = crud.get_location_by_qr(db, qr_code)
    if location:
        items = crud.get_items_by_location(db, location.id)
        return {"entity_type": "location", "data": location, "contained_items": items}

    raise HTTPException(status_code=404, detail="Nothing found for this QR token")


@app.post("/ai/analyze-image/", tags=["AI"])
async def analyze_item_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        image_bytes = await file.read()
        mime_type = file.content_type

        if not mime_type or not mime_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="The uploaded file must be an image.")

        return ai.analyze_image_with_gemini(
            db=db,
            image_bytes=image_bytes,
            mime_type=mime_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")


@app.get("/settings/", response_model=schemas.SettingsResponse, tags=["Settings"])
def get_settings(db: Session = Depends(get_db)):
    api_key = crud.get_setting_value(db, "gemini_api_key") or os.getenv("GEMINI_API_KEY", "")
    model = crud.get_setting_value(db, "gemini_model") or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    print_enabled_str = crud.get_setting_value(db, "print_enabled", "true")
    print_enabled = print_enabled_str.lower() == "true"
    
    printer_transport = crud.get_setting_value(db, "printer_transport", "ble")
    printer_language = crud.get_setting_value(db, "printer_language", "fichero")
    
    label_width_str = crud.get_setting_value(db, "label_width", "40")
    label_width = int(label_width_str) if label_width_str.isdigit() else 40
    
    label_height_str = crud.get_setting_value(db, "label_height", "15")
    label_height = int(label_height_str) if label_height_str.isdigit() else 15
    
    printer_ip = crud.get_setting_value(db, "printer_ip", "")
    printer_ble_name_prefix = crud.get_setting_value(db, "printer_ble_name_prefix", "FICHERO,D11")

    return {
        "gemini_api_key": api_key,
        "gemini_model": model,
        "available_models": ai.AVAILABLE_MODELS,
        "print_enabled": print_enabled,
        "printer_transport": printer_transport,
        "printer_language": printer_language,
        "label_width": label_width,
        "label_height": label_height,
        "printer_ip": printer_ip,
        "printer_ble_name_prefix": printer_ble_name_prefix
    }

@app.post("/settings/", response_model=schemas.SettingsResponse, tags=["Settings"])
def update_settings(payload: schemas.SettingsUpdate, db: Session = Depends(get_db)):
    if payload.gemini_api_key is not None:
        crud.set_setting_value(db, "gemini_api_key", payload.gemini_api_key.strip())
    if payload.gemini_model is not None:
        crud.set_setting_value(db, "gemini_model", payload.gemini_model.strip())

    if payload.print_enabled is not None:
        crud.set_setting_value(db, "print_enabled", "true" if payload.print_enabled else "false")
    if payload.printer_transport is not None:
        crud.set_setting_value(db, "printer_transport", payload.printer_transport.strip())
    if payload.printer_language is not None:
        crud.set_setting_value(db, "printer_language", payload.printer_language.strip())
    if payload.label_width is not None:
        crud.set_setting_value(db, "label_width", str(payload.label_width))
    if payload.label_height is not None:
        crud.set_setting_value(db, "label_height", str(payload.label_height))
    if payload.printer_ip is not None:
        crud.set_setting_value(db, "printer_ip", payload.printer_ip.strip())
    if payload.printer_ble_name_prefix is not None:
        crud.set_setting_value(db, "printer_ble_name_prefix", payload.printer_ble_name_prefix.strip())

    return get_settings(db=db)