import os
import time
import numpy as np
import matplotlib.pyplot as plt
from src.input_parser import InputParser
from src.analyzer import FrameAnalyzer

def plot_deflection(xy, con, displacements, scale_factor=1000):
    print(f"\nGrafik ciziliyor (Olcek: x{scale_factor})... Lutfen bekleyin.")
    plt.figure(figsize=(10, 12))
    
    xy = np.array(xy)
    # HATA BURADAYDI: num_node'u displacements uzunluğuna göre kısıtlıyoruz
    num_node = min(len(xy), len(displacements) // 3) 
    xy_def = np.zeros((num_node, 2))
    
    for i in range(num_node):
        # İndekslerin dışarı taşmaması için kontrol
        idx_x = i * 3
        idx_y = i * 3 + 1
        
        u = displacements[idx_x]
        v = displacements[idx_y]
        
        xy_def[i, 0] = xy[i, 0] + u * scale_factor
        xy_def[i, 1] = xy[i, 1] + v * scale_factor

    # Çizim kısmı aynı kalabilir...
    # (Buradan aşağısı eski kodunla aynı)

    # Hiz icin her 5 elemanda bir cizim yapiyoruz (100bin dugumde cok kasar)
    for i, elem in enumerate(con):
        if i % 5 == 0: 
            s_idx = int(elem[0]) - 1
            e_idx = int(elem[1]) - 1
            plt.plot([xy[s_idx, 0], xy[e_idx, 0]], [xy[s_idx, 1], xy[e_idx, 1]], 
                     'gray', linestyle='--', linewidth=0.3, alpha=0.2)
            plt.plot([xy_def[s_idx, 0], xy_def[e_idx, 0]], [xy_def[s_idx, 1], xy_def[e_idx, 1]], 
                     'blue', linewidth=0.8)

    plt.title(f"ODTU CE-4011: Deflected Shape (Scale: x{scale_factor})")
    plt.axis('equal')
    plt.grid(True, linestyle=':', alpha=0.5)
    print("Grafik kaydedildi: data/deflection_plot.png")
    plt.savefig("data/deflection_plot.png", dpi=300)
    plt.show()

# --- ANA PROGRAM ---
def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    input_file = os.path.join(data_dir, "large_design.txt")
    
    print("\n" + "="*50)
    print("   ODTU STRUCTURAL ANALYSIS ENGINE v2.0")
    print("="*50)

    if not os.path.exists(input_file):
        print(f"HATA: {input_file} bulunamadi! Once generate_data.py calismali.")
        return

    # 1. VERI OKUMA
    print("Adim 1: Veri seti yukleniyor...")
    parser = InputParser(input_file)
    parser.parse_txt()
    xy, m_props, con, supports, loads = parser.get_structural_data()

    # 2. ANALIZ
    print(f"Adim 2: Matrisler kuruluyor ve cozucu baslatiliyor...")
    analyzer = FrameAnalyzer(xy, m_props, con, supports, loads, [])
    displacements = analyzer.solve()

    # 3. SONUC
    max_disp = np.max(np.abs(displacements))
    print("\n" + "!"*40)
    print(f"ANALIZ TAMAMLANDI!")
    print(f"Maksimum Deplasman: {max_disp:.10e} m")
    print("!"*40)

    # 4. GÖRSELLEŞTİRME SORUSU
    secim = input("\nGrafigi gormek istiyor musun? (e/h): ")
    if secim.lower() == 'e':
        plot_deflection(xy, con, displacements)

if __name__ == "__main__":
    main()
