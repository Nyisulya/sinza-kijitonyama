from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Mshiriki, Ibada, Uthibitisho, SMSConfig, Mahudhurio, SMSLog
from .sms_helper import send_bulk_ibada_sms, send_attendance_sms, send_rsvp_reminder_sms
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

    context = {
        'upcoming_ibada': upcoming_ibada,
        'washiriki': washiriki,
    }
    return render(request, 'home.html', context)

def register_member(request):
    if request.method == 'POST':
        jina = request.POST.get('jina')
        simu = request.POST.get('simu')
        familia = request.POST.get('familia', '')

        try:
            mshiriki = Mshiriki(jina=jina, simu=simu, familia=familia)
            mshiriki.full_clean()
            mshiriki.save()
            messages.success(request, f"Hongera! {jina} amesajiliwa kikamilifu kwenye Kanda ya Sinza na Kijitonyama.")
        except Exception as e:
            messages.error(request, f"Imeshindwa kusajili: {e}")

    return redirect('home')

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
    rsvps = []
    rsvp_yes_count = 0
    rsvp_no_count = 0
    rsvp_transport_count = 0
    missing_members = Mshiriki.objects.filter(is_active=True)

    if upcoming_ibada:
        rsvps = Uthibitisho.objects.filter(ibada=upcoming_ibada)
        rsvp_yes_count = rsvps.filter(status='NITAKUJA').count()
        rsvp_no_count = rsvps.filter(status='SITAFANIKIWA').count()
        rsvp_transport_count = rsvps.filter(status='NAHITAJI_USAFIRI').count()
        
        # Exclude those who did RSVP from missing_members
        rsvp_member_ids = rsvps.values_list('mshiriki_id', flat=True)
        missing_members = missing_members.exclude(id__in=rsvp_member_ids)
        
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
        'rsvps': rsvps,
        'rsvp_yes_count': rsvp_yes_count + rsvp_transport_count,
        'rsvp_no_count': rsvp_no_count,
        'rsvp_transport_count': rsvp_transport_count,
        'missing_members': missing_members,
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
                messages.success(request, f"Njia ya Majaribio (Mockup Mode): SMS {success_count} za mwaliko zimetengenezwa na kuhifadhiwa kwenye kumbukumbu za mfumo (Logs) kwa sababu API key haijawekwa.")
            else:
                messages.success(request, f"SMS {success_count} za mwaliko zimetumwa kikamilifu kupitia SMS gateway!")
        elif success_count > 0:
            messages.warning(request, f"SMS {success_count} zilitumwa lakini {fail_count} zimeshindwa kutumwa. Tafadhali angalia mazingira ya SMS.")
        else:
            messages.error(request, "SMS hazikutumwa kabisa. Hakuna washiriki waliosajiliwa au mazingira ya SMS yamezima.")

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
            
            # Send SMS
            success_count, fail_count, use_mockup = send_attendance_sms(ibada, present_members, absent_members)
            
            status_type = "Mockup Mode (Logs)" if use_mockup else "Live Gateway"
            messages.success(
                request, 
                f"Mahudhurio yamehifadhiwa na ibada imewekwa kama Imekamilika! "
                f"SMS za shukrani na faraja zimetumwa kwa wote ({status_type}). "
                f"Zilizotuma: {success_count}, Zilizofeli: {fail_count}."
            )
        except Exception as e:
            messages.error(request, f"Imeshindwa kuhifadhi mahudhurio: {e}")
            
    return redirect('leader_dashboard')

def leader_login(request):
    if request.method == 'POST':
        passcode = request.POST.get('passcode')
        
        # Retrieve config passcode
        config = SMSConfig.objects.filter(is_active=True).first()
        actual_passcode = config.leader_passcode if (config and config.leader_passcode) else "1234"
        
        if passcode == actual_passcode:
            request.session['is_leader'] = True
            messages.success(request, "Karibu kwenye sehemu ya viongozi!")
            return redirect('leader_dashboard')
        else:
            messages.error(request, "Neno la siri si sahihi! Tafadhali jaribu tena.")
            
    return render(request, 'leader_login.html')

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
    """Ukurasa wa mazingira ya SMS (API keys, templates, neno la siri)."""
    config = SMSConfig.objects.filter(is_active=True).first()

    if request.method == 'POST':
        action = request.POST.get('action', 'save')

        if action == 'save':
            if config:
                config.api_key = request.POST.get('api_key', '').strip()
                config.secret_key = request.POST.get('secret_key', '').strip()
                config.sender_id = request.POST.get('sender_id', 'KANDA').strip() or 'KANDA'
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
                    sender_id=request.POST.get('sender_id', 'KANDA').strip() or 'KANDA',
                    sms_template=request.POST.get('sms_template', ''),
                    sms_present_template=request.POST.get('sms_present_template', ''),
                    sms_absent_template=request.POST.get('sms_absent_template', ''),
                    leader_passcode=request.POST.get('leader_passcode', '1234').strip() or '1234',
                    is_active=True,
                )
            messages.success(request, "Mazingira ya SMS yamehifadhiwa kikamilifu!")
        elif action == 'reset_mock':
            config.api_key = "MOCK_KEY"
            config.secret_key = "MOCK_SECRET"
            config.save()
            messages.info(request, "Mfumo umerejeshwa kwenye Mock Mode (jaribio) — SMS zitaandikwa kwenye logs tu.")

        return redirect('sms_settings')

    # Mapinduzi ya templates za default ikiwa hazipo
    if not config:
        config = SMSConfig(api_key="MOCK_KEY", secret_key="MOCK_SECRET", sender_id="KANDA")

    context = {
        'config': config,
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
