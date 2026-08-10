import requests
import json
import base64
import logging
from django.utils import timezone
from .models import Mshiriki, SMSConfig, SMSLog

logger = logging.getLogger(__name__)


def _log_sms(mshiriki, ibada, sms_type, phone, message, status, error=None):
    """Hifadhi kumbukumbu ya SMS kwenye database (SMSLog)."""
    try:
        SMSLog.objects.create(
            mshiriki=mshiriki if mshiriki and mshiriki.pk else None,
            ibada=ibada if ibada and ibada.pk else None,
            type=sms_type,
            status=status,
            phone=phone,
            message=message,
            error=error,
        )
    except Exception as e:
        logger.error(f"Imeshindwa kuhifadhi SMSLog: {e}")


def send_single_sms(dest_phone, message, config, mshiriki=None, ibada=None, sms_type='INVITATION'):
    """
    Sends a single SMS using Beem SMS Gateway API (or mock mode if credentials are empty).
    Rekodi za SMS zinahifadhiwa kwenye SMSLog.
    """
    # If API keys are empty, fallback to Mock Mode
    if not config or not config.api_key or not config.secret_key or config.api_key == "MOCK_KEY":
        # Mock mode: Log SMS details to standard log or console AND save to DB
        print(f"--- [MOCK SMS TO {dest_phone}] ---")
        print(f"Sender ID: {config.sender_id if config else 'KANDA'}")
        print(f"Message: {message}")
        print("---------------------------------")
        _log_sms(mshiriki, ibada, sms_type, dest_phone, message, 'MOCKUP')
        # Return success in mock mode
        return True

    # Actual Beem SMS API Integration
    # Endpoint: https://api.beem.africa/v1/send
    api_url = "https://api.beem.africa/v1/send"

    # Setup credentials for Basic Auth
    credentials = f"{config.api_key}:{config.secret_key}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_credentials}"
    }

    payload = {
        "source_addr": config.sender_id,
        "schedule_time": "",
        "encoding": "0",
        "message": message,
        "recipients": [
            {
                "recipient_id": 1,
                "dest_addr": dest_phone
            }
        ]
    }

    try:
        response = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=10)
        if response.status_code == 200:
            resp_data = response.json()
            # Beem returns successful delivery reports inside JSON
            if resp_data.get('code') == 100 or 'successful' in resp_data:
                _log_sms(mshiriki, ibada, sms_type, dest_phone, message, 'SUCCESS')
                return True
            else:
                logger.error(f"Beem SMS API Error: {resp_data}")
                _log_sms(mshiriki, ibada, sms_type, dest_phone, message, 'FAILED', str(resp_data))
                return False
        else:
            logger.error(f"Beem SMS API HTTP Error {response.status_code}: {response.text}")
            _log_sms(mshiriki, ibada, sms_type, dest_phone, message, 'FAILED', f"HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to connect to Beem SMS API: {e}")
        _log_sms(mshiriki, ibada, sms_type, dest_phone, message, 'FAILED', str(e))
        return False


def get_active_config():
    """Rudisha SMSConfig inayotumika, ukiunda moja ya mockup ikiwa hakuna."""
    config = SMSConfig.objects.filter(is_active=True).first()
    if not config:
        config = SMSConfig.objects.create(
            api_key="MOCK_KEY",
            secret_key="MOCK_SECRET",
            sender_id="KANDA"
        )
    return config


def format_ibada_time(ibada):
    """Panga tarehe na muda wa ibada katika muundo wa SMS."""
    local_time = timezone.localtime(ibada.tarehe_muda)
    formatted_time = local_time.strftime("%I:%M %p")
    formatted_date = local_time.strftime("%d/%m/%Y")
    return f"{formatted_date} saa {formatted_time}"


def send_bulk_ibada_sms(ibada):
    """
    Sends invitation and reminder SMS to all active members for a given Ibada session.
    Returns (success_count, fail_count, use_mockup).
    """
    config = get_active_config()
    use_mockup = (config.api_key == "MOCK_KEY" or not config.api_key)

    active_members = Mshiriki.objects.filter(is_active=True)
    if not active_members.exists():
        return 0, 0, use_mockup

    success_count = 0
    fail_count = 0

    time_str = format_ibada_time(ibada)

    for member in active_members:
        # Personalize template for each member
        message = config.sms_template.format(
            jina=member.jina,
            mwenyeji=ibada.mwenyeji,
            muda=time_str,
            ramani_link=ibada.ramani_link or "maelekezo: " + (ibada.maelekezo or "ibada ya kanda")
        )

        is_sent = send_single_sms(member.simu, message, config, mshiriki=member, ibada=ibada, sms_type='INVITATION')
        if is_sent:
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count, use_mockup


def send_rsvp_reminder_sms(ibada, members):
    """
    Sends a short reminder SMS to members who have NOT submitted RSVP yet.
    Returns (success_count, fail_count, use_mockup).
    """
    config = get_active_config()
    use_mockup = (config.api_key == "MOCK_KEY" or not config.api_key)

    if not members:
        return 0, 0, use_mockup

    success_count = 0
    fail_count = 0
    time_str = format_ibada_time(ibada)

    for member in members:
        message = (
            f"Habari {member.jina}, bado hatujapokea uthibitisho wako wa ibada ya Kanda ya "
            f"Sinza & Kijitonyama kwa familia ya {ibada.mwenyeji} ({time_str}). "
            f"Tafadhali thibitisha kwa kufungua: http://127.0.0.1:8000/ - Karibu sana!"
        )
        is_sent = send_single_sms(member.simu, message, config, mshiriki=member, ibada=ibada, sms_type='REMINDER')
        if is_sent:
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count, use_mockup


def send_attendance_sms(ibada, present_members, absent_members):
    """
    Sends customized thank you / encouraging SMS to members depending on whether they attended the session.
    Returns (success_count, fail_count, use_mockup).
    """
    config = get_active_config()
    use_mockup = (config.api_key == "MOCK_KEY" or not config.api_key)

    success_count = 0
    fail_count = 0

    # 1. Send SMS to present members
    for member in present_members:
        message = config.sms_present_template.format(
            jina=member.jina,
            mwenyeji=ibada.mwenyeji
        )
        is_sent = send_single_sms(member.simu, message, config, mshiriki=member, ibada=ibada, sms_type='THANK_YOU')
        if is_sent:
            success_count += 1
        else:
            fail_count += 1

    # 2. Send SMS to absent members
    for member in absent_members:
        message = config.sms_absent_template.format(
            jina=member.jina,
            mwenyeji=ibada.mwenyeji
        )
        is_sent = send_single_sms(member.simu, message, config, mshiriki=member, ibada=ibada, sms_type='ENCOURAGEMENT')
        if is_sent:
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count, use_mockup
