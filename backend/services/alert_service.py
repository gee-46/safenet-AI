"""
SafeNet AI – Alert Service
Multi-channel alert dispatcher: WhatsApp, SMS, push notifications.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from backend.core.config import get_settings
from backend.db.models import Alert

settings = get_settings()

# Scam type → human-readable alert header
SCAM_ALERT_HEADERS = {
    "digital_arrest": "🚨 Digital Arrest Scam Detected",
    "kyc_update": "🚨 KYC / OTP Fraud Detected",
    "loan_fraud": "🚨 Fake Loan Scam Detected",
    "investment": "🚨 Investment Fraud Detected",
    "lottery": "🚨 Lottery Scam Detected",
    "impersonation": "🚨 Impersonation Scam Detected",
    "romance": "🚨 Romance Scam Detected",
    "tech_support": "🚨 Tech Support Scam Detected",
    "unknown": "🚨 Suspicious Call Detected",
}


def _build_scam_alert_message(
    scam_type: str,
    confidence: float,
    recommended_action: str,
) -> str:
    header = SCAM_ALERT_HEADERS.get(scam_type, SCAM_ALERT_HEADERS["unknown"])
    confidence_pct = int(confidence * 100)
    return (
        f"{header}\n\n"
        f"⚡ Confidence: {confidence_pct}%\n\n"
        f"📌 What to do:\n{recommended_action}\n\n"
        f"📞 Call 1930 (National Cybercrime Helpline) immediately.\n"
        f"🌐 Report at: cybercrime.gov.in\n\n"
        f"—SafeNet AI 🔒"
    )


async def _send_twilio_whatsapp(phone: str, message: str) -> Optional[str]:
    """Send WhatsApp message via Twilio. Returns message SID or None."""
    if not (settings.twilio_account_sid and settings.twilio_auth_token):
        print(f"[AlertService] Twilio not configured — skipping WhatsApp to {phone}")
        return None
    try:
        from twilio.rest import Client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        to_number = phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}"
        msg = client.messages.create(
            body=message,
            from_=settings.twilio_whatsapp_from,
            to=to_number,
        )
        return msg.sid
    except Exception as e:
        print(f"[AlertService] WhatsApp send failed: {e}")
        return None


async def _send_twilio_sms(phone: str, message: str) -> Optional[str]:
    """Send SMS via Twilio. Returns message SID or None."""
    if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_sms_from):
        print(f"[AlertService] Twilio SMS not configured — skipping SMS to {phone}")
        return None
    try:
        from twilio.rest import Client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        msg = client.messages.create(
            body=message[:160],  # SMS max length
            from_=settings.twilio_sms_from,
            to=phone,
        )
        return msg.sid
    except Exception as e:
        print(f"[AlertService] SMS send failed: {e}")
        return None


async def send_alert(
    phone_number: str,
    alert_type: str,
    scam_type: str,
    confidence: float,
    recommended_action: str,
    db,
    channel: str = "whatsapp",
    language: str = "en",
) -> bool:
    """
    Send a fraud alert to a phone number.
    Persists alert record in DB. Returns True if sent successfully.

    Args:
        phone_number: E.164 phone number
        alert_type: scam_call | counterfeit | fraud_network
        scam_type: specific scam type
        confidence: detection confidence (0-1)
        recommended_action: action string to include in message
        db: async DB session
        channel: whatsapp | sms
        language: ISO 639-1 language code
    """
    message = _build_scam_alert_message(scam_type, confidence, recommended_action)
    alert_id = uuid.uuid4()
    twilio_sid = None
    delivered = False

    # Attempt delivery
    if channel == "whatsapp":
        twilio_sid = await _send_twilio_whatsapp(phone_number, message)
    elif channel == "sms":
        twilio_sid = await _send_twilio_sms(phone_number, message)

    if twilio_sid:
        delivered = True

    # Persist alert record regardless of delivery success (for audit trail)
    alert = Alert(
        id=alert_id,
        phone_number=phone_number,
        channel=channel,
        alert_type=alert_type,
        severity="high" if confidence >= 0.85 else "medium",
        message=message,
        message_language=language,
        reference_id=scam_type,
        delivered=delivered,
        delivered_at=datetime.utcnow() if delivered else None,
        twilio_sid=twilio_sid,
    )
    db.add(alert)

    print(
        f"[AlertService] Alert {alert_id} → {phone_number} "
        f"via {channel} | delivered={delivered} | sid={twilio_sid}"
    )
    return delivered


async def send_law_enforcement_alert(
    case_number: str,
    fraud_type: str,
    affected_states: list,
    estimated_victims: int,
    evidence_url: str,
    officer_phones: list,
    db,
) -> int:
    """
    Notify law enforcement officers of a new high-severity case.
    Returns number of successful deliveries.
    """
    message = (
        f"🔴 *SafeNet AI — New Fraud Case Alert*\n\n"
        f"Case: {case_number}\n"
        f"Type: {fraud_type.replace('_', ' ').title()}\n"
        f"States: {', '.join(affected_states)}\n"
        f"Est. Victims: {estimated_victims}\n\n"
        f"Evidence Package: {evidence_url}\n\n"
        f"Login to dashboard: https://safenet.ai/dashboard"
    )

    sent = 0
    for phone in officer_phones:
        sid = await _send_twilio_whatsapp(phone, message)
        if sid:
            sent += 1
            db.add(Alert(
                phone_number=phone,
                channel="whatsapp",
                alert_type="fraud_network",
                severity="critical",
                message=message,
                reference_id=case_number,
                delivered=True,
                delivered_at=datetime.utcnow(),
                twilio_sid=sid,
            ))

    return sent
