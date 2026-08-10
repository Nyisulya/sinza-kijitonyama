from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from kanda.models import Ibada
from kanda.sms_helper import send_bulk_ibada_sms

class Command(BaseCommand):
    help = 'Inatuma SMS za mwaliko kwa washiriki wote asubuhi ya Jumapili kwa ajili ya ibada ya siku hiyo.'

    def handle(self, *args, **options):
        self.stdout.write("Inaanza mchakato wa kutuma SMS za mwaliko...")

        now = timezone.now()
        # Find meetings scheduled for today (within the next 18 hours)
        end_of_day = now + timedelta(hours=18)
        
        ibada = Ibada.objects.filter(
            is_completed=False,
            tarehe_muda__gte=now - timedelta(hours=2), # Include meetings starting very recently
            tarehe_muda__lte=end_of_day
        ).order_by('tarehe_muda').first()

        if not ibada:
            # Fallback: find the single next upcoming meeting
            ibada = Ibada.objects.filter(
                is_completed=False,
                tarehe_muda__gte=now
            ).order_by('tarehe_muda').first()
            
            if ibada:
                self.stdout.write(self.style.WARNING(
                    f"Hakuna ibada iliyopatikana kwa leo. Mfumo utatumia ibada ijayo ya tarehe {ibada.tarehe_muda} kama mbadala."
                ))

        if not ibada:
            self.stdout.write(self.style.ERROR("Hakuna ibada yoyote iliyopangwa au ambayo haijakamilika katika mfumo! SMS hazijatumwa."))
            return

        self.stdout.write(f"Ibada inayotumika: Familia ya {ibada.mwenyeji} wa tarehe {ibada.tarehe_muda}")

        success_count, fail_count, use_mockup = send_bulk_ibada_sms(ibada)

        if success_count > 0:
            status_type = "MOCKUP (Logs only)" if use_mockup else "LIVE GATEWAY"
            self.stdout.write(self.style.SUCCESS(
                f"Kazi Imekamilika! Njia: {status_type}. Zilizotuma kwa mafanikio: {success_count}, Zilizofeli: {fail_count}."
            ))
        else:
            self.stdout.write(self.style.WARNING("Hakuna washiriki wanaopokea SMS au utumaji umefeli kikamilifu."))
