from src.report_generator import ReportGenerator  # En üste ekle

# ... main() fonksiyonu içinde en sona ekle ...
# 6. Rapor Oluşturma
report_file = "data/output_report.txt"
reporter = ReportGenerator(report_file)
reporter.write_report(len(xy), len(con), displacements, input_file)
