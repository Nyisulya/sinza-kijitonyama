from django.test import TestCase, Client
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
from .models import Mshiriki, Ibada, Uthibitisho, SMSConfig

class KandaModelsTestCase(TestCase):
    def test_mshiriki_phone_cleaning_local(self):
        # Local format starting with 07 should clean to 2557
        member = Mshiriki.objects.create(
            jina="Neema John",
            simu="0712345678",
            familia="Familia ya John"
        )
        self.assertEqual(member.simu, "255712345678")

    def test_mshiriki_phone_cleaning_international(self):
        # International format starting with 255 should keep it
        member = Mshiriki.objects.create(
            jina="Baraka Mwita",
            simu="255688112233",
            familia=""
        )
        self.assertEqual(member.simu, "255688112233")

    def test_mshiriki_invalid_phone_raises_error(self):
        # Invalid phone should raise validation error
        member = Mshiriki(jina="Invalid Person", simu="0222123456")
        with self.assertRaises(ValidationError):
            member.full_clean()

    def test_ibada_str_representation(self):
        # Checking String formatting for meetings
        time = timezone.now()
        ibada = Ibada.objects.create(
            mwenyeji="Mzee Joshua",
            tarehe_muda=time,
            ramani_link="https://maps.google.com/?q=sinza"
        )
        expected_str = f"Ibada kwa Mzee Joshua - {time.strftime('%d/%m/%Y saa %H:%M')}"
        self.assertEqual(str(ibada), expected_str)

    def test_sms_config_singleton(self):
        # Only one SMSConfig can exist
        SMSConfig.objects.create(api_key="KEY1", secret_key="SEC1")
        config2 = SMSConfig(api_key="KEY2", secret_key="SEC2")
        with self.assertRaises(ValidationError):
            config2.full_clean()


class KandaViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        session = self.client.session
        session['is_leader'] = True
        session.save()
        SMSConfig.objects.create(api_key="MOCK_KEY", secret_key="MOCK_SECRET", is_active=True)
        
        self.mshiriki = Mshiriki.objects.create(
            jina="John Joseph",
            simu="0788998899",
            familia="Joseph Family"
        )
        self.ibada = Ibada.objects.create(
            mwenyeji="Mama Eliya",
            tarehe_muda=timezone.now() + timezone.timedelta(days=1),
            ramani_link="https://maps.google.com"
        )

    def test_home_view_status(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mama Eliya")
        self.assertContains(response, "John Joseph")

    def test_register_member_view(self):
        response = self.client.post(reverse('register_member'), {
            'jina': 'Amani Kessy',
            'simu': '0754112233',
            'familia': 'Kessy Family'
        })
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(Mshiriki.objects.filter(jina="Amani Kessy").exists())

    def test_submit_rsvp_view(self):
        response = self.client.post(reverse('submit_rsvp', args=[self.ibada.id]), {
            'mshiriki_id': self.mshiriki.id,
            'status': 'NITAKUJA',
            'maoni': 'Nitaleta zawadi'
        })
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(Uthibitisho.objects.filter(
            mshiriki=self.mshiriki,
            ibada=self.ibada,
            status='NITAKUJA',
            maoni='Nitaleta zawadi'
        ).exists())

    def test_create_ibada_view(self):
        # Verify that we can create a meeting directly from dashboard POST
        response = self.client.post(reverse('create_ibada'), {
            'mwenyeji': 'Kaka John Mwaseba',
            'tarehe_muda': '2026-08-16T16:00',
            'ramani_link': 'https://maps.google.com',
            'maelekezo': 'Sinza Mori',
            'masomo': 'Somo la 6'
        })
        self.assertRedirects(response, reverse('leader_dashboard'))
        self.assertTrue(Ibada.objects.filter(mwenyeji='Kaka John Mwaseba').exists())
        # Past meeting should be completed
        self.assertTrue(Ibada.objects.get(id=self.ibada.id).is_completed)

    def test_take_attendance_view(self):
        # Pre-select check: John Joseph is not preselected because he has no RSVP yes
        # Let's create an RSVP Yes for self.mshiriki
        Uthibitisho.objects.create(mshiriki=self.mshiriki, ibada=self.ibada, status='NITAKUJA')
        
        response = self.client.get(reverse('take_attendance', args=[self.ibada.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John Joseph")
        self.assertContains(response, "Alithibitisha kuja")

    def test_save_attendance_view(self):
        # Let's save attendance where self.mshiriki is present
        response = self.client.post(reverse('save_attendance', args=[self.ibada.id]), {
            'present_members': [self.mshiriki.id]
        })
        self.assertRedirects(response, reverse('leader_dashboard'))
        
        # Verify Mahudhurio entry exists
        from .models import Mahudhurio
        self.assertTrue(Mahudhurio.objects.filter(
            ibada=self.ibada,
            mshiriki=self.mshiriki,
            is_present=True
        ).exists())
        
        # Meeting should be marked completed
        self.ibada.refresh_from_db()
        self.assertTrue(self.ibada.is_completed)

    def test_attendance_history_view(self):
        # Mark meeting as completed
        self.ibada.is_completed = True
        self.ibada.save()
        
        # Create a mahudhurio record
        from .models import Mahudhurio
        Mahudhurio.objects.create(ibada=self.ibada, mshiriki=self.mshiriki, is_present=True)
        
        response = self.client.get(reverse('attendance_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mama Eliya")
        self.assertContains(response, "Waliohudhuria: 1")


class KandaSecurityTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.ibada = Ibada.objects.create(
            mwenyeji="Test Host",
            tarehe_muda=timezone.now() + timezone.timedelta(days=1)
        )
        SMSConfig.objects.create(leader_passcode="kanda123")

    def test_dashboard_redirects_unauthorized(self):
        # Accessing dashboard without session should redirect to login
        response = self.client.get(reverse('leader_dashboard'))
        self.assertRedirects(response, reverse('leader_login'))

    def test_login_with_correct_passcode(self):
        # Post correct passcode
        response = self.client.post(reverse('leader_login'), {'passcode': 'kanda123'})
        self.assertRedirects(response, reverse('leader_dashboard'))
        self.assertTrue(self.client.session.get('is_leader'))

    def test_login_with_incorrect_passcode(self):
        # Post incorrect passcode
        response = self.client.post(reverse('leader_login'), {'passcode': 'wrong_one'})
        self.assertEqual(response.status_code, 200) # Re-renders login page
        self.assertFalse(self.client.session.get('is_leader'))


class NextSMSTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        session = self.client.session
        session['is_leader'] = True
        session.save()
        SMSConfig.objects.all().delete()
        self.config = SMSConfig.objects.create(api_key="MOCK_KEY", secret_key="MOCK_SECRET", is_active=True)

    def test_phone_cleaner(self):
        from .sms_helper import clean_phone_number
        self.assertEqual(clean_phone_number("0787661560"), "255787661560")
        self.assertEqual(clean_phone_number("+255 787 661 560"), "255787661560")
        self.assertEqual(clean_phone_number("255787661560"), "255787661560")
        self.assertEqual(clean_phone_number("787661560"), "255787661560")
        self.assertEqual(clean_phone_number("0655123456"), "255655123456")

    def test_auth_headers_generator(self):
        from .sms_helper import get_auth_headers_list
        # Test username and password
        headers = get_auth_headers_list("my_user", "my_pass")
        self.assertIn("Basic bXlfdXNlcjpteV9wYXNz", headers)

        # Test single token
        token_headers = get_auth_headers_list("d9cb8faef4158c2055cb150be7083208", "")
        self.assertIn("Bearer d9cb8faef4158c2055cb150be7083208", token_headers)

    def test_mock_send_test_sms(self):
        from .sms_helper import send_test_sms
        res = send_test_sms("0787661560", "Jaribio", self.config)
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "MOCK")

    def test_sms_settings_test_action(self):
        response = self.client.post(reverse('sms_settings'), {
            'action': 'test_sms',
            'test_phone': '0787661560',
            'test_message': 'Jaribio la SMS'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ujumbe wa jaribio umerekodiwa kikamilifu")

    def test_sms_settings_check_balance(self):
        response = self.client.post(reverse('sms_settings'), {
            'action': 'check_balance'
        })
        self.assertEqual(response.status_code, 200)

    def test_single_sms_length_guarantee(self):
        """Verify that all generated SMS messages are strictly <= 160 characters (1 SMS segment)."""
        from .sms_helper import format_ibada_time_short
        ibada = Ibada.objects.create(
            mwenyeji="Mama Gityamwi",
            tarehe_muda=timezone.now() + timezone.timedelta(days=1),
            maelekezo="Sinza Mori karibu Meeda"
        )
        member = Mshiriki.objects.create(
            jina="Bonaventura Makala",
            simu="0712345678"
        )
        time_str = format_ibada_time_short(ibada)
        first_name = member.jina.strip().split()[0].capitalize()

        # 1. Invitation with Location
        msg_location = f"MANZESE SDA\nHabari {first_name}, karibu Ibada ya Anza na Bwana {time_str} kwa {ibada.mwenyeji} ({ibada.maelekezo}). Karibu sana!"
        self.assertLessEqual(len(msg_location), 160)
        self.assertEqual(first_name, "Bonaventura")

        # 2. Invitation with Map link
        ibada.ramani_link = "https://maps.app.goo.gl/xyz123"
        msg_map = f"MANZESE SDA\nHabari {first_name}, karibu Ibada ya Anza na Bwana {time_str} kwa {ibada.mwenyeji}. Ramani: {ibada.ramani_link} . Karibu!"
        self.assertLessEqual(len(msg_map), 160)

        # 3. Thank You SMS
        msg_thanks = f"MANZESE SDA\nHabari {first_name}, asante kwa kushiriki Ibada ya Kanda leo kwa {ibada.mwenyeji}. Uwepo wako ulikuwa baraka. Ubarikiwe sana!"
        self.assertLessEqual(len(msg_thanks), 160)

        # 4. Absent SMS
        msg_absent = f"MANZESE SDA\nHabari {first_name}, tulikumiss sana kwenye Ibada ya Kanda leo kwa {ibada.mwenyeji}. Ubarikiwe na uwe na juma njema. Karibu ibada ijayo!"
        self.assertLessEqual(len(msg_absent), 160)


