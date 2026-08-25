import os, sys
base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base)
sys.path.insert(0, os.path.join(base, "deps"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kanda_connect.settings")
import django
django.setup()
from django.contrib.auth.models import User
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@example.com", "admin123")
    print("Superuser 'admin' created (password: admin123)")
else:
    print("Superuser 'admin' already exists")
