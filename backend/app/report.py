from fpdf import FPDF
from datetime import datetime


def generate_pdf(title: str, content: str, output_path: str = "report.pdf"):
    """
    Gera um relatório PDF simples com título e conteúdo.
    """
    pdf = FPDF()
    pdf.add_page()

    # Título
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")

    pdf.ln(10)

    # Corpo do texto
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, content)

    pdf.ln(10)

    # Data de geração
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="R")

    pdf.output(output_path)
    return output_path