# -*- coding: utf-8 -*-
"""
generate_answers_pdf.py
=======================
Script ya kutengeneza PDF ya MAJIBU ya "Semester 02 Final UE".

MATUMIZI:
    python generate_answers_pdf.py

PDF inayozalishwa: Majibu_Sem02_Final_UE.pdf
------------------------------------------------------------
Kila swali linawakilishwa kama tuple:
    ("SWALI ...", "Andika jibu kamili hapa...")

Ili kuongeza majibu, ongeza tu vitu vipya kwenye orodha ya
ANSWERS hapa chini, kisha endesha script tena.
"""

from fpdf import FPDF

# ----------------------------------------------------------------------
# TAARIFA ZA MTIHANI
# ----------------------------------------------------------------------
EXAM_TITLE = "SEMESTER 02 FINAL UE"
EXAM_SUBJECT = "Majibu ya Maswali ya Mtihani"
EXAM_DATE = "09-08-2024"
PAGES = 24

# ----------------------------------------------------------------------
# MASWALI NA MAJIBU  (ongeza/edit hapa)
# ----------------------------------------------------------------------
ANSWERS = [
    (
        "SWALI 1",
        "Hapa ndipo jibu la Swali la 1 linaandikwa. "
        "Tafadhali niletee maswali kama maandishi ili niweze kuyajibu kwa usahihi.",
    ),
    (
        "SWALI 2",
        "Hapa ndipo jibu la Swali la 2 linaandikwa.",
    ),
    (
        "SWALI 3",
        "Hapa ndipo jibu la Swali la 3 linaandikwa.",
    ),
    (
        "SWALI 4",
        "Hapa ndipo jibu la Swali la 4 linaandikwa.",
    ),
    (
        "SWALI 5",
        "Hapa ndipo jibu la Swali la 5 linaandikwa.",
    ),
    (
        "SWALI 6",
        "Hapa ndipo jibu la Swali la 6 linaandikwa.",
    ),
    (
        "SWALI 7",
        "Hapa ndipo jibu la Swali la 7 linaandikwa.",
    ),
    (
        "SWALI 8",
        "Hapa ndipo jibu la Swali la 8 linaandikwa.",
    ),
    (
        "SWALI 9",
        "Hapa ndipo jibu la Swali la 9 linaandikwa.",
    ),
    (
        "SWALI 10",
        "Hapa ndipo jibu la Swali la 10 linaandikwa.",
    ),
]

# ----------------------------------------------------------------------
# RANGI (RGB)
# ----------------------------------------------------------------------
NAVY = (21, 45, 110)
BLUE = (37, 99, 235)
LIGHT_BLUE = (226, 235, 255)
DARK_GRAY = (55, 65, 81)
GRAY = (107, 114, 128)
WHITE = (255, 255, 255)


class AnswersPDF(FPDF):
    """PDF ya majibu yenye kichwa/mguu wa ukurasa na namba."""

    def header(self):
        if self.page_no() == 1:
            return  # hakuna header kwenye cover
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*NAVY)
        self.cell(0, 6, EXAM_TITLE + "  -  MAJIBU", align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*GRAY)
        self.cell(0, 6, f"Ukurasa {self.page_no()}", align="R")
        self.ln(3)
        self.set_draw_color(*BLUE)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_draw_color(*LIGHT_BLUE)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 6, "Majibu ya Mtihani wa Sem 02 Final UE", align="C")

    # ------------------------------------------------------------------
    def cover_page(self):
        self.add_page()
        # Ukanda wa rangi juu
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 95, "F")
        self.set_fill_color(*BLUE)
        self.rect(0, 95, 210, 4, "F")

        self.set_y(40)
        self.set_font("Helvetica", "B", 26)
        self.set_text_color(*WHITE)
        self.cell(0, 14, EXAM_TITLE, align="C")
        self.ln(16)
        self.set_font("Helvetica", "", 14)
        self.cell(0, 10, EXAM_SUBJECT, align="C")
        self.ln(8)
        self.set_font("Helvetica", "I", 11)
        self.cell(0, 8, "Tarehe ya Mtihani: " + EXAM_DATE, align="C")
        self.ln(30)

        # Sanduku la taarifa za mwanafunzi
        self.set_x(35)
        self.set_fill_color(*LIGHT_BLUE)
        self.rect(35, 150, 140, 55, "F")
        self.set_draw_color(*BLUE)
        self.set_line_width(0.5)
        self.rect(35, 150, 140, 55, "D")

        self.set_xy(42, 158)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*NAVY)
        self.cell(0, 8, "TAARIFA ZA MWANAFUNZI", align="C")
        self.ln(12)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*DARK_GRAY)
        self.set_x(42)
        self.cell(0, 8, "Jina:  ..............................................")
        self.ln(9)
        self.set_x(42)
        self.cell(0, 8, "Namba ya Mtihani:  .............................")
        self.ln(9)
        self.set_x(42)
        self.cell(0, 8, "Kozi / Programme:  .............................")
        self.ln(30)

        self.set_font("Helvetica", "I", 10)
        self.set_text_color(*GRAY)
        self.cell(0, 8, "Jumla ya kurasa za mtihani: " + str(PAGES), align="C")

    # ------------------------------------------------------------------
    def answers_page(self):
        self.add_page()
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*NAVY)
        self.cell(0, 10, "MAJIBU YA MASWALI", align="L")
        self.ln(12)

        for q_no, (swali, jibu) in enumerate(ANSWERS, start=1):
            # Chips ya namba ya swali
            self.set_fill_color(*BLUE)
            self.set_text_color(*WHITE)
            self.set_font("Helvetica", "B", 10)
            label = f" {q_no} "
            self.cell(10, 8, label, fill=True, align="C")
            self.set_text_color(*NAVY)
            self.set_font("Helvetica", "B", 12)
            self.cell(0, 8, "  " + swali)
            self.ln(9)

            # Jibu
            self.set_x(16)
            self.set_fill_color(*LIGHT_BLUE)
            self.set_draw_color(*LIGHT_BLUE)
            self.set_text_color(*DARK_GRAY)
            self.set_font("Helvetica", "", 11)
            self.multi_cell(180, 6.5, "JIBU: " + jibu, fill=True)
            self.ln(6)

        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*GRAY)
        self.cell(0, 6, "--- Mwisho wa Majibu ---", align="C")

    # ------------------------------------------------------------------
    def build(self, output_path):
        self.cover_page()
        self.answers_page()
        self.output(output_path)
        print(f"[OK] PDF imezalishwa: {output_path}")


if __name__ == "__main__":
    pdf = AnswersPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.build("Majibu_Sem02_Final_UE.pdf")
