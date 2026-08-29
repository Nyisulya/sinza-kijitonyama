from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Mshiriki, Ibada, Uthibitisho, SMSConfig, Mahudhurio, SMSLog
from .sms_helper import (
    send_bulk_ibada_sms, 
    send_attendance_sms, 
    send_rsvp_reminder_sms,
    send_test_sms,
    check_nextsms_balance,
    is_mock_mode,
    get_active_config,
    send_custom_broadcast_sms
)
from functools import wraps


def leader_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('is_leader'):
            messages.warning(request, "Tafadhali ingiza neno la siri ili kuingia kwenye ukurasa wa viongozi.")
            return redirect('leader_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def home(request):
    # Get the next upcoming ibada (closest in the future and not completed)
    upcoming_ibada = Ibada.objects.filter(is_completed=False, tarehe_muda__gte=timezone.now()).order_by('tarehe_muda').first()
    if not upcoming_ibada:
        # Fallback to any uncompleted ibada
        upcoming_ibada = Ibada.objects.filter(is_completed=False).order_by('tarehe_muda').first()

    washiriki = Mshiriki.objects.filter(is_active=True)
    viongozi = Mshiriki.objects.filter(is_active=True, jukumu='KIONGOZI')

    context = {
        'upcoming_ibada': upcoming_ibada,
        'washiriki': washiriki,
        'viongozi': viongozi,
    }
    return render(request, 'home.html', context)

def register_member(request):
    if request.method == 'POST':
        jina = request.POST.get('jina')
        simu = request.POST.get('simu')
        familia = request.POST.get('familia', '')
        jukumu = request.POST.get('jukumu', 'MSHIRIKI')
        cheo = request.POST.get('cheo', 'Kiongozi wa Kanda' if jukumu == 'KIONGOZI' else '')
        picha = request.FILES.get('picha')
        next_url = request.POST.get('next', 'members_list')

        try:
            mshiriki = Mshiriki(jina=jina, simu=simu, familia=familia, jukumu=jukumu, cheo=cheo)
            if picha:
                mshiriki.picha = picha
            mshiriki.full_clean()
            mshiriki.save()
            messages.success(request, f"Hongera! Mshiriki '{jina}' amesajiliwa kikamilifu.")
        except Exception as e:
            messages.error(request, f"Imeshindwa kusajili mshiriki: {e}")

        if next_url == 'home':
            return redirect('home')
        return redirect('members_list')

    return redirect('members_list')

def submit_rsvp(request, ibada_id):
    if request.method == 'POST':
        ibada = get_object_or_404(Ibada, id=ibada_id)
        mshiriki_id = request.POST.get('mshiriki_id')
        status = request.POST.get('status')
        maoni = request.POST.get('maoni', '')

        mshiriki = get_object_or_404(Mshiriki, id=mshiriki_id)

        try:
            rsvp, created = Uthibitisho.objects.update_or_create(
                mshiriki=mshiriki,
                ibada=ibada,
                defaults={'status': status, 'maoni': maoni}
            )
            messages.success(request, f"Uthibitisho wako umepokelewa! Asante {mshiriki.jina}.")
        except Exception as e:
            messages.error(request, f"Imeshindwa kutuma RSVP: {e}")

    return redirect('home')

def schedule(request):
    ibada_list = Ibada.objects.all().order_by('-tarehe_muda')
    return render(request, 'schedule.html', {'ibada_list': ibada_list})

@leader_required
def leader_dashboard(request):
    # Next upcoming ibada (uncompleted)
    upcoming_ibada = Ibada.objects.filter(is_completed=False).order_by('tarehe_muda').first()

    # Most recent completed ibada
    latest_completed_ibada = Ibada.objects.filter(is_completed=True).order_by('-tarehe_muda').first()

    washiriki_count = Mshiriki.objects.filter(is_active=True).count()
    ibada_completed_count = Ibada.objects.filter(is_completed=True).count()

    # Get attendance details for the latest completed meeting
    completed_attendance = []
    completed_present_count = 0
    completed_absent_count = 0
    if latest_completed_ibada:
        completed_attendance = Mahudhurio.objects.filter(ibada=latest_completed_ibada).order_by('mshiriki__jina')
        completed_present_count = completed_attendance.filter(is_present=True).count()
        completed_absent_count = completed_attendance.filter(is_present=False).count()

    context = {
        'upcoming_ibada': upcoming_ibada,
        'latest_completed_ibada': latest_completed_ibada,
        'washiriki_count': washiriki_count,
        'ibada_completed_count': ibada_completed_count,
        'completed_attendance': completed_attendance,
        'completed_present_count': completed_present_count,
        'completed_absent_count': completed_absent_count,
    }
    return render(request, 'leader_dashboard.html', context)


@leader_required
def trigger_sms(request, ibada_id):
    if request.method == 'POST':
        ibada = get_object_or_404(Ibada, id=ibada_id)
        
        success_count, fail_count, use_mockup = send_bulk_ibada_sms(ibada)
        
        if fail_count == 0 and success_count > 0:
            if use_mockup:
                messages.success(request, f"Njia ya Majaribio (Mock Mode): SMS {success_count} za mwaliko zimetengenezwa na kuhifadhiwa kwenye kumbukumbu (SMS Logs).")
            else:
                messages.success(request, f"✅ Hongera! SMS {success_count} za mwaliko zimetumwa kikamilifu kupitia Next SMS Gateway!")
        elif success_count > 0 and fail_count > 0:
            messages.warning(request, f"SMS {success_count} zilitumwa lakini {fail_count} zimeshindwa (Salio limeisha katikati). Angalia SMS Logs.")
        elif fail_count > 0:
            # Pata hitilafu ya mwisho iliyorekodiwa kwenye SMSLog
            last_failed_log = SMSLog.objects.filter(ibada=ibada, status='FAILED').order_by('-created_at').first()
            err_reason = f" ({last_failed_log.error})" if last_failed_log and last_failed_log.error else ""
            messages.error(
                request, 
                f"❌ SMS {fail_count} zimeshindwa kutumwa{err_reason}. "
                f"Sababu: Akaunti yako ya Next SMS haina salio la kutosha (Inahitaji kuongezwa salio) au angalia SMS Logs."
            )
        else:
            messages.info(request, "Hakuna washiriki walio active kwenye mfumo wa kuwatumia SMS.")

    return redirect('leader_dashboard')

@leader_required
def create_ibada(request):
    from django.utils.dateparse import parse_datetime
    
    if request.method == 'POST':
        mwenyeji = request.POST.get('mwenyeji')
        tarehe_muda_str = request.POST.get('tarehe_muda')
        ramani_link = request.POST.get('ramani_link', '')
        maelekezo = request.POST.get('maelekezo', '')
        masomo = request.POST.get('masomo', '')

        try:
            naive_datetime = parse_datetime(tarehe_muda_str)
            if naive_datetime:
                aware_datetime = timezone.make_aware(naive_datetime, timezone.get_current_timezone())
                # Mark past uncompleted ibada sessions as completed
                Ibada.objects.filter(is_completed=False).update(is_completed=True)
                
                ibada = Ibada.objects.create(
                    mwenyeji=mwenyeji,
                    tarehe_muda=aware_datetime,
                    ramani_link=ramani_link,
                    maelekezo=maelekezo,
                    masomo=masomo,
                    is_completed=False
                )
                messages.success(request, f"Hongera! Ibada mpya kwa Familia ya {mwenyeji} imesajiliwa kikamilifu.")
            else:
                messages.error(request, "Tarehe na muda uliowekwa si sahihi.")
        except Exception as e:
            messages.error(request, f"Imeshindwa kusajili ibada: {e}")

    return redirect('leader_dashboard')

@leader_required
def take_attendance(request, ibada_id):
    ibada = get_object_or_404(Ibada, id=ibada_id)
    washiriki = Mshiriki.objects.filter(is_active=True)
    
    # Pre-select members who RSVP'd Yes or Needs Transport
    rsvp_yes_member_ids = list(Uthibitisho.objects.filter(
        ibada=ibada, 
        status__in=['NITAKUJA', 'NAHITAJI_USAFIRI']
    ).values_list('mshiriki_id', flat=True))
    
    context = {
        'ibada': ibada,
        'washiriki': washiriki,
        'rsvp_yes_member_ids': rsvp_yes_member_ids,
    }
    return render(request, 'attendance_rollcall.html', context)

@leader_required
def save_attendance(request, ibada_id):
    if request.method == 'POST':
        ibada = get_object_or_404(Ibada, id=ibada_id)
        present_member_ids_str = request.POST.getlist('present_members')
        
        active_members = Mshiriki.objects.filter(is_active=True)
        present_members = []
        absent_members = []
        
        try:
            for member in active_members:
                is_present = str(member.id) in present_member_ids_str
                Mahudhurio.objects.update_or_create(
                    ibada=ibada,
                    mshiriki=member,
                    defaults={'is_present': is_present}
                )
                if is_present:
                    present_members.append(member)
                else:
                    absent_members.append(member)
            
            # Complete the meeting session
            ibada.is_completed = True
            ibada.save()
            
            # Check SMS options
            send_to_present = request.POST.get('send_to_present') == 'on'
            send_to_absent = request.POST.get('send_to_absent') == 'on'
            custom_present_msg = request.POST.get('custom_present_msg', '').strip()
            custom_absent_msg = request.POST.get('custom_absent_msg', '').strip()

            # If neither checkbox was present in form (fallback), send to both
            if 'submitted_via_form' in request.POST and not send_to_present and not send_to_absent:
                success_count, fail_count, use_mockup = 0, 0, False
                messages.info(request, "Mahudhurio yamehifadhiwa bila kutuma SMS (umechagua kutotuma).")
            else:
                if 'submitted_via_form' not in request.POST:
                    send_to_present = True
                    send_to_absent = True
                
                success_count, fail_count, use_mockup = send_attendance_sms(
                    ibada, present_members, absent_members,
                    send_to_present=send_to_present,
                    send_to_absent=send_to_absent,
                    custom_present_msg=custom_present_msg,
                    custom_absent_msg=custom_absent_msg
                )
                
                status_type = "Mockup Mode (Logs)" if use_mockup else "Next SMS Gateway"
                messages.success(
                    request, 
                    f"✅ Mahudhurio yamehifadhiwa kikamilifu! "
                    f"SMS zimetumwa kiotomatiki kupitia {status_type}: "
                    f"Zilizofika: {success_count}, Zilizofeli: {fail_count}."
                )
        except Exception as e:
            messages.error(request, f"Imeshindwa kuhifadhi mahudhurio: {e}")
            
    return redirect('leader_dashboard')

def leader_login(request):
    """Huruhusu viongozi kuingia kwenye paneli kwa kutumia nenosiri la 2010."""
    if request.method == 'POST':
        passcode = request.POST.get('passcode', '').strip()
        
        # Retrieve config passcode (default 2010)
        config = SMSConfig.objects.filter(is_active=True).first()
        actual_passcode = config.leader_passcode.strip() if (config and config.leader_passcode) else "2010"
        
        if passcode == actual_passcode or passcode == "2010":
            request.session['is_leader'] = True
            messages.success(request, "Hongera! Umeingia kikamilifu kwenye Dashibodi ya Viongozi.")
            next_url = request.GET.get('next') or 'leader_dashboard'
            return redirect(next_url)
        else:
            messages.error(request, "Neno la siri si sahihi! Tafadhali jaribu tena.")
            
    return render(request, 'leader_login.html')


def leader_logout(request):
    """Hutoa kiongozi kwenye paneli ili nenosiri la 2010 lihitajike tena wakati ujao."""
    if 'is_leader' in request.session:
        del request.session['is_leader']
    messages.info(request, "Umetoka kwenye sehemu ya viongozi kwa usalama.")
    return redirect('home')

@leader_required
def attendance_history(request):
    completed_meetings = Ibada.objects.filter(is_completed=True).order_by('-tarehe_muda').prefetch_related('mahudhurio_set__mshiriki')
    
    meetings_data = []
    for meeting in completed_meetings:
        records = meeting.mahudhurio_set.all().order_by('mshiriki__jina')
        present_count = records.filter(is_present=True).count()
        absent_count = records.filter(is_present=False).count()
        meetings_data.append({
            'meeting': meeting,
            'records': records,
            'present_count': present_count,
            'absent_count': absent_count
        })

    return render(request, 'attendance_history.html', {'meetings_data': meetings_data})


@leader_required
def sms_settings(request):
    """Ukurasa wa mazingira ya SMS (API keys, templates, neno la siri, jaribio la SMS, na salio)."""
    config = get_active_config()
    test_result = None
    balance_info = None

    if request.method == 'POST':
        action = request.POST.get('action', 'save')

        if action == 'send_custom_broadcast':
            custom_msg = request.POST.get('custom_message', '').strip()
            recipient_type = request.POST.get('recipient_type', 'ALL')
            specific_member_id = request.POST.get('specific_member_id') or None

            if not custom_msg:
                messages.error(request, "Tafadhali andika ujumbe unaotaka kuutuma.")
            else:
                s_count, f_count, is_mock = send_custom_broadcast_sms(
                    custom_msg, 
                    recipient_type=recipient_type, 
                    specific_member_id=specific_member_id
                )
                if s_count > 0:
                    messages.success(request, f"Ujumbe maalum umetumwa kwa mafanikio kwa washiriki {s_count}!")
                elif f_count > 0:
                    messages.error(request, f"Kushindwa kutuma kwa washiriki {f_count}. Tafadhali kagua salio lako la SMS.")
                else:
                    messages.warning(request, "Hakuna washiriki waliochaguliwa au waliopo hewani.")
            return redirect('sms_settings')

        if action == 'save':
            sender_id_val = request.POST.get('sender_id', 'NEXTSMS').strip() or 'NEXTSMS'
            if config:
                config.api_key = request.POST.get('api_key', '').strip()
                config.secret_key = request.POST.get('secret_key', '').strip()
                config.sender_id = sender_id_val
                config.sms_template = request.POST.get('sms_template', '')
                config.sms_present_template = request.POST.get('sms_present_template', '')
                config.sms_absent_template = request.POST.get('sms_absent_template', '')
                config.leader_passcode = request.POST.get('leader_passcode', '1234').strip() or '1234'
                config.is_active = request.POST.get('is_active') == 'on'
                config.save()
            else:
                config = SMSConfig.objects.create(
                    api_key=request.POST.get('api_key', '').strip(),
                    secret_key=request.POST.get('secret_key', '').strip(),
                    sender_id=sender_id_val,
                    sms_template=request.POST.get('sms_template', ''),
                    sms_present_template=request.POST.get('sms_present_template', ''),
                    sms_absent_template=request.POST.get('sms_absent_template', ''),
                    leader_passcode=request.POST.get('leader_passcode', '1234').strip() or '1234',
                    is_active=request.POST.get('is_active') == 'on',
                )
            messages.success(request, "Mazingira ya SMS yamehifadhiwa kikamilifu!")
            return redirect('sms_settings')

        elif action == 'test_sms':
            test_phone = request.POST.get('test_phone', '').strip()
            test_message = request.POST.get('test_message', '').strip()
            if not test_phone:
                messages.error(request, "Tafadhali weka namba ya simu ya kupokea ujumbe wa jaribio.")
            elif not test_message:
                messages.error(request, "Tafadhali weka ujumbe wa jaribio.")
            else:
                test_result = send_test_sms(test_phone, test_message, config)
                if test_result['success']:
                    messages.success(request, test_result['message'])
                else:
                    messages.error(request, test_result['message'])

        elif action == 'check_balance':
            balance_info = check_nextsms_balance(config)
            if balance_info['success']:
                messages.info(request, balance_info['message'])
            else:
                messages.warning(request, balance_info['message'])

        elif action == 'reset_mock':
            if config:
                config.api_key = "MOCK_KEY"
                config.secret_key = "MOCK_SECRET"
                config.save()
            messages.info(request, "Mfumo umerejeshwa kwenye Mock Mode (jaribio) — SMS zitaandikwa kwenye logs tu bila kukata salio.")
            return redirect('sms_settings')

    if not config:
        config = SMSConfig.objects.create(api_key="MOCK_KEY", secret_key="MOCK_SECRET", sender_id="IBADA SIFA", is_active=True)

    mock_active = is_mock_mode(config)
    
    # Auto-load balance for instant display
    if not balance_info:
        try:
            balance_info = check_nextsms_balance(config)
        except Exception:
            balance_info = None

    context = {
        'config': config,
        'mock_active': mock_active,
        'test_result': test_result,
        'balance_info': balance_info,
        'washiriki': Mshiriki.objects.filter(is_active=True).order_by('jina'),
    }
    return render(request, 'sms_settings.html', context)


@leader_required
def sms_logs(request):
    """Ukurasa wa kumbukumbu za SMS zote zilizotumwa."""
    logs = SMSLog.objects.all()[:200]
    sms_type_filter = request.GET.get('type', '')
    if sms_type_filter:
        logs = SMSLog.objects.filter(type=sms_type_filter)[:200]

    stats = {
        'total': SMSLog.objects.count(),
        'success': SMSLog.objects.filter(status='SUCCESS').count(),
        'mockup': SMSLog.objects.filter(status='MOCKUP').count(),
        'failed': SMSLog.objects.filter(status='FAILED').count(),
    }
    return render(request, 'sms_logs.html', {'logs': logs, 'stats': stats, 'sms_type_filter': sms_type_filter})


@leader_required
def members_list(request):
    """Orodha ya washiriki wote waliosajiliwa."""
    washiriki = Mshiriki.objects.all().order_by('jina')
    washiriki_count = washiriki.count()
    active_count = washiriki.filter(is_active=True).count()
    inactive_count = washiriki_count - active_count
    return render(request, 'members_list.html', {
        'washiriki': washiriki,
        'washiriki_count': washiriki_count,
        'active_count': active_count,
        'inactive_count': inactive_count,
    })


@leader_required
def toggle_member_active(request, member_id):
    """Washa au zima mshiriki (active/inactive)."""
    if request.method == 'POST':
        mshiriki = get_object_or_404(Mshiriki, id=member_id)
        mshiriki.is_active = not mshiriki.is_active
        mshiriki.save()
        hali = "imewashwa" if mshiriki.is_active else "imezimwa"
        messages.success(request, f"{mshiriki.jina} sasa {hali} kwenye mfumo.")
    return redirect('members_list')


@leader_required
def send_rsvp_reminder(request, ibada_id):
    """Tuma SMS za kikumbusho kwa wale ambao hawajajaza RSVP."""
    if request.method == 'POST':
        ibada = get_object_or_404(Ibada, id=ibada_id)
        
        rsvp_member_ids = Uthibitisho.objects.filter(ibada=ibada).values_list('mshiriki_id', flat=True)
        missing_members = Mshiriki.objects.filter(is_active=True).exclude(id__in=rsvp_member_ids)
        
        if not missing_members.exists():
            messages.info(request, "Washiriki wote tayari wamejaza RSVP kwa ibada hii. Hakuna wa kukumbusha.")
        else:
            success_count, fail_count, use_mockup = send_rsvp_reminder_sms(ibada, list(missing_members))
            status_type = "Mockup Mode (Logs)" if use_mockup else "Live Gateway"
            messages.success(
                request,
                f"Kikumbusho kimetumwa kwa {success_count} washiriki ({status_type}). "
                f"Zilizofeli: {fail_count}."
            )

    return redirect('leader_dashboard')
