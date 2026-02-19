"""
Shared QR code image generation for Kodi addon authorization dialogs.

Tries three strategies in order so the feature works across environments:
  1. Local `qrcode` library  — offline, best quality, needs Pillow
  2. Local `segno` library   — offline, lightweight pure-Python
  3. api.qrserver.com API    — network fallback (always available during auth)
"""
import os


def generate_qr_image(url, path):
    """
    Write a QR code PNG encoding *url* to *path*.
    Returns True on success, False if all strategies fail.
    """
    # 1. qrcode + Pillow
    try:
        import qrcode
        img = qrcode.make(url)
        img.save(path)
        if os.path.getsize(path) > 0:
            return True
    except Exception:
        pass

    # 2. segno (pure-Python, no Pillow required)
    try:
        import segno
        qr = segno.make_qr(url, error='m')
        qr.save(path, scale=10, border=2)
        if os.path.getsize(path) > 0:
            return True
    except Exception:
        pass

    # 3. Free web API — network is already active during auth flows
    try:
        import urllib.request
        import urllib.parse
        encoded = urllib.parse.quote(url, safe='')
        api_url = f'https://api.qrserver.com/v1/create-qr-code/?size=400x400&margin=20&data={encoded}'
        urllib.request.urlretrieve(api_url, path)
        with open(path, 'rb') as fh:
            if fh.read(4) == b'\x89PNG':
                return True
    except Exception:
        pass

    return False
