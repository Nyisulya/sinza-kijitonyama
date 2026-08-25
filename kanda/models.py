from django.db import models
from django.core.exceptions import ValidationError
import re

class Mshiriki(models.Model):
    JUKUMU_CHOICES = [
        ('KIONGOZI', 'Kiongozi wa Kanda'),
        ('MSHIRIKI', 'Mshiriki wa Kanda'),
    ]

    jina = models.CharField(max_length=150, verbose_name="Jina Kamili")
    simu = models.CharField(max_length=15, verbose_name="Namba ya Simu", help_text="Mfano: 0712345678 au 255712345678")
    familia = models.CharField(max_length=150, blank=True, verbose_name="Jina la Familia", help_text="Mfano: Familia ya Mzee Kamau")
    jukumu = models.CharField(max_length=20, choices=JUKUMU_CHOICES, default='MSHIRIKI', verbose_name="Jukumu")
    cheo = models.CharField(max_length=100, blank=True, default="Kiongozi wa Kanda", verbose_name="Cheo / Wadhifa", help_text="Mfano: Mwenyekiti wa Kanda, Mzee wa Kanda, Katibu, n.k.")
    picha = models.FileField(upload_to='viongozi/', blank=True, null=True, verbose_name="Picha ya Kiongozi / Mshiriki")
    is_active = models.BooleanField(default=True, verbose_name="Yuko Active?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarehe ya Kusajiliwa")

    class Meta:
        verbose_name = "Mshiriki"
        verbose_name_plural = "Washiriki"
        ordering = ['jina']

    def clean(self):
        # Validate and clean Tanzanian phone numbers
        phone = self.simu.strip().replace(" ", "").replace("+", "")
        if re.match(r'^(06|07|01)\d{8}$', phone):
            # Convert 07... to 2557...
            self.simu = "255" + phone[1:]
        elif re.match(r'^255\d{9}$', phone):
            self.simu = phone
        else:
            raise ValidationError({'simu': 'Tafadhali weka namba ya simu ya Tanzania iliyo sahihi (Mfano: 0712345678 au 255712345678)'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.jina} ({self.get_jukumu_display()})"


class Ibada(models.Model):
    mwenyeji = models.CharField(max_length=150, verbose_name="Familia Mwenyeji (Host)", help_text="Mfano: Mzee Joshua au Kijitonyama")
    tarehe_muda = models.DateTimeField(verbose_name="Tarehe na Muda wa Ibada")
    ramani_link = models.URLField(blank=True, null=True, verbose_name="Kiungo cha Ramani (Google Maps)", help_text="Mfano: https://maps.google.com/?q=...")
    maelekezo = models.TextField(blank=True, verbose_name="Maelekezo ya kufika", help_text="Maelekezo mafupi kama: Karibu na Kanisa la Lutheran Sinza")
    masomo = models.TextField(blank=True, verbose_name="Somo au Mada ya Kujadili", help_text="Mfano: Somo la 5 la Kitabu cha Mwongozo wa Kujifunza Biblia")
    is_completed = models.BooleanField(default=False, verbose_name="Ibada Imekamilika?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ibada"
        verbose_name_plural = "Ibada za Kanda"
        ordering = ['-tarehe_muda']

    def __str__(self):
        # Format date for display in Swahili
        formatted_date = self.tarehe_muda.strftime("%d/%m/%Y saa %H:%M")
        return f"Ibada kwa {self.mwenyeji} - {formatted_date}"


class Uthibitisho(models.Model):
    STATUS_CHOICES = [
        ('NITAKUJA', 'Nitakuja'),
        ('SITAFANIKIWA', 'Sitafanikiwa'),
        ('NAHITAJI_USAFIRI', 'Nitakuja, Nahitaji Usafiri'),
    ]

    mshiriki = models.ForeignKey(Mshiriki, on_delete=models.CASCADE, verbose_name="Mshiriki")
    ibada = models.ForeignKey(Ibada, on_delete=models.CASCADE, verbose_name="Ibada")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Hali ya Mahudhurio")
    maoni = models.TextField(blank=True, null=True, verbose_name="Maelezo/Maoni ya ziada", help_text="Mfano: Nitachelewa kidogo au nina wageni 2")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Muda wa Kujaza")

    class Meta:
        verbose_name = "Uthibitisho wa Mahudhurio (RSVP)"
        verbose_name_plural = "Uthibitisho wa Mahudhurio (RSVPs)"
        unique_together = ('mshiriki', 'ibada')

    def __str__(self):
        return f"{self.mshiriki.jina} -> {self.get_status_display()} kwa {self.ibada.mwenyeji}"


class SMSConfig(models.Model):
    api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="Username / API Key ya Next SMS", help_text="Username ya akaunti yako ya Next SMS au API Key")
    secret_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="Password / Secret Key ya Next SMS", help_text="Password ya akaunti ya Next SMS au API Secret")
    sender_id = models.CharField(max_length=20, default="NEXTSMS", verbose_name="Sender ID ya SMS", help_text="Jina la mtumaji lililoidhinishwa, mfano: NEXTSMS, CHURCH, au KANISA")
    sms_template = models.TextField(
        default="Habari {jina}, ibada yetu ya Kanda ya Sinza & Kijitonyama itafanyika leo Jumapili kwa familia ya {mwenyeji} saa {muda}. Karibu sana! Ramani: {ramani_link}",
        verbose_name="Kiolezo cha Mwaliko (SMS Template)",
        help_text="Tumia mabano ya {jina}, {mwenyeji}, {muda}, na {ramani_link} ili mfumo uweke taarifa zenyewe kiotomatiki."
    )
    sms_present_template = models.TextField(
        default="Habari {jina}, asante sana kwa kuhudhuria ibada ya kanda leo kwa familia ya {mwenyeji}. Uwepo wako ulikuwa baraka kubwa sana! Ubarikiwe.",
        verbose_name="Kiolezo cha Waliopo (Thank You SMS)",
        help_text="Tumia mabano ya {jina} na {mwenyeji}."
    )
    sms_absent_template = models.TextField(
        default="Habari {jina}, tulikumiss sana kwenye ibada ya kanda leo kwa familia ya {mwenyeji}. Tunakuombea na karibu sana tujumuike pamoja Jumapili ijayo!",
        verbose_name="Kiolezo cha Wasiofika (Encouragement SMS)",
        help_text="Tumia mabano ya {jina} na {mwenyeji}."
    )
    is_active = models.BooleanField(default=True, verbose_name="Mfumo wa SMS Uko Active?")
    leader_passcode = models.CharField(
        max_length=20, 
        default="1234", 
        verbose_name="Neno la Siri la Viongozi",
        help_text="Neno la siri la kuingia kwenye Dashibodi ya Viongozi"
    )

    class Meta:
        verbose_name = "Mazingira ya SMS (SMS Setting)"
        verbose_name_plural = "Mazingira ya SMS (SMS Settings)"

    def clean(self):
        # Prevent multiple configs
        if SMSConfig.objects.exists() and not self.pk:
            raise ValidationError("Unaweza kuwa na Mazingira ya SMS moja tu ya mfumo.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        status = "Active" if self.is_active else "In-Active"
        return f"Mazingira ya SMS ({status})"


class Mahudhurio(models.Model):
    ibada = models.ForeignKey(Ibada, on_delete=models.CASCADE, verbose_name="Ibada")
    mshiriki = models.ForeignKey(Mshiriki, on_delete=models.CASCADE, verbose_name="Mshiriki")
    is_present = models.BooleanField(default=False, verbose_name="Alihudhuria?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mahudhurio"
        verbose_name_plural = "Mahudhurio ya Kanda"
        unique_together = ('ibada', 'mshiriki')

    def __str__(self):
        hali = "Alihudhuria" if self.is_present else "Hakuhudhuria"
        return f"{self.mshiriki.jina} -> {hali} kwenye ibada ya {self.ibada.mwenyeji}"


class SMSLog(models.Model):
    STATUS_CHOICES = [
        ('SUCCESS', 'Imefanikiwa'),
        ('FAILED', 'Imeshindwa'),
        ('MOCKUP', 'Mockup (Jaribio)'),
    ]

    TYPE_CHOICES = [
        ('INVITATION', 'Mwaliko wa Ibada'),
        ('THANK_YOU', 'Shukrani (Alihudhuria)'),
        ('ENCOURAGEMENT', 'Faraja (Hakuhudhuria)'),
        ('REMINDER', 'Kikumbusho cha RSVP'),
    ]

    mshiriki = models.ForeignKey(Mshiriki, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Mshiriki")
    ibada = models.ForeignKey(Ibada, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Ibada")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='INVITATION', verbose_name="Aina ya SMS")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='MOCKUP', verbose_name="Hali ya Utumaji")
    phone = models.CharField(max_length=20, verbose_name="Namba ya Simu")
    message = models.TextField(verbose_name="Ujumbe")
    error = models.TextField(blank=True, null=True, verbose_name="Hitilafu (Ikiwa Ipo)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Muda wa Kutumwa")

    class Meta:
        verbose_name = "Rekodi ya SMS"
        verbose_name_plural = "Kumbukumbu za SMS"
        ordering = ['-created_at']

    def __str__(self):
        return f"SMS {self.get_type_display()} -> {self.phone} ({self.get_status_display()})"
