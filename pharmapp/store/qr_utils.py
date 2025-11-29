"""
QR Code Generation Utilities for PharmApp
Handles QR code generation for items, receipts, and labels
"""
import qrcode
import io
import base64
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings


def generate_qr_code(data, size=10, border=2):
    """
    Generate a QR code from the provided data

    Args:
        data: String data to encode in QR code
        size: Size of QR code boxes (default 10)
        border: Border size in boxes (default 2)

    Returns:
        PIL Image object of the QR code
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    return img


def generate_qr_code_base64(data, size=10, border=2):
    """
    Generate a QR code and return as base64 encoded string for embedding in HTML

    Args:
        data: String data to encode in QR code
        size: Size of QR code boxes (default 10)
        border: Border size in boxes (default 2)

    Returns:
        Base64 encoded string of QR code image
    """
    img = generate_qr_code(data, size, border)

    # Convert to base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return f"data:image/png;base64,{img_str}"


def generate_item_qr_data(item, mode='retail'):
    """
    Generate QR code data string for an item

    Args:
        item: Item or WholesaleItem object
        mode: 'retail' or 'wholesale'

    Returns:
        Formatted string containing item information
    """
    # Primary: Use barcode if available
    if hasattr(item, 'barcode') and item.barcode:
        return item.barcode

    # Fallback: Use structured data
    data = {
        'id': item.id,
        'name': item.name,
        'mode': mode,
    }

    # Format as simple string (can be parsed by scanner)
    qr_string = f"PHARM-{mode.upper()}-{item.id}"

    return qr_string


def generate_receipt_qr_data(receipt, mode='retail'):
    """
    Generate QR code data string for a receipt

    Args:
        receipt: Receipt or WholesaleReceipt object
        mode: 'retail' or 'wholesale'

    Returns:
        Formatted string containing receipt information
    """
    # Format: RECEIPT-MODE-ID-RECEIPTNUM
    qr_string = f"RECEIPT-{mode.upper()}-{receipt.id}-{receipt.receipt_no}"
    return qr_string


def generate_item_label_with_qr(item, mode='retail', include_price=True):
    """
    Generate a printable label image with QR code and item details

    Args:
        item: Item or WholesaleItem object
        mode: 'retail' or 'wholesale'
        include_price: Whether to include price on label

    Returns:
        PIL Image object of the complete label
    """
    # Generate QR code
    qr_data = generate_item_qr_data(item, mode)
    qr_img = generate_qr_code(qr_data, size=8, border=1)

    # Create label image (400x250 pixels - standard label size)
    label_width = 400
    label_height = 250
    label = Image.new('RGB', (label_width, label_height), 'white')
    draw = ImageDraw.Draw(label)

    # Try to load a font, fallback to default if not available
    try:
        title_font = ImageFont.truetype("arial.ttf", 20)
        detail_font = ImageFont.truetype("arial.ttf", 14)
        price_font = ImageFont.truetype("arialbd.ttf", 24)
    except:
        title_font = ImageFont.load_default()
        detail_font = ImageFont.load_default()
        price_font = ImageFont.load_default()

    # Position QR code on the left
    qr_size = 150
    qr_img_resized = qr_img.resize((qr_size, qr_size))
    label.paste(qr_img_resized, (20, 50))

    # Add item details on the right
    text_x = 190
    y_offset = 40

    # Item name (truncate if too long)
    name = item.name[:30] + "..." if len(item.name) > 30 else item.name
    draw.text((text_x, y_offset), name, fill='black', font=title_font)
    y_offset += 35

    # Brand
    if hasattr(item, 'brand') and item.brand:
        brand_text = f"Brand: {item.brand[:20]}"
        draw.text((text_x, y_offset), brand_text, fill='black', font=detail_font)
        y_offset += 25

    # Dosage form
    if hasattr(item, 'dosage_form') and item.dosage_form:
        dosage_text = f"Form: {item.dosage_form[:20]}"
        draw.text((text_x, y_offset), dosage_text, fill='black', font=detail_font)
        y_offset += 25

    # Stock
    if hasattr(item, 'stock'):
        stock_text = f"Stock: {item.stock}"
        draw.text((text_x, y_offset), stock_text, fill='black', font=detail_font)
        y_offset += 25

    # Price
    if include_price and hasattr(item, 'price'):
        price_text = f"₦{item.price:,.2f}"
        draw.text((text_x, y_offset), price_text, fill='#007bff', font=price_font)
        y_offset += 35

    # Add barcode text at bottom if available
    if hasattr(item, 'barcode') and item.barcode:
        barcode_text = f"Barcode: {item.barcode}"
        draw.text((20, 220), barcode_text, fill='gray', font=detail_font)

    # Add border
    draw.rectangle([(0, 0), (label_width-1, label_height-1)], outline='black', width=2)

    return label


def generate_item_label_base64(item, mode='retail', include_price=True):
    """
    Generate a printable label and return as base64 encoded string

    Args:
        item: Item or WholesaleItem object
        mode: 'retail' or 'wholesale'
        include_price: Whether to include price on label

    Returns:
        Base64 encoded string of label image
    """
    img = generate_item_label_with_qr(item, mode, include_price)

    # Convert to base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return f"data:image/png;base64,{img_str}"
