import os
import requests
import json
import base64
import re
import logging
from datetime import timedelta
from django.utils import timezone
from .models import Mshiriki, SMSConfig, SMSLog

logger = logging.getLogger(__name__)

# Official Next SMS Endpoints
NEXT_SMS_V1_SINGLE_URL = "https://messaging-service.co.tz/api/sms/v1/text/single"
NEXT_SMS_V2_SINGLE_URL = "https://messaging-service.co.tz/api/sms/v2/text/single"
NEXT_SMS_BALANCE_URL = "https://messaging-service.co.tz/api/sms/v1/balance"
NEXT_SMS_V2_BALANCE_URL = "https://messaging-service.co.tz/api/v2/balance"


def _log_sms(mshiriki, ibada, sms_type, phone, message, status, error=None):
    """Hifadhi kumbukumbu ya SMS kwenye database (SMSLog)."""
    try:
        return SMSLog.objects.create(
            mshiriki=mshiriki if mshiriki and getattr(mshiriki, 'pk', None) else None,
            ibada=ibada if ibada and getattr(ibada, 'pk', None) else None,
            type=sms_type,
            status=status,
            phone=phone,
            message=message,
            error=error,
        )
    except Exception as e:
        logger.error(f"Imeshindwa kuhifadhi SMSLog: {e}")
        return None


def clean_phone_number(dest_phone):
    """
    Husafisha namba ya simu kuwa kwenye muundo wa Tanzania wa tarakimu 12 (255XXXXXXXXX).
    Inaondoa alama za +, nafasi, mabano na mikwaju.
    """
    if not dest_phone:
        return ""
    digits = re.sub(r'\D', '', str(dest_phone).strip())
    
    if digits.startswith("0") and len(digits) == 10:
        return "255" + digits[1:]
    elif digits.startswith("255") and len(digits) == 12:
        return digits
    elif len(digits) == 9 and digits.startswith(("6", "7")):
        return "255" + digits
    elif digits.startswith("00255") and len(digits) == 14:
        return digits[2:]
    return digits


def get_auth_headers_list(api_key, secret_key):
    """
    Hutengeneza orodha ya vichwa vya habari vya uthibitisho (Authorization headers)
    kwa ajili ya Next SMS API kulingana na vigezo vilivyowekwa.
    """
    api_key = (api_key or "").strip()
    secret_key = (secret_key or "").strip()
    headers_list = []

    # 1. Kama mtumiaji ameingiza moja kwa moja kianzio cha "Bearer " au "Basic "
    if api_key.startswith("Basic ") or api_key.startswith("Bearer "):
        headers_list.append(api_key)
    if secret_key.startswith("Basic ") or secret_key.startswith("Bearer "):
        headers_list.append(secret_key)

    # 2. Next SMS Standard: Username (api_key) na Password (secret_key)
    if api_key and secret_key and api_key != secret_key:
        credentials = f"{api_key}:{secret_key}"
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        headers_list.append(f"Basic {encoded}")

    # 3. Kama API key moja tu imewekwa au zote zinafanana
    single_token = api_key or secret_key
    if single_token and single_token not in ["MOCK_KEY", "MOCK_SECRET"]:
        # Jaribu kuona kama ni base64 iliyokwisha andaliwa (ina jina:nenosiri)
        try:
            decoded = base64.b64decode(single_token.encode('utf-8')).decode('utf-8')
            if ":" in decoded:
                headers_list.append(f"Basic {single_token}")
        except Exception:
            pass

        # Bearer token (Next SMS API token)
        headers_list.append(f"Bearer {single_token}")
        # Basic token fallback
        headers_list.append(f"Basic {single_token}")
        # Base64 encoded token
        b64_raw = base64.b64encode(single_token.encode('utf-8')).decode('utf-8')
        headers_list.append(f"Basic {b64_raw}")

    # Hakikisha hakuna marudio huku tukihifadhi mpangilio
    unique_headers = []
    for h in headers_list:
        if h and h not in unique_headers:
            unique_headers.append(h)

    return unique_headers


def is_mock_mode(config):
    """Kuangalia kama mfumo uko kwenye Mock Mode."""
    if not config:
        return False
    key = (config.api_key or "").strip()
    secret = (config.secret_key or "").strip()
    if key in ["MOCK_KEY", ""] and (secret in ["MOCK_SECRET", ""] or not DEFAULT_NEXT_SMS_API_KEY):
        return True
    return False


def send_single_sms(dest_phone, message, config=None, mshiriki=None, ibada=None, sms_type='INVITATION'):
    """
    Hutuma SMS moja kwa kutumia Next SMS API (au Mock Mode kama credentials ni za majaribio).
    Inasaidia V1 na V2 za Next SMS na inahifadhi taarifa zote kwenye SMSLog.
    """
    if config is None:
        config = get_active_config()

    phone_clean = clean_phone_number(dest_phone)
    if not phone_clean or len(phone_clean) < 9:
        err = f"Namba ya simu si sahihi: {dest_phone}"
        logger.warning(err)
        _log_sms(mshiriki, ibada, sms_type, dest_phone, message, 'FAILED', err)
        return False

    # Angalia kama mfumo wa SMS uko Active
    if not getattr(config, 'is_active', True):
        err = "Mfumo wa SMS umezimwa kwenye mipangilio (is_active=False)."
        logger.info(err)
        _log_sms(mshiriki, ibada, sms_type, phone_clean, message, 'FAILED', err)
        return False

    # Mock Mode
    if is_mock_mode(config):
        print(f"--- [MOCK SMS TO {phone_clean}] ---")
        print(f"Sender ID: {getattr(config, 'sender_id', 'IBADA') or 'IBADA SIFA'}")
        print(f"Message: {message}")
        print("---------------------------------")
        _log_sms(mshiriki, ibada, sms_type, phone_clean, message, 'MOCKUP')
        return True

    sender_id = (getattr(config, 'sender_id', '') or 'IBADA SIFA').strip()
    api_k = (getattr(config, 'api_key', None) or DEFAULT_NEXT_SMS_API_KEY or '').strip()
    secret_k = (getattr(config, 'secret_key', None) or DEFAULT_NEXT_SMS_SECRET or '').strip()
    auth_headers = get_auth_headers_list(api_k, secret_k)
    if not auth_headers:
        err = "Taarifa za uthibitisho (Credentials) za Next SMS hazipo."
        _log_sms(mshiriki, ibada, sms_type, phone_clean, message, 'FAILED', err)
        return False

    payload = {
        "from": sender_id,
        "to": phone_clean,
        "text": message
    }

    endpoints = [NEXT_SMS_V1_SINGLE_URL, NEXT_SMS_V2_SINGLE_URL]
    last_error = ""

    for api_url in endpoints:
        for auth_h in auth_headers:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": auth_h
            }
            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=12)

                if response.status_code in [200, 201]:
                    try:
                        resp_data = response.json()
                    except Exception:
                        resp_data = {}

                    messages_list = resp_data.get('messages', [])
                    if messages_list:
                        first_msg = messages_list[0]
                        status_obj = first_msg.get('status', {})
                        group_id = status_obj.get('groupId')
                        status_name = str(status_obj.get('name', '')).upper()
                        status_desc = status_obj.get('description', '')
                        group_name = str(status_obj.get('groupName', '')).upper()

                        # Next SMS Success Status Groups:
                        # 0 = ACCEPTED, 1 = PENDING, 3 = DELIVERED, 18 = PENDING (SENT/ENROUTE), 20 = DELIVERY (DELIVERED/SENT)
                        is_success = (
                            group_id in [0, 1, 3, 18, 20] or
                            group_name in ['PENDING', 'ACCEPTED', 'DELIVERED', 'SUCCESS', 'OK'] or
                            any(k in status_name for k in ['ACCEPT', 'PENDING', 'ENROUTE', 'SENT', 'DELIVER', 'SUCCESS', 'OK'])
                        )

                        if is_success:
                            _log_sms(mshiriki, ibada, sms_type, phone_clean, message, 'SUCCESS')
                            return True
                        else:
                            last_error = f"{status_name}: {status_desc}" if status_desc else str(status_obj)
                            logger.error(f"Next SMS status rejected: {last_error}")
                            _log_sms(mshiriki, ibada, sms_type, phone_clean, message, 'FAILED', last_error)
                            return False
                    elif resp_data.get('success') is True or resp_data.get('status') in [200, 201]:
                        _log_sms(mshiriki, ibada, sms_type, phone_clean, message, 'SUCCESS')
                        return True
                    else:
                        last_error = str(resp_data)
                        _log_sms(mshiriki, ibada, sms_type, phone_clean, message, 'FAILED', last_error)
                        return False

                elif response.status_code in [401, 403]:
                    last_error = f"HTTP {response.status_code}: Uthibitisho wa Next SMS umeshindikana ({response.text})."
                    # Jaribu header inayofuata
                    continue
                elif response.status_code in [400, 422]:
                    last_error = f"HTTP {response.status_code}: Data si sahihi ({response.text})."
                    logger.error(f"Next SMS 400/422: {response.text}")
                    break
                else:
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"Next SMS HTTP Error {response.status_code}: {response.text}")

            except requests.exceptions.RequestException as req_err:
                last_error = f"Hitilafu ya Mtandao: {req_err}"
                logger.error(f"Network error calling Next SMS: {req_err}")

    # Kama zote zimefeli
    _log_sms(mshiriki, ibada, sms_type, phone_clean, message, 'FAILED', last_error)
    return False


def send_test_sms(dest_phone, test_message, config=None):
    """
    Hutuma SMS ya majaribio kwa kutumia Next SMS API ili kuthibitisha muunganisho.
    Inaweka moja kwa moja header ya: MANZESE SDA, SINZA NA KIJITONYAMA
    """
    HEADER_PREFIX = "MANZESE SDA, SINZA NA KIJITONYAMA\n\n"
    if test_message and not test_message.strip().startswith("MANZESE SDA"):
        test_message = f"{HEADER_PREFIX}{test_message.strip()}"
    """
    Hutuma SMS ya majaribio na kurudisha ripoti ya kina ya kiufundi (kwa ajili ya ukurasa wa SMS Settings).
    """
    if config is None:
        config = get_active_config()

    phone_clean = clean_phone_number(dest_phone)
    if not phone_clean or len(phone_clean) < 9:
        return {
            "success": False,
            "status_code": 400,
            "message": f"Namba ya simu uliyoweka ({dest_phone}) si sahihi. Weka namba ya Tanzania mfano 0787661560 au 255787661560.",
            "phone": dest_phone,
            "mode": "ERROR",
            "raw_response": ""
        }

    if is_mock_mode(config):
        _log_sms(None, None, 'TEST', phone_clean, test_message, 'MOCKUP')
        return {
            "success": True,
            "status_code": 200,
            "message": "Ujumbe wa jaribio umerekodiwa kikamilifu kwenye SMS Logs (Mock Mode). Hakuna salio lililokatwa kwa sababu API Key haijawekwa.",
            "phone": phone_clean,
            "mode": "MOCK",
            "raw_response": "MOCK_MODE_ACTIVE"
        }

    sender_id = (getattr(config, 'sender_id', '') or 'IBADA SIFA').strip()
    api_k = (getattr(config, 'api_key', None) or DEFAULT_NEXT_SMS_API_KEY or '').strip()
    secret_k = (getattr(config, 'secret_key', None) or DEFAULT_NEXT_SMS_SECRET or '').strip()
    auth_headers = get_auth_headers_list(api_k, secret_k)
    if not auth_headers:
        return {
            "success": False,
            "status_code": 401,
            "message": "Tafadhali weka Username na Password au API Key ya Next SMS kwenye fomu ya mazingira.",
            "phone": phone_clean,
            "mode": "ERROR",
            "raw_response": ""
        }

    payload = {
        "from": sender_id,
        "to": phone_clean,
        "text": test_message
    }

    endpoints = [NEXT_SMS_V1_SINGLE_URL, NEXT_SMS_V2_SINGLE_URL]
    last_response_text = ""
    last_status_code = 0

    for api_url in endpoints:
        for auth_h in auth_headers:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": auth_h
            }
            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=15)
                last_status_code = response.status_code
                last_response_text = response.text

                if response.status_code in [200, 201]:
                    try:
                        resp_data = response.json()
                    except Exception:
                        resp_data = {}

                    messages_list = resp_data.get('messages', [])
                    if messages_list:
                        first_msg = messages_list[0]
                        status_obj = first_msg.get('status', {})
                        group_id = status_obj.get('groupId')
                        status_name = str(status_obj.get('name', '')).upper()
                        status_desc = status_obj.get('description', '')
                        group_name = str(status_obj.get('groupName', '')).upper()

                        is_success = (
                            group_id in [0, 1, 3, 18, 20] or
                            group_name in ['PENDING', 'ACCEPTED', 'DELIVERED', 'SUCCESS', 'OK'] or
                            any(k in status_name for k in ['ACCEPT', 'PENDING', 'ENROUTE', 'SENT', 'DELIVER', 'SUCCESS', 'OK'])
                        )

                        if is_success:
                            _log_sms(None, None, 'TEST', phone_clean, test_message, 'SUCCESS')
                            return {
                                "success": True,
                                "status_code": response.status_code,
                                "message": f"Hongera! SMS ya jaribio imetumwa kikamilifu kwenda {phone_clean} kupitia Next SMS Gateway (Hali: {status_name or 'SENT'}).",
                                "phone": phone_clean,
                                "mode": "LIVE",
                                "raw_response": response.text,
                                "endpoint": api_url
                            }
                        else:
                            err_desc = f"{status_name}: {status_desc}" if status_desc else str(status_obj)
                            _log_sms(None, None, 'TEST', phone_clean, test_message, 'FAILED', err_desc)
                            return {
                                "success": False,
                                "status_code": response.status_code,
                                "message": f"Next SMS imekataa kutuma ujumbe ({err_desc}). Angalia kama Sender ID '{sender_id}' imeidhinishwa na akaunti yako ina salio.",
                                "phone": phone_clean,
                                "mode": "LIVE",
                                "raw_response": response.text,
                                "endpoint": api_url
                            }
                    elif resp_data.get('success') is True or resp_data.get('status') in [200, 201]:
                        _log_sms(None, None, 'TEST', phone_clean, test_message, 'SUCCESS')
                        return {
                            "success": True,
                            "status_code": response.status_code,
                            "message": f"Hongera! SMS ya jaribio imetumwa kikamilifu kwenda {phone_clean}.",
                            "phone": phone_clean,
                            "mode": "LIVE",
                            "raw_response": response.text,
                            "endpoint": api_url
                        }

                elif response.status_code in [401, 403]:
                    continue
                elif response.status_code in [400, 422]:
                    break
            except Exception as e:
                last_response_text = str(e)
                last_status_code = 500

    # Kama zote zimefeli
    _log_sms(None, None, 'TEST', phone_clean, test_message, 'FAILED', f"HTTP {last_status_code}: {last_response_text}")
    
    diagnostic_hint = ""
    if last_status_code in [401, 403]:
        diagnostic_hint = "Sababu: Username, Password, au API Token ya Next SMS si sahihi au imeisha muda wake. Hakikisha umeiandika sawa."
    elif last_status_code in [400, 422]:
        diagnostic_hint = f"Sababu: Muundo wa namba ya simu ({phone_clean}) au Sender ID ('{sender_id}') haijaruhusiwa na Next SMS."
    elif last_status_code == 0 or "connection" in last_response_text.lower():
        diagnostic_hint = "Sababu: Imeshindwa kuungana na seva za Next SMS (Mtandao/Internet inasumbua)."

    return {
        "success": False,
        "status_code": last_status_code,
        "message": f"Kosa {last_status_code}: Imeshindwa kutuma SMS. {diagnostic_hint}",
        "phone": phone_clean,
        "mode": "LIVE",
        "raw_response": last_response_text
    }


def check_nextsms_balance(config=None):
    """
    Hukagua salio la SMS lililobaki kwenye akaunti ya Next SMS (messaging-service.co.tz).
    """
    if config is None:
        config = get_active_config()

    api_k = (getattr(config, 'api_key', None) or DEFAULT_NEXT_SMS_API_KEY or '').strip()
    secret_k = (getattr(config, 'secret_key', None) or DEFAULT_NEXT_SMS_SECRET or '').strip()

    if is_mock_mode(config) and not api_k:
        return {
            "success": True,
            "is_mock": True,
            "balance": "Majaribio (Mock Mode)",
            "message": "Mfumo uko kwenye Hali ya Majaribio."
        }

    auth_headers = get_auth_headers_list(api_k, secret_k)
    if not auth_headers:
        return {
            "success": False,
            "is_mock": False,
            "balance": "Haipatikani",
            "message": "Weka Username na Password za Next SMS kwanza."
        }

    balance_urls = [NEXT_SMS_V2_BALANCE_URL, NEXT_SMS_BALANCE_URL]

    for auth_h in auth_headers:
        headers = {
            "Accept": "application/json",
            "Authorization": auth_h
        }
        for b_url in balance_urls:
            try:
                response = requests.get(b_url, headers=headers, timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    sms_balance = (
                        data.get('display') or
                        data.get('sms_balance') or
                        data.get('smsBalance') or
                        data.get('balance') or
                        data.get('credits') or
                        data.get('currentBalance')
                    )
                    currency = data.get('currency', 'TZS' if 'display' in data or 'sms_balance' in data else 'SMS')
                    bal_str = f"{sms_balance}" if (str(sms_balance).endswith('TZS') or ' ' in str(sms_balance)) else f"{sms_balance} {currency}"
                    return {
                        "success": True,
                        "is_mock": False,
                        "balance": sms_balance if sms_balance is not None else "Inapatikana",
                        "currency": currency,
                        "data": data,
                        "message": f"Salio lako la Next SMS: {bal_str}"
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch Next SMS balance from {b_url}: {e}")

    return {
        "success": False,
        "is_mock": False,
        "balance": "Haipatikani",
        "message": "Imeshindwa kupata salio kutoka Next SMS. Hakikisha taarifa zako za kuingia ni sahihi."
    }


DEFAULT_NEXT_SMS_API_KEY = os.getenv('NEXTSMS_API_KEY', '').strip()
DEFAULT_NEXT_SMS_SECRET = os.getenv('NEXTSMS_SECRET', '').strip()
DEFAULT_SENDER_ID = os.getenv('NEXTSMS_SENDER_ID', 'IBADA SIFA').strip() or 'IBADA SIFA'
DEFAULT_PASSCODE = os.getenv('LEADER_PASSCODE', '2010').strip() or '2010'

def get_active_config():
    """Rudisha SMSConfig inayotumika ikiwa na credentials rasmi za NextSMS."""
    config = SMSConfig.objects.filter(is_active=True).first()
    if not config:
        config = SMSConfig.objects.create(
            api_key=DEFAULT_NEXT_SMS_API_KEY,
            secret_key=DEFAULT_NEXT_SMS_SECRET,
            sender_id=DEFAULT_SENDER_ID,
            leader_passcode=DEFAULT_PASSCODE,
            is_active=True
        )
    elif not config.api_key or not config.secret_key:
        config.api_key = DEFAULT_NEXT_SMS_API_KEY
        config.secret_key = DEFAULT_NEXT_SMS_SECRET
        config.sender_id = DEFAULT_SENDER_ID
        config.leader_passcode = DEFAULT_PASSCODE
        config.is_active = True
        config.save()

    return config


def format_ibada_time_short(ibada):
    """Panga tarehe na muda wa ibada kwa ufupi na uwazi ili kulinda herufi za SMS (mfano: kesho 07/09 saa 12:30 Asb)."""
    local_time = timezone.localtime(ibada.tarehe_muda)
    date_str = local_time.strftime("%d/%m")
    
    hour = local_time.hour
    minute = local_time.strftime("%M")
    
    # Swahili hour conversion
    sw_hour = (hour + 6) % 12
    if sw_hour == 0:
        sw_hour = 12
        
    if 4 <= hour < 12:
        period = "Asb"
    elif 12 <= hour < 16:
        period = "Mchana"
    elif 16 <= hour < 19:
        period = "Jioni"
    else:
        period = "Usiku"

    today = timezone.localdate()
    ibada_date = local_time.date()
    if ibada_date == today:
        prefix = "leo"
    elif ibada_date == today + timedelta(days=1):
        prefix = "kesho"
    else:
        prefix = "tarehe"
        
    return f"{prefix} {date_str} saa {sw_hour}:{minute} {period}"


def format_ibada_time(ibada):
    """Panga tarehe na muda wa ibada katika muundo kamili wa Kiswahili."""
    return format_ibada_time_short(ibada)


def send_bulk_ibada_sms(ibada):
    """
    Hutuma SMS za mwaliko kwa washiriki wote zikiwa fupi na salama (SMS 1 = Tsh 16).
    Inatumia jina la kwanza tu la mshiriki na kugawa herufi kwa ufanisi.
    """
    config = get_active_config()
    use_mockup = is_mock_mode(config)

    active_members = Mshiriki.objects.filter(is_active=True)
    if not active_members.exists():
        return 0, 0, use_mockup

    success_count = 0
    fail_count = 0
    time_str = format_ibada_time_short(ibada)
    mwenyeji = (ibada.mwenyeji or "").strip()
    ramani_link = (ibada.ramani_link or "").strip()
    maelekezo = (ibada.maelekezo or "").strip()

    for member in active_members:
        # Chukua jina la kwanza pekee ili kuokoa herufi
        raw_name = (member.jina or "").strip()
        first_name = raw_name.split()[0].capitalize() if raw_name else "Mpendwa"

        if ramani_link:
            message = (
                f"MANZESE SDA\n"
                f"Habari {first_name}, karibu Ibada ya Anza na Bwana {time_str} "
                f"kwa {mwenyeji}. Ramani: {ramani_link}"
            )
        elif maelekezo:
            message = (
                f"MANZESE SDA\n"
                f"Habari {first_name}, karibu Ibada ya Anza na Bwana {time_str} "
                f"kwa {mwenyeji} ({maelekezo})."
            )
        else:
            message = (
                f"MANZESE SDA (SINZA & KIJITONYAMA)\n"
                f"Habari {first_name}, karibu Ibada ya Anza na Bwana {time_str} "
                f"kwa {mwenyeji}."
            )

        # Ulinzi mkali (Safety Guard): Hakikisha ujumbe hauvuki herufi 160 kamwe (Strictly 1 SMS)
        if len(message) > 160 and maelekezo:
            excess = len(message) - 160
            trimmed_maelekezo = maelekezo[:-excess].strip().rstrip('.,;')
            message = (
                f"MANZESE SDA\n"
                f"Habari {first_name}, karibu Ibada ya Anza na Bwana {time_str} "
                f"kwa {mwenyeji} ({trimmed_maelekezo})."
            )

        is_sent = send_single_sms(member.simu, message, config, mshiriki=member, ibada=ibada, sms_type='INVITATION')
        if is_sent:
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count, use_mockup


def send_rsvp_reminder_sms(ibada, members):
    """
    Sends a short reminder SMS to members who have NOT submitted RSVP yet (Strictly 1 SMS).
    """
    config = get_active_config()
    use_mockup = is_mock_mode(config)

    if not members:
        return 0, 0, use_mockup

    success_count = 0
    fail_count = 0
    time_str = format_ibada_time_short(ibada)
    mwenyeji = (ibada.mwenyeji or "").strip()

    for member in members:
        raw_name = (member.jina or "").strip()
        first_name = raw_name.split()[0].capitalize() if raw_name else "Mpendwa"
        message = (
            f"MANZESE SDA\n"
            f"Habari {first_name}, tafadhali thibitisha mahudhurio ya Ibada "
            f"{time_str} kwa {mwenyeji}. Karibu sana tubarikiwe!"
        )
        is_sent = send_single_sms(member.simu, message, config, mshiriki=member, ibada=ibada, sms_type='REMINDER')
        if is_sent:
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count, use_mockup


def send_attendance_sms(ibada, present_members, absent_members, send_to_present=True, send_to_absent=True, custom_present_msg=None, custom_absent_msg=None):
    """
    Sends customized thank you / encouraging SMS to members depending on whether they attended (Strictly 1 SMS each).
    """
    config = get_active_config()
    use_mockup = is_mock_mode(config)

    success_count = 0
    fail_count = 0
    mwenyeji = (ibada.mwenyeji or "").strip()

    # 1. Send SMS to present members (Thank You SMS)
    if send_to_present:
        for member in present_members:
            raw_name = (member.jina or "").strip()
            first_name = raw_name.split()[0].capitalize() if raw_name else "Mpendwa"
            if custom_present_msg and custom_present_msg.strip():
                message = custom_present_msg.strip().replace("{jina}", first_name).replace("{mwenyeji}", mwenyeji)
            else:
                message = (
                    f"MANZESE SDA\n"
                    f"Habari {first_name}, asante kwa kushiriki Ibada ya Kanda leo "
                    f"kwa {mwenyeji}. Uwepo wako ulikuwa baraka. Ubarikiwe sana!"
                )
            is_sent = send_single_sms(member.simu, message, config, mshiriki=member, ibada=ibada, sms_type='THANK_YOU')
            if is_sent:
                success_count += 1
            else:
                fail_count += 1

    # 2. Send SMS to absent members (Encouragement SMS)
    if send_to_absent:
        for member in absent_members:
            raw_name = (member.jina or "").strip()
            first_name = raw_name.split()[0].capitalize() if raw_name else "Mpendwa"
            if custom_absent_msg and custom_absent_msg.strip():
                message = custom_absent_msg.strip().replace("{jina}", first_name).replace("{mwenyeji}", mwenyeji)
            else:
                message = (
                    f"MANZESE SDA\n"
                    f"Habari {first_name}, tulikumiss sana kwenye Ibada ya Kanda leo "
                    f"kwa {mwenyeji}. Ubarikiwe na uwe na juma njema. Karibu ibada ijayo!"
                )
            is_sent = send_single_sms(member.simu, message, config, mshiriki=member, ibada=ibada, sms_type='ENCOURAGEMENT')
            if is_sent:
                success_count += 1
            else:
                fail_count += 1

    return success_count, fail_count, use_mockup


def send_custom_broadcast_sms(custom_message, recipient_type='ALL', specific_member_id=None):
    """
    Hutuma ujumbe maalum kwa washiriki ukibadilisha {jina} na jina la kwanza.
    """
    config = get_active_config()
    use_mockup = is_mock_mode(config)

    if specific_member_id:
        target_members = Mshiriki.objects.filter(id=specific_member_id, is_active=True)
    else:
        target_members = Mshiriki.objects.filter(is_active=True)

    if not target_members.exists():
        return 0, 0, use_mockup

    success_count = 0
    fail_count = 0

    for member in target_members:
        raw_name = (member.jina or "").strip()
        first_name = raw_name.split()[0].capitalize() if raw_name else "Mpendwa"
        msg_body = custom_message.replace("{jina}", first_name).strip()

        is_sent = send_single_sms(member.simu, msg_body, config, mshiriki=member, ibada=None, sms_type='CUSTOM')
        if is_sent:
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count, use_mockup
