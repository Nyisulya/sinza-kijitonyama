"""Command ya kujaza mfumo kwa data ya mfano (jaribio).

Matumizi:
    python manage.py create_sample_data
    python manage.py create_sample_data --clear
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from kanda.models import Mshiriki, Ibada, Uthibitisho, Mahudhurio


class Command(BaseCommand):
    help = 'Inaunda data ya mfano (washiriki, ibada, RSVP) kwa ajili ya majaribio ya mfumo.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Futa data zote zilizopo kabla ya kuunda mpya.',
        )

    def handle(self, *args, **options):
        if options['clear']:
            Mahudhurio.objects.all().delete()
            Uthibitisho.objects.all().delete()
            Ibada.objects.all().delete()
            Mshiriki.objects.all().delete()
            self.stdout.write(self.style.WARNING("Data zote za zamani zimefutwa."))

        # --- Washiriki wa mfano ---
        sample_members = [
            ("Neema John", "0712345678", "Familia ya John", "MSHIRIKI"),
            ("Baraka Mwita", "255688112233", "Familia ya Mwita", "KIONGOZI"),
            ("Amani Kessy", "0754112233", "Familia ya Kessy", "MSHIRIKI"),
            ("Grace Mwakasege", "0744332211", "Familia ya Mwakasege", "MSHIRIKI"),
            ("Emmanuel Richard", "0766554433", "Familia ya Richard", "MSHIRIKI"),
            ("Pendo Lyimo", "0788990011", "Familia ya Lyimo", "MSHIRIKI"),
            ("Josephine Chacha", "0711223344", "Familia ya Chacha", "MSHIRIKI"),
            ("John Mwaseba", "255712223344", "Familia ya Mwaseba", "KIONGOZI"),
        ]

        created_members = []
        for jina, simu, familia, jukumu in sample_members:
            mshiriki, created = Mshiriki.objects.get_or_create(
                simu=simu,
                defaults={
                    'jina': jina,
                    'familia': familia,
                    'jukumu': jukumu,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  + Mshiriki: {jina}"))
            created_members.append(mshiriki)

        # --- Ibada ya mfano (ijayo) ---
        upcoming, created = Ibada.objects.get_or_create(
            mwenyeji="Mzee Joshua",
            defaults={
                'tarehe_muda': timezone.now() + timedelta(days=3),
                'ramani_link': "https://maps.google.com/?q=sinza+mori",
                'maelekezo': "Karibu na Kanisa la Lutheran Sinza, barabara ya Mori.",
                'masomo': "Somo la 5: Ushindi wa Imani",
                'is_completed': False,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"  + Ibada ya Familia ya Mzee Joshua imeundwa."))

        # --- Ibada ya mfano (iliyokamilika) ---
        completed, created = Ibada.objects.get_or_create(
            mwenyeji="Kijitonyama",
            defaults={
                'tarehe_muda': timezone.now() - timedelta(days=7),
                'ramani_link': "https://maps.google.com/?q=kijitonyama",
                'maelekezo': "Kijitonyama, karibu na duka la kona.",
                'masomo': "Somo la 4: Nguvu ya Maombi",
                'is_completed': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"  + Ibada ya Kijitonyama imeundwa."))

        # --- RSVP kwa ibada ijayo ---
        rsvp_counts = {
            0: "NITAKUJA",
            1: "NITAKUJA",
            2: "NITAKUJA",
            3: "SITAFANIKIWA",
            4: "NAHITAJI_USAFIRI",
        }
        for idx, member in enumerate(created_members):
            if idx in rsvp_counts:
                Uthibitisho.objects.get_or_create(
                    mshiriki=member,
                    ibada=upcoming,
                    defaults={'status': rsvp_counts[idx]}
                )

        # --- Mahudhurio kwa ibada iliyokamilika ---
        for idx, member in enumerate(created_members):
            # Nusu ya washiriki walihudhuria
            Mahudhurio.objects.get_or_create(
                ibada=completed,
                mshiriki=member,
                defaults={'is_present': idx % 2 == 0}
            )

        self.stdout.write(self.style.SUCCESS(
            "\n[DONE] Data ya mfano imeundwa kikamilifu!"
            f"\n   Washiriki: {len(created_members)}"
            "\n   Ibada zinazokuja: 1, zilizokamilika: 1"
            "\n   Fungua http://127.0.0.1:8000/ kuona."
        ))
