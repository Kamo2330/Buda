try:
    import qrcode
    from io import BytesIO
    from django.core.files.base import ContentFile
    from django.conf import settings
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False


def generate_qr_code(data, size=200):
    """Generate a QR code image for the given data"""
    if not QR_AVAILABLE:
        return None
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize image
    img = img.resize((size, size))
    
    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return ContentFile(buffer.getvalue(), name=f'qr_{data.replace("/", "_")}.png')


def generate_table_qr_code(table, base_url=None):
    """Generate QR code for a specific table"""
    if not QR_AVAILABLE:
        return None
        
    if not base_url:
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
    
    qr_data = f"{base_url}/{table.club.slug}/table/{table.number}/"
    return generate_qr_code(qr_data)
