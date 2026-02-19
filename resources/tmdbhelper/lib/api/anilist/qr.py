"""QR code dialog for AniList OAuth authorization."""
import os
import tempfile
import xbmcgui


# Kodi xbmcgui alignment constants
_ALIGN_CENTER = 6  # XBFONT_CENTER_X (2) | XBFONT_CENTER_Y (4)


def _generate_qr_image(url, path):
    """
    Try to generate a QR code PNG at *path* encoding *url*.
    Attempts three strategies in order:
      1. Local `qrcode` library (no network, best quality)
      2. Local `segno` library (no network, lightweight)
      3. Free web API — api.qrserver.com (network required)
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

    # 2. segno
    try:
        import segno
        qr = segno.make_qr(url, error='m')
        qr.save(path, scale=10, border=2)
        if os.path.getsize(path) > 0:
            return True
    except Exception:
        pass

    # 3. Web API (fallback — network already in use during auth)
    try:
        import urllib.request
        import urllib.parse
        encoded = urllib.parse.quote(url, safe='')
        api_url = f'https://api.qrserver.com/v1/create-qr-code/?size=400x400&margin=20&data={encoded}'
        urllib.request.urlretrieve(api_url, path)
        with open(path, 'rb') as f:
            header = f.read(4)
        if header == b'\x89PNG':
            return True
    except Exception:
        pass

    return False


class QRCodeDialog(xbmcgui.WindowDialog):
    """
    Kodi overlay dialog that displays a QR code for AniList OAuth.

    Shows a scannable QR (if generation succeeds) plus text instructions.
    The user scans with their phone, approves on AniList, then copies the
    displayed access_token and pastes it into the subsequent input dialog.
    """

    _ACTION_BACK = 10    # ACTION_PREVIOUS_MENU
    _ACTION_NAV_BACK = 92  # ACTION_NAV_BACK

    def __init__(self, auth_url):
        super().__init__()
        self._auth_url = auth_url
        self._qr_path = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        sw = self.getWidth()
        sh = self.getHeight()
        cx = sw // 2  # horizontal centre

        # Generate QR to a temp PNG
        fd, self._qr_path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        has_qr = _generate_qr_image(self._auth_url, self._qr_path)

        # QR image dimensions — roughly 1/3 of the shorter screen dimension
        qr_size = min(sw, sh) // 3

        # Vertical layout anchors
        top_y = sh // 8
        title_y = top_y
        content_y = title_y + 55

        # Title
        self.addControl(xbmcgui.ControlLabel(
            0, title_y, sw, 50,
            'Authorize AniList',
            alignment=_ALIGN_CENTER,
        ))

        if has_qr:
            # --- QR image ---
            qr_x = cx - qr_size // 2
            qr_ctrl = xbmcgui.ControlImage(qr_x, content_y, qr_size, qr_size, self._qr_path)
            self.addControl(qr_ctrl)

            # Step 1: scan
            step1_y = content_y + qr_size + 15
            self.addControl(xbmcgui.ControlLabel(
                0, step1_y, sw, 38,
                '[B]Step 1:[/B]  Scan the QR code with your phone',
                alignment=_ALIGN_CENTER,
            ))

            # Step 2: approve
            step2_y = step1_y + 42
            self.addControl(xbmcgui.ControlLabel(
                0, step2_y, sw, 38,
                '[B]Step 2:[/B]  Log in to AniList and tap [B]Authorize[/B]',
                alignment=_ALIGN_CENTER,
            ))

            # Step 3: copy token
            step3_y = step2_y + 42
            self.addControl(xbmcgui.ControlLabel(
                0, step3_y, sw, 38,
                '[B]Step 3:[/B]  Copy the [B]access_token[/B] shown and paste it in the next dialog',
                alignment=_ALIGN_CENTER,
            ))

            btn_y = step3_y + 58

        else:
            # --- Text-only fallback ---
            self.addControl(xbmcgui.ControlLabel(
                0, content_y, sw, 38,
                'Visit this URL on your phone to authorize AniList:',
                alignment=_ALIGN_CENTER,
            ))
            url_y = content_y + 50
            self.addControl(xbmcgui.ControlLabel(
                60, url_y, sw - 120, 80,
                f'[B]{self._auth_url}[/B]',
                alignment=_ALIGN_CENTER,
            ))
            note_y = url_y + 90
            self.addControl(xbmcgui.ControlLabel(
                0, note_y, sw, 38,
                'After approving, copy the [B]access_token[/B] and paste it in the next dialog',
                alignment=_ALIGN_CENTER,
            ))
            btn_y = note_y + 58

        # OK / Continue button
        btn_w = 180
        self._btn_ok = xbmcgui.ControlButton(
            cx - btn_w // 2, btn_y, btn_w, 48,
            'Continue',
        )
        self.addControl(self._btn_ok)
        self.setFocus(self._btn_ok)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def onControl(self, control):
        if control == self._btn_ok:
            self.close()

    def onAction(self, action):
        if action.getId() in (self._ACTION_BACK, self._ACTION_NAV_BACK):
            self.close()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _cleanup(self):
        if self._qr_path:
            try:
                os.remove(self._qr_path)
            except OSError:
                pass
            self._qr_path = None

    def __del__(self):
        self._cleanup()


def show_qr_auth_dialog(auth_url):
    """
    Display a blocking QR code dialog for AniList OAuth authorization.
    Generates a QR encoding *auth_url* and shows step-by-step instructions.
    Cleans up the temp PNG after the dialog is dismissed.
    """
    dialog = QRCodeDialog(auth_url)
    dialog.show()
    dialog.doModal()
    dialog._cleanup()
    del dialog
