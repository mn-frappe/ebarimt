# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Jinja utility functions for eBarimt
"""


def get_qr_code(data, size=200):
    """
    Generate QR code HTML from data
    Used in print formats for receipts
    """
    if not data:
        return ""

    import base64

    try:
        from io import BytesIO

        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return f'<img src="data:image/png;base64,{img_str}" width="{size}" height="{size}" />'

    except ImportError:
        # Fallback: return link to QR generation service
        import urllib.parse
        encoded = urllib.parse.quote(data)
        return f'<img src="https://chart.googleapis.com/chart?chs={size}x{size}&cht=qr&chl={encoded}" />'


def format_lottery_number(lottery):
    """Format lottery number for display"""
    if not lottery:
        return ""

    # Format as XXX-XXX-XXX if 9 digits
    lottery = str(lottery).strip()

    if len(lottery) == 9 and lottery.isdigit():
        return f"{lottery[:3]}-{lottery[3:6]}-{lottery[6:]}"

    return lottery
