"""Launcher: adds local deps (Django) to path and runs Django commands."""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
deps = os.path.join(BASE, "deps")
if deps not in sys.path:
    sys.path.insert(0, deps)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kanda_connect.settings")

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
