import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List
from sqlalchemy.orm import Session
import crud
from database import SessionLocal

AVAILABLE_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest"
]

class MetadataField(BaseModel):
    key: str = Field(description="The attribute name, e.g. 'brand', 'color', 'voltage', 'package'.")
    value: str = Field(description="The attribute value, e.g. 'Arduino', 'Blue', '5V', 'SMD'.")

class AIItemExtraction(BaseModel):
    name: str = Field(
        description="A short, concise, generic name (2 to 4 words maximum). Never include package sizes, voltages, or part numbers here."
    )
    description: str = Field(description="A brief description of what the item is and its potential use.")
    quantity: int = Field(description="Estimated quantity. 1 for unique items, or estimated count for bulk items.")
    is_consumable: bool = Field(description="True if consumable or bulk components.")
    metadata_fields: List[MetadataField] = Field(description="All technical specifications must be placed here.")

def get_gemini_client_and_model(db: Session = None):
    api_key = ""
    model_name = ""

    if db is not None:
        try:
            api_key = crud.get_setting_value(db, "gemini_api_key")
            model_name = crud.get_setting_value(db, "gemini_model")
        except Exception:
            pass

    api_key = api_key or os.getenv("GEMINI_API_KEY", "")
    model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    if not api_key:
        raise ValueError("Gemini API key is not configured. Please set it in Settings.")

    client = genai.Client(api_key=api_key)
    return client, model_name

def analyze_image_with_gemini(*args, **kwargs) -> dict:
    db = kwargs.get("db")
    image_bytes = kwargs.get("image_bytes")
    mime_type = kwargs.get("mime_type")

    if args:
        if isinstance(args[0], bytes):
            image_bytes = args[0]
            if len(args) > 1:
                mime_type = args[1]
            if len(args) > 2:
                db = args[2]
        else:
            db = args[0]
            if len(args) > 1:
                image_bytes = args[1]
            if len(args) > 2:
                mime_type = args[2]

    if not image_bytes or not mime_type:
        raise ValueError("Both image_bytes and mime_type are required.")

    close_db_session = False
    if db is None:
        db = SessionLocal()
        close_db_session = True

    try:
        client, model_name = get_gemini_client_and_model(db)

        prompt = """
        You are an expert warehouse manager for an engineering and maker workspace.
        Analyze the provided image of an item.
        Identify the item and extract all useful information to catalog it in an inventory system.
        Pay attention to brands, part numbers, text printed on packaging, and object type.
        IMPORTANT NAMING RULE:
        Keep the 'name' field strictly short and generic (e.g. 'Ceramic Capacitor', 'Hex Screw M3', 'OLED Display').
        Move ALL specific parameters, values, voltages, chipsets, or dimensions into 'metadata_fields'.

        Ignore codes that are not useful for identifying or sourcing the item.
        Do NOT extract or store:
        - Barcodes (EAN, UPC, GTIN, QR codes, etc.)
        """

        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIItemExtraction,
                temperature=0.2, 
            ),
        )

        extracted_data = AIItemExtraction.model_validate_json(response.text)
        result_dict = extracted_data.model_dump()
        
        flat_metadata = {field.key: field.value for field in extracted_data.metadata_fields}
        result_dict["metadata_fields"] = flat_metadata
        
        return result_dict

    finally:
        if close_db_session and db is not None:
            db.close()