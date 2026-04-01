import sys
import os

# 1. Klasör yollarını otomatik ayarla (Nerede olursan ol, dosyanı bulur)
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

from src.input_parser import InputParser
from src.analyzer import FrameAnalyzer
from src.report_generator import ReportGenerator

def main():
    input_file = os.path.join(base_dir, "data", "large_design.txt")
    report_file = os.path.join(base_dir, "data", "output_report.txt")
    
    # Klasör kontrolü (Eğer data klasörü yoksa otomatik oluşturur)
    data_folder = os.path.join(base_dir, "data")
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

    # ANALİZ SÜRECİ
    print("--- Analiz Basliyor ---")
    parser = InputParser(input_file)
    parser.parse_txt()
    
    xy, m_props, con, supports, loads = parser.get_structural_data()
    bw = parser.calculate_optimized_bandwidth()
    
    analyzer = FrameAnalyzer(xy, m_props, con, supports, loads, parser.member_loads, bw)
    analyzer.label_active_dof()
    
    print("Sistem cozuluyor...")
    displacements = analyzer.solve() 
    
    # SONUÇLARI YAZDIRMA
    print("Rapor olusturuluyor...")
    reporter = ReportGenerator(report_file)
    reporter.write_report(len(xy), len(con), displacements, input_file)
    
    print("\n" + "="*40)
    print(" BASARI: Analiz bitti ve rapor kaydedildi!")
    print(f" Raporun yeri: {report_file}")
    print("="*40)

if __name__ == "__main__":
    main()
