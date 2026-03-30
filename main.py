import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.input_parser import InputParser
from src.analyzer import FrameAnalyzer
from src.report_generator import ReportGenerator

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, "data", "test_design.txt")
    parser = InputParser(input_file)
    parser.parse_txt()
    
    # Verileri alıyoruz
    xy, m_props, con, supports, loads = parser.get_structural_data()
    bw = parser.calculate_optimized_bandwidth()
    
    analyzer = FrameAnalyzer(xy, m_props, con, supports, loads, parser.member_loads, bw)
    analyzer.label_active_dof()
    
    # ÇÖZÜMÜ BURADA YAPIYORUZ
    displacements = analyzer.solve() 
    
    # 2. Raporu Çözümden SONRA oluşturuyoruz
    report_file = "data/output_report.txt"
    reporter = ReportGenerator(report_file)
    reporter.write_report(len(xy), len(con), displacements, input_file)
    
    print("Analiz bitti ve rapor oluşturuldu!")

if __name__ == "__main__":
    main()
