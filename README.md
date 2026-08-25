# Kanda Connect - Manzese SDA (Sinza & Kijitonyama)

Mfumo Rasmi wa Kidijitali wa Usimamizi wa Kanda ya Sinza na Kijitonyama (Kanisa la Waadventista Wasabato Manzese).

## Sifa Kuu za Mfumo:
- **Tovuti Rasmi ya Kanda:** Taarifa za ibada za nyumba kwa nyumba, maelekezo ya Google Maps, ratiba za kila wiki, na orodha ya viongozi.
- **Huduma ya SMS (NextSMS API V2):** Utumaji wa moja kwa moja wa mialiko ya ibada, shukrani kwa waliohudhuria, na faraja kwa wasiohudhuria kupitia Sender ID: `IBADA SIFA`.
- **Dashibodi ya Viongozi:** Usimamizi wa washiriki, mahudhurio ya ibada (Rollcall), ripoti, na kumbukumbu za SMS. Inalindwa na nenosiri la **`2010`**.
- **PostgreSQL Database:** Imeandaliwa kwa ajili ya seva ya uzalishaji (VPS).

---

## 🚀 Maelekezo ya Kupandisha Kwenye VPS (Ubuntu / Debian Deployment):

### 1. Sasisha Seva na Sakinisha Python, PostgreSQL na Nginx:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib nginx git libpq-dev
```

### 2. Sanidi Database ya PostgreSQL:
```bash
sudo -u postgres psql
```
Ndani ya PostgreSQL shell, andika:
```sql
CREATE DATABASE sinza;
ALTER USER postgres WITH PASSWORD 'nyisu';
GRANT ALL PRIVILEGES ON DATABASE sinza TO postgres;
\q
```

### 3. Clone Repository na Sanidi Virtual Environment:
```bash
cd /var/www
git clone https://github.com/Nyisulya/sinza-kijitonyama.git
cd sinza-kijitonyama

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Endesha Migrations na Kusanya Static Files:
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
```

### 5. Unda Akaunti ya Msimamizi (Superuser):
```bash
python manage.py createsuperuser
```

### 6. Washa Gunicorn Systemd Service:
Unda faili `/etc/systemd/system/kanda.service`:
```ini
[Unit]
Description=Gunicorn daemon for Kanda Connect Sinza
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/sinza-kijitonyama
ExecStart=/var/www/sinza-kijitonyama/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/var/www/sinza-kijitonyama/kanda.sock kanda_connect.wsgi:application

[Install]
WantedBy=multi-user.target
```
Washa huduma:
```bash
sudo systemctl daemon-reload
sudo systemctl start kanda
sudo systemctl enable kanda
```

### 7. Sanidi Nginx Server Block:
Unda `/etc/nginx/sites-available/kanda`:
```nginx
server {
    listen 80;
    server_name your_domain.com IP_ADDRESS;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root /var/www/sinza-kijitonyama;
    }
    location /media/ {
        root /var/www/sinza-kijitonyama;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/sinza-kijitonyama/kanda.sock;
    }
}
```
Washa tovuti:
```bash
sudo ln -s /etc/nginx/sites-available/kanda /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```
