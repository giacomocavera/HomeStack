import os
import base64
import socket
import io
import qrcode
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session
import crud
from fastapi import HTTPException

def get_scalable_font(size: int, bold: bool = False):
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
    ]
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()

def wrap_text_to_lines(text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int = 2) -> list[str]:
    words = text.split()
    if not words:
        return []

    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
            if len(lines) >= max_lines:
                break

    if current_line and len(lines) < max_lines:
        lines.append(current_line)

    return lines

def generate_label_image(entity_name: str, qr_data: str, subtitle: str = "", width_mm: int = 40, height_mm: int = 15) -> Image.Image:

    DPI_DOTS_PER_MM = 8
    width_px = ((int(width_mm * DPI_DOTS_PER_MM) + 7) // 8) * 8
    height_px = int(height_mm * DPI_DOTS_PER_MM)

    label_img = Image.new('RGB', (width_px, height_px), color='white')
    draw = ImageDraw.Draw(label_img)

    qr_side = max(16, height_px - 16)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=max(1, qr_side // 25),
        border=1,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    qr_img = qr_img.resize((qr_side, qr_side))

    left_margin = int(width_px * 0.05)
    qr_y = (height_px - qr_side) // 2
    label_img.paste(qr_img, (left_margin, qr_y))

    text_x = left_margin + qr_side + int(width_px * 0.03)
    max_text_width = width_px - text_x - int(width_px * 0.03)

    font_title_size = max(10, int(height_px * 0.22))
    font_sub_size = max(8, int(height_px * 0.16))

    font_title = get_scalable_font(font_title_size, bold=True)
    font_sub = get_scalable_font(font_sub_size, bold=False)

    name_lines = wrap_text_to_lines(entity_name, font_title, max_text_width, max_lines=2)
    sub_line = subtitle if subtitle else qr_data

    line_height_title = int(font_title_size * 1.2)
    line_height_sub = int(font_sub_size * 1.2)
    spacing = 2

    total_text_height = (len(name_lines) * line_height_title) + line_height_sub + spacing
    start_y = max(2, (height_px - total_text_height) // 2)

    current_y = start_y
    for line in name_lines:
        draw.text((text_x, current_y), line, fill="black", font=font_title)
        current_y += line_height_title

    current_y += spacing
    draw.text((text_x, current_y), sub_line[:24], fill="black", font=font_sub)

    return label_img.convert('1')

def image_to_raster_bytes(img: Image.Image) -> tuple[bytearray, int, int, int]:
    width = img.width
    height = img.height
    bytes_per_row = width // 8

    raster = bytearray()
    for y in range(height):
        row_byte = 0
        bit_count = 0
        for x in range(width):
            pixel = img.getpixel((x, y))
            bit = 1 if pixel == 0 else 0
            row_byte = (row_byte << 1) | bit
            bit_count += 1
            if bit_count == 8:
                raster.append(row_byte)
                row_byte = 0
                bit_count = 0
    return raster, width, height, bytes_per_row

def encode_fichero(img: Image.Image) -> bytearray:
    rotated = img.rotate(90, expand=True)
    raster, width, height, bytes_per_row = image_to_raster_bytes(rotated)

    stream = bytearray()
    stream.extend(b"\x00" * 12)
    stream.extend(bytes([0x10, 0xFF, 0x10, 0x00, 0x01]))
    stream.extend(bytes([0x10, 0xFF, 0x84, 0x00]))
    stream.extend(bytes([0x10, 0xFF, 0xFE, 0x01]))

    yl = height & 0xFF
    yh = (height >> 8) & 0xFF
    stream.extend(bytes([0x1D, 0x76, 0x30, 0x00, bytes_per_row, 0x00, yl, yh]))
    stream.extend(raster)
    stream.extend(bytes([0x1D, 0x0C]))
    stream.extend(bytes([0x10, 0xFF, 0xFE, 0x45]))
    return stream

def encode_escpos(img: Image.Image) -> bytearray:
    raster, width, height, bytes_per_row = image_to_raster_bytes(img)
    stream = bytearray()
    stream.extend(b"\x1B\x40")  # Initialize printer
    
    xl = bytes_per_row & 0xFF
    xh = (bytes_per_row >> 8) & 0xFF
    yl = height & 0xFF
    yh = (height >> 8) & 0xFF
    
    stream.extend(bytes([0x1D, 0x76, 0x30, 0x00, xl, xh, yl, yh]))
    stream.extend(raster)
    stream.extend(b"\x1D\x56\x41\x00")
    return stream

def encode_tspl(img: Image.Image, width_mm: int, height_mm: int) -> bytearray:
    raster, width, height, bytes_per_row = image_to_raster_bytes(img)
    header = f"SIZE {width_mm} mm, {height_mm} mm\r\nGAP 2 mm,0 mm\r\nDIRECTION 1\r\nCLS\r\nBITMAP 0,0,{bytes_per_row},{height},0,".encode('ascii')
    footer = b"\r\nPRINT 1,1\r\n"
    return bytearray(header + raster + footer)


def print_to_network(ip_address: str, payload: bytearray, port: int = 9100) -> bool:
    host = ip_address.split(":")[0].strip()
    if ":" in ip_address:
        try:
            port = int(ip_address.split(":")[1].strip())
        except ValueError:
            port = 9100

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5.0)
        s.connect((host, port))
        s.sendall(payload)
    return True


def get_print_payload(db: Session, entity_id: int, entity_name: str, qr_data: str, subtitle: str = "", prefix: str = "item") -> dict:
    transport = crud.get_setting_value(db, "printer_transport", "ble")
    language = crud.get_setting_value(db, "printer_language", "fichero")
    
    width_mm_str = crud.get_setting_value(db, "label_width", "40")
    height_mm_str = crud.get_setting_value(db, "label_height", "15")
    width_mm = int(width_mm_str) if width_mm_str.isdigit() else 40
    height_mm = int(height_mm_str) if height_mm_str.isdigit() else 15
    
    printer_ip = crud.get_setting_value(db, "printer_ip", "")
    ble_prefix = crud.get_setting_value(db, "printer_ble_name_prefix", "FICHERO,D11")

    img = generate_label_image(entity_name, qr_data, subtitle, width_mm=width_mm, height_mm=height_mm)

    if transport == "browser" or language == "pdf":
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return {
            "status": "ok",
            "transport": "browser",
            "image_base64": f"data:image/png;base64,{img_str}",
            "width_mm": width_mm,
            "height_mm": height_mm
        }

    if language == "escpos":
        stream = encode_escpos(img)
    elif language == "tspl":
        stream = encode_tspl(img, width_mm, height_mm)
    else:
        stream = encode_fichero(img)

    if transport == "network":
        if not printer_ip:
            raise HTTPException(status_code=400, detail="Missing IP address. Check settings.")
        try:
            print_to_network(printer_ip, stream)
            return {
                "status": "ok",
                "transport": "network",
                "message": f"Printed successfully to {printer_ip}"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Unable to reach {printer_ip}. (Detail: {str(e)})")

    CHUNK_SIZE = 200
    chunks = []
    for i in range(0, len(stream), CHUNK_SIZE):
        chunk_data = stream[i : i + CHUNK_SIZE]
        chunks.append(base64.b64encode(chunk_data).decode('utf-8'))

    return {
        "status": "ok",
        "transport": "ble",
        "chunks": chunks,
        "ble_prefix": ble_prefix
    }

def delete_label_image(entity_id: int, prefix: str = "item") -> bool:
    return True