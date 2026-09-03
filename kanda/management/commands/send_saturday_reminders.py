from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from kanda.models import Ibada, SMSLog
from kanda.sms_helper import send_bulk_ibada_sms

class Command(BaseCommand):
    help = 'Inatuma SMS za mwaliko kwa washiriki wote Jumamosi saa 1:00 usiku kwa ajili ya ibada ya kesho Jumapili.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Tuma SMS hata kama zilishatumwa kwa ajili ya ibada hii.',
        )

    def handle(self, *args, **options):
        self.stdout.write("==================================================")
        self.stdout.write("Inaanza mchakato wa kutuma SMS za mwaliko (Jumamosi Saa 1:00 Usiku)...")
        self.stdout.write(f"Muda wa sasa (Server Time): {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S')}")

        now = timezone.now()
        # Tafuta ibada ijayo inayofanyika kesho Jumapili (ndani ya masaa 36 yajayo)
        end_window = now + timedelta(hours=36)
        
        ibada = Ibada.objects.filter(
            is_completed=False,
            tarehe_muda__gte=now,
            tarehe_muda__lte=end_window
        ).order_by('tarehe_muda').first()

        if not ibada:
            # Mbadala: Tafuta ibada inayofuata mbele zaidi
            ibada = Ibada.objects.filter(
                is_completed=False,
                tarehe_muda__gte=now
            ).order_by('tarehe_muda').first()
            
            if ibada:
                self.stdout.write(self.style.WARNING(
                    f"Taarifa: Hakuna ibada ndani ya masaa 36 yajayo. Mfumo unatumia ibada ya tarehe {ibada.tarehe_muda}."
                ))

        if not ibada:
            self.stdout.write(self.style.ERROR(
                "❌ Hakuna ibada yoyote iliyopangwa au ambayo haijakamilika katika mfumo! SMS hazijatumwa."
            ))
            return

        self.stdout.write(f"📌 Ibada iliyolengwa: Familia ya {ibada.mwenyeji} wa tarehe {timezone.localtime(ibada.tarehe_muda).strftime('%d/%m/%Y saa %H:%M')}")

        # Kagua kama SMS zilishawahi kutumwa kwa ibada hii (Ulinzi wa kutotuma mara mbili)
        already_sent = SMSLog.objects.filter(ibada=ibada, type='INVITATION', status='SUCCESS').exists()
        if already_sent and not options.get('force'):
            self.stdout.write(self.style.WARNING(
                f"⚠️ Ujumbe wa mwaliko kwa ibada hii tayari ulishawahi kutumwa kwa mafanikio. "
                f"Utumaji umesitishwa ili kuzuia kukatwa salio mara mbili. (Tumia --force kulazimisha)."
            ))
            return

        success_count, fail_count, use_mockup = send_bulk_ibada_sms(ibada)

        status_type = "MOCKUP (Jaribio kwenye Log)" if use_mockup else "LIVE GATEWAY (Next SMS)"
        if success_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f"✅ Kazi Imekamilika! Njia: {status_type}.\n"
                f"   - Zilizofanikiwa: {success_count}\n"
                f"   - Zilizofeli: {fail_count}"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"⚠️ Hakuna SMS zilizofanikiwa kutumwa. (Njia: {status_type}, Zilizofeli: {fail_count})."
            ))
        self.stdout.write("==================================================")
