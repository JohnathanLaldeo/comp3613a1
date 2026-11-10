"""Build docs/a2-report.pdf from docs/a2-report.md using the project's PDF renderer.

Usage: python docs/build_a2_pdf.py
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import report_pdf as rp  # noqa: E402

TITLE = "COMP 3613 Assignment 2"


class A2PDF(rp.ReportPDF):
    def header(self) -> None:
        if self.page_no() == 1:
            self.set_fill_color(*rp.NAVY)
            self.rect(0, 0, self.w, 36, "F")
            self.set_fill_color(*rp.GOLD)
            self.rect(0, 36, self.w, 2.2, "F")
            self.set_text_color(255, 255, 255)
            self.set_font("Body", "B", 20)
            self.set_xy(self.l_margin, 9)
            self.cell(self.epw, 10, TITLE)
            self.set_font("Body", "", 11)
            self.set_xy(self.l_margin, 20)
            self.cell(self.epw, 8, "Testing and REST API report")
            self.set_text_color(0, 0, 0)
            self.set_y(48)
            return
        self.set_y(10)
        self.set_font("Body", "", 9)
        self.set_text_color(*rp.NAVY)
        self.cell(self.epw, 6, TITLE, new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)
        self.set_draw_color(*rp.GOLD)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_text_color(0, 0, 0)
        self.set_y(self.t_margin)


def main() -> None:
    src = ROOT / "docs" / "a2-report.md"
    dest = ROOT / "docs" / "a2-report.pdf"
    rp.ReportPDF = A2PDF
    pdf = rp._new_pdf(False)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        html = rp._markdown_to_html(src.read_text(encoding="utf-8"), src.parent, Path(tmp))
        rp._write_report_html(pdf, html)
    pdf.output(dest)
    print(f"PDF: {dest} ({pdf.page_no()} pages)")


if __name__ == "__main__":
    main()
