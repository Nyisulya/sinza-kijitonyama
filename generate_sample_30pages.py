# -*- coding: utf-8 -*-
"""
generate_sample_30pages.py
==========================
Script ya sampuli: inazalisha PDF yenye KURASA 30 za majaribio.
Matumizi:  python generate_sample_30pages.py
PDF:       Sampuli_Kurasa30.pdf
"""

from fpdf import FPDF

EXAM_TITLE = "SEMESTER 02 FINAL UE"
SUBJECT    = "Sampuli ya Majibu - Kurasa 30"
TOTAL      = 30

class AnswerPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(30, 58, 138)          # bluu giza
        self.cell(0, 8, EXAM_TITLE + "  |  " + SUBJECT, align="L")
        self.ln(2)
        self.set_draw_color(30, 58, 138)
        self.set_line_width(0.6)
        self.line(10, 14, 200, 14)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(30, 58, 138)
        self.set_line_width(0.6)
        self.line(10, 282, 200, 282)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Ukurasa {self.page_no()} kati ya {TOTAL}", align="C")


pdf = AnswerPDF()
pdf.set_auto_page_break(auto=True, margin=20)

for i in range(1, TOTAL + 1):
    pdf.add_page()

    # ----- Sanduku la kichwa cha ukurasa -----
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"UKURASA {i}", border=0, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ----- Maandishi ya sampuli -----
    pdf.set_text_color(40, 40, 40)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, f"SWALI {i}:", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6,
        "Huu ni ukurasa wa sampuli unaoonesha jinsi PDF ya majibu itakavyokuwa. "
        "Kila ukurasa una kichwa, namba ya ukurasa, na eneo la maandishi. "
        "Katika PDF halisi ya majibu, kila ukurasa huu ungekuwa na swali na jibu lake kamili.",
        new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ----- Sanduku la jibu -----
    pdf.set_fill_color(230, 240, 255)
    pdf.set_draw_color(30, 58, 138)
    pdf.set_text_color(30, 58, 138)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "JIBU", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_text_color(40, 40, 40)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6,
        "Hapa ndipo jibu la swali hili linaandikwa. Mwili wa jibu unaweza kuwa mrefu "
        "au mfupi kadri unavyotaka. Ukiandika jibu refu, maandishi yataendelea kwenye "
        "ukurasa unaofuata kiotomatiki na PDF itakuwa na kurasa nyingi zaidi.",
        new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ----- Orodha ndogo ya alama -----
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 7, "Mambo muhimu ya ukurasa huu:", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(40, 40, 40)
    for point in ["Kichwa cha ukurasa kina jina la mtihani.",
                  "Namba ya ukurasa inaonekana chini (footer).",
                  "Rangi ya bluu inatumika kwa vichwa na mipaka."]:
        pdf.cell(5, 6)
        pdf.cell(0, 6, "- " + point, new_x="LMARGIN", new_y="NEXT")

    # ----- Baadhi ya kurasa ziwe na maandishi zaidi (kuonesha mtiririko) -----
    if i % 3 == 0:
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6,
            "Hii ni sehemu ya ziada inayoonesha kwamba ukurasa unaweza kujaa maandishi "
            "zaidi. Katika PDF ya majibu halisi, kila ukurasa ungekuwa na maelezo kamili "
            "ya jibu la swali husika. Unaweza kuona kwamba muundo unabaki nadhifu na "
            "usomaji ni rahisi hata kama kuna maandishi mengi.",
            new_x="LMARGIN", new_y="NEXT")

pdf.output("Sampuli_Kurasa30.pdf")
print("[OK] Sampuli ya kurasa 30 imezalishwa: Sampuli_Kurasa30.pdf")
