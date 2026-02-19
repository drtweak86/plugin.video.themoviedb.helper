"""QR code dialog for Trakt device code authorization."""
import os
import tempfile
import xbmcgui
from tmdbhelper.lib.addon.qr import generate_qr_image


# Kodi xbmcgui alignment constants
_ALIGN_CENTER = 6   # XBFONT_CENTER_X (2) | XBFONT_CENTER_Y (4)
_ALIGN_LEFT = 0


class QRCodeDialog(xbmcgui.WindowDialog):
    """
    Kodi overlay dialog that displays a QR code for Trakt device auth.

    The QR encodes https://trakt.tv/activate/{user_code} so the user's phone
    browser opens the activation page with the code already pre-filled.
    The user_code is also shown in large text as a fallback.

    After scanning and approving on their phone, the user clicks Continue
    and the existing Trakt poller takes over (polling until auth is confirmed).
    """

    _ACTION_BACK = 10     # ACTION_PREVIOUS_MENU
    _ACTION_NAV_BACK = 92  # ACTION_NAV_BACK

    def __init__(self, activation_url, user_code):
        super().__init__()
        self._activation_url = activation_url
        self._user_code = user_code
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
        has_qr = generate_qr_image(self._activation_url, self._qr_path)

        # QR image size — roughly 1/3 of the shorter screen dimension
        qr_size = min(sw, sh) // 3

        top_y = sh // 8
        title_y = top_y
        content_y = title_y + 55

        # Title
        self.addControl(xbmcgui.ControlLabel(
            0, title_y, sw, 50,
            'Authorize Trakt',
            alignment=_ALIGN_CENTER,
        ))

        if has_qr:
            # --- QR image ---
            qr_x = cx - qr_size // 2
            qr_ctrl = xbmcgui.ControlImage(qr_x, content_y, qr_size, qr_size, self._qr_path)
            self.addControl(qr_ctrl)

            # User code displayed large below QR — visible without scanning
            code_y = content_y + qr_size + 10
            self.addControl(xbmcgui.ControlLabel(
                0, code_y, sw, 48,
                f'[B]{self._user_code}[/B]',
                alignment=_ALIGN_CENTER,
            ))

            # Step 1: scan
            step1_y = code_y + 54
            self.addControl(xbmcgui.ControlLabel(
                0, step1_y, sw, 38,
                '[B]Step 1:[/B]  Scan the QR code — or visit [B]trakt.tv/activate[/B] and enter the code above',
                alignment=_ALIGN_CENTER,
            ))

            # Step 2: approve
            step2_y = step1_y + 42
            self.addControl(xbmcgui.ControlLabel(
                0, step2_y, sw, 38,
                '[B]Step 2:[/B]  Log in to Trakt and click [B]Allow[/B]',
                alignment=_ALIGN_CENTER,
            ))

            # Step 3: continue
            step3_y = step2_y + 42
            self.addControl(xbmcgui.ControlLabel(
                0, step3_y, sw, 38,
                '[B]Step 3:[/B]  Click [B]Continue[/B] below — Kodi will wait until authorization is confirmed',
                alignment=_ALIGN_CENTER,
            ))

            btn_y = step3_y + 58

        else:
            # --- Text-only fallback ---
            self.addControl(xbmcgui.ControlLabel(
                0, content_y, sw, 38,
                'Visit [B]trakt.tv/activate[/B] on your phone and enter this code:',
                alignment=_ALIGN_CENTER,
            ))
            # Code in large bold text
            self.addControl(xbmcgui.ControlLabel(
                0, content_y + 50, sw, 60,
                f'[B]{self._user_code}[/B]',
                alignment=_ALIGN_CENTER,
            ))
            self.addControl(xbmcgui.ControlLabel(
                0, content_y + 120, sw, 38,
                'After clicking [B]Allow[/B] on Trakt, click [B]Continue[/B] below',
                alignment=_ALIGN_CENTER,
            ))
            btn_y = content_y + 178

        # Continue button
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


def show_qr_auth_dialog(activation_url, user_code):
    """
    Display a blocking Trakt QR authorization dialog.

    *activation_url* encodes https://trakt.tv/activate/{user_code} so
    the phone browser pre-fills the code.  *user_code* is also shown
    in large text for manual entry fallback.

    After the dialog is dismissed the caller should start the Trakt poller.
    """
    dialog = QRCodeDialog(activation_url, user_code)
    dialog.show()
    dialog.doModal()
    dialog._cleanup()
    del dialog
