# ⛪ Kanda Connect — Manzese SDA (Sinza na Kijitonyama)

Mfumo wa kidijitali wa kuendesha **Kanda ya Sinza na Kijitonyama** wa Kanisa la **Manzese SDA Church** (Tanzania).

Programu hii husaidia viongozi wa kanda kusimamia washiriki, kupanga ibada, kufuatilia mahudhurio, na kuwasiliana na wanakanda kiotomatiki kupitia SMS na WhatsApp.

---

## 🚀 Vipengele Vikuu

| Kipengele | Maelezo |
|---|---|
| **Usajili wa Washiriki** | Kujisajili kwa jina, namba ya simu (Tanzania), na familia |
| **Ratiba ya Ibada** | Kupanga ibada kwa familia mwenyeji, muda, ramani na somo |
| **RSVP** | Wanakanda wanaweza kuthibitisha: `Nitakuja`, `Sitafanikiwa`, au `Nahitaji Usafiri` |
| **Dashibodi ya Viongozi** | Takwimu, orodha za RSVP, na kufuatilia wale ambao hawajajibu |
| **Mahudhurio (Roll Call)** | Kuweka mahudhurio ya ibada kwa kubofya tu |
| **SMS Automatic** | Mwaliko wa SMS, SMS za shukrani, na faraja kwa wasiofika (Beem API) |
| **Historia ya Mahudhurio** | Kumbukumbu za ibada zote zilizokamilika |
| **Kumbukumbu za SMS (Logs)** | Rekodi ya SMS zote zilizotumwa / mockup |
| **WhatsApp Reminder** | Kikumbusho cha moja kwa moja kwa wale hawajajaza RSVP |

---

## 🛠️ Teknolojia

- **Python** 3.10+
- **Django** 6.0
- **SQLite** (database ya mwanzo)
- **Beem SMS API** (Tanzania SMS gateway)
- Timezone: `Africa/Dar_es_Salaam`

---

## 📦 Ufungaji (Installation)

```bash
# 1. Clone au fungua folda ya mradi
cd "sinza na kijitonyama"

# 2. Unda virtual environment
python -m venv venv

# 3. Washa virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Sakinisha packages
pip install -r requirements.txt

# 5. Fanya migrations za database
python manage.py makemigrations kanda
python manage.py migrate

# 6. Unda superuser (kwa admin panel)
python manage.py createsuperuser

# 7. Anzisha server
python manage.py runserver
```

Kisha fungua: **http://127.0.0.1:8000/**

---

## 🧭 Matumizi ya Mfumo

### Kwa Wanakanda (Washiriki)
1. Fungua ukurasa wa **Nyumbani** (`/`)
2. Ukiwa hujasajiliwa — jisajili kwenye fomu ya **Jisajili Kwenye Kanda** (kulia)
3. Chagua ibada ijayo, kisha **Thibitisha Mahudhurio (RSVP)**:
   - ✅ **Nitakuja**
   - ❌ **Sitafanikiwa**
   - 🚗 **Nahitaji Usafiri**
4. Angalia **Ratiba ya Ibada** (`/schedule/`) kwa ibada zote zilizopangwa

### Kwa Viongozi
1. Bofya **Kiongozi Panel** kwenye navigation
2. Ingiza **Neno la Siri** (default: `1234` — badilisha kwenye admin/SMS Settings)
3. Kwenye Dashibodi unaweza:
   - Kuona **takwimu** (washiriki, wanaokuja, hawaji, wanahitaji usafiri)
   - **Sajili Ibada Mpya**
   - **Tuma SMS za Mwaliko** kwa washiriki wote
   - **Anza Mahudhurio (Roll Call)** — weka nani alikuja / hakuja
   - Kuona **Historia ya Mahudhurio**
   - **Kufuatilia** washiriki walioachia kujaza RSVP (WhatsApp reminder)

### SMS Gateway (Beem)
Weka API keys kwenye **Admin Panel** → **SMS Settings** (au kwenye mazingira ya viongozi):
- `API Key` — kutoka Beem dashboard
- `Secret Key`
- `Sender ID` (default: `KANDA`)
- Templates za SMS zinaweza kubadilishwa

> 💡 **Mock Mode**: Ikiwa API keys hazijawekwa (au zina `MOCK_KEY`), SMS zitaandikwa kwenye **kumbukumbu za mfumo (SMS Logs)** badala ya kutumwa kweli. Hii inakusaidia kujaribu bila gharama.

---

## 📂 Muundo wa Mradi

```
sinza na kijitonyama/
├── kanda/                    # App kuu
│   ├── management/commands/  # Custom commands (send_sunday_reminders)
│   ├── migrations/
│   ├── admin.py              # Admin panel
│   ├── models.py             # Database models
│   ├── views.py              # Logic ya kurasa
│   ├── urls.py               # Routes
│   └── sms_helper.py         # Beem SMS integration
├── kanda_connect/            # Project settings
├── templates/                # HTML templates
├── static/                   # CSS, JS
├── db.sqlite3                # Database
└── manage.py
```

---

## ⏰ Reminder ya Kiotomatiki (Cron / Task Scheduler)

Ili kutuma SMS za mwaliko **kiotomatiki asubuhi ya Jumapili**:

```bash
python manage.py send_sunday_reminders
```

Weka hii kwenye task scheduler / cron kwa kila Jumapili asubuhi (mfano: `0 7 * * 0`).

---

## 🧪 Kupima (Tests)

```bash
python manage.py test kanda
```

Mfumo unajumuisha tests za:
- Usafi wa namba za simu za Tanzania
- RSVP submission
- Uundaji wa ibada
- Mahudhurio
- Usalama wa dashibodi (passcode)

---

## 🔒 Usalama

- Dashibodi ya viongozi inalindwa na **neno la siri** (session-based)
- Namba za simu zinasafishwa na kuthibitishwa kwa muundo wa Tanzania (`07...` → `2557...`)
- Badilisha `SECRET_KEY` kwenye `kanda_connect/settings.py` kabla ya production

---

## 📜 Leseni

Programu ya ndani ya Kanisa la Manzese SDA — imetengenezwa kwa ajili ya matumizi ya kanda ya Sinza na Kijitonyama.

---

*Imetengenezwa kwa Upendo ❤️ — Manzese SDA Church (Sinza na Kijitonyama Zone)*
