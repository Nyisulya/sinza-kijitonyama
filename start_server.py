"""Anzisha Django server kwenye background (mchakato tofauti unaoendelea kukimbia)."""
import subprocess
import sys
import os

log_file = open("server.log", "w", encoding="utf-8")
flags = 0
if os.name == "nt":
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

proc = subprocess.Popen(
    [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
    stdout=log_file,
    stderr=subprocess.STDOUT,
    creationflags=flags,
    close_fds=True,
)
print(f"Server imeanza kwenye background! PID: {proc.pid}")
print("Fungua: http://127.0.0.1:8000/")
