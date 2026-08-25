"""Starting the Django server in the background."""
import subprocess, sys, os

base = os.path.dirname(os.path.abspath(__file__))
log = open(os.path.join(base, "server.log"), "w", encoding="utf-8")
flags = 0
if os.name == "nt":
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

py = sys.executable
if not os.path.exists(py) or "WindowsApps" in py:
    py = r"C:\Users\maria\AppData\Local\Programs\Python311\python.exe"

proc = subprocess.Popen(
    [py, os.path.join(base, "manage.py"), "runserver", "127.0.0.1:8000", "--noreload"],
    cwd=base,
    stdout=log,
    stderr=subprocess.STDOUT,
    creationflags=flags,
    close_fds=True,
)
print(f"Server started in background. PID: {proc.pid}")
print("Open: http://127.0.0.1:8000/")
