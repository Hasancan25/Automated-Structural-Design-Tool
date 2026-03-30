from src.input_parser import InputParser
from src.analyzer import FrameAnalyzer

def main():
    # 1. Veriyi Oku
    parser = InputParser('data/test_design.txt')
    parser.parse_txt()
    xy, m_props, con, supports, loads = parser.get_structural_data()
    bw = parser.calculate_optimized_bandwidth()

    # 2. Analizi Başlat
    # (Burada analyzer nesnesini kurup assemble_and_solve() diyeceğiz)
    print("Sistem başarıyla modellendi. Çözüm başlatılıyor...")

if __name__ == "__main__":
    main()
