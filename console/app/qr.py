# app/qr.py — Génération de QR code (pour le lien d'activation)
"""
Le lien d'activation est affiché en QR code pour être transmis en main propre
(impression ou écran), sans passer par un service tiers de messagerie.
"""
import base64
import io
import qrcode


def qr_data_uri(text: str) -> str:
    """Génère un QR code PNG encodé en data URI (affichable en <img>)."""
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
