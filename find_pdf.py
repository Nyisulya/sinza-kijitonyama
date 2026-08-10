# -*- coding: utf-8 -*-
"""Script ya kutafuta database 1.pdf kwenye maeneo ya kawaida."""
import os

targets = [
    r"C:\Users\felic\Downloads",
    r"C:\Users\felic\Desktop",
    r"C:\Users\felic\Documents",
    r"D:\projects\django1\sinza na kijitonyama",
]

for base in targets:
    if not os.path.isdir(base):
        continue
    for root, dirs, files in os.walk(base):
        for f in files:
            if f.lower().endswith(".pdf"):
                full = os.path.join(root, f)
                size = os.path.getsize(full)
                print(f"{size:>10}  {full}")
