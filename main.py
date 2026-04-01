import os
import time
from src.input_parser import InputParser
from src.analyzer import FrameAnalyzer

def main():
    # Dosya yollarını belirle
    input_file = os.path.join("data", "large_design.txt")
    output_file = os.path.join("data", "output_report.txt")
    
    if not os.path.exists(input_file):
        print(f"HATA: {input_file} bulunamadı! Önce generate_data.py çalıştırılmalı.")
        return

    print("--- ODTU Structural Analysis Tool (Sparse Engine) ---")
    start_total = time.time()

    # 1. DOSYAYI OKU (Parser)
    print("Adım 1: Veri seti okunuyor...")
    parser = InputParser(input_file)
    parser.parse_txt()
    
    # Yeni InputParser fonksiyonumuzu çağırıyoruz
    xy, m_props, con, supports, loads = parser.get_structural_data()

    # 2. ANALİZİ BAŞLAT (Analyzer)
    # Artık 'bw' (bandwidth) göndermemize gerek yok!
    analyzer = FrameAnalyzer(xy, m_props, con, supports, loads, [])
    
    print(f"Adım 2: Analiz motoru hazırlandı. ({len(xy)} Düğüm, {len(con)} Eleman)")
    displacements = analyzer.solve()

    # 3. RAPOR OLUŞTUR (Report)
    print("Adım 5: Rapor yazdırılıyor...")
    with open(output_file, "w") as f:
        f.write("="*60 + "\n")
        f.write("        STRUCTURAL ANALYSIS REPORT - 2D FRAME\n")
        f.write(f"        Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")
        f.write(f"Source Input File: {os.path.abspath(input_file)}\n")
        f.write(f"Nodes Detected: {len(xy)}\n")
        f.write(f"Elements Detected: {len(con)}\n")
        f.write("-" * 30 + "\n\n")
        f.write("NODAL DISPLACEMENTS\n")
        f.write(f"{'DOF No':<10} | {'Displacement (m or rad)':<25}\n")
        f.write("-" * 40 + "\n")
        
        for i, disp in enumerate(displacements):
            f.write(f"{i+1:<10} | {disp: .8e}\n")

    end_total = time.time()
    print(f"\n[BASARI] Analiz ve raporlama {end_total - start_total:.2f} saniyede tamamlandi.")
    print(f"Sonuclar: {output_file}")

if __name__ == "__main__":
    main()
