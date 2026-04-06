import os
import time
import numpy as np
import matplotlib.pyplot as plt
from src.input_parser import InputParser
from src.analyzer import FrameAnalyzer

# --- GÖRSELLEŞTİRME FONKSİYONU ---
def plot_deflection(xy, con, displacements, node_map, scale_factor=100):
    """
    xy: Orijinal koordinatlar
    con: Eleman baglantıları
    displacements: Cozucu sonucu (u, v, theta)
    node_map: Dosyadaki ID -> Matristeki Sira haritasi
    """
    print(f"\nGrafik ciziliyor (Olcek: x{scale_factor})... Lutfen bekleyin.")
    plt.figure(figsize=(10, 12))
    
    num_node = len(xy)
    xy_def = np.zeros_like(xy)
    
    # 1. Deforme olmus koordinatları hesapla
    for i in range(num_node):
        idx_x, idx_y = i * 3, i * 3 + 1
        if idx_y < len(displacements):
            # i zaten matris sirasi oldugu icin dogrudan kullaniyoruz
            xy_def[i, 0] = xy[i, 0] + displacements[idx_x] * scale_factor
            xy_def[i, 1] = xy[i, 1] + displacements[idx_y] * scale_factor
        else:
            xy_def[i, :] = xy[i, :]

    # 2. Elemanları ciz
    print("Elemanlar haritalaniyor...")
    drawn_count = 0
    for i, elem in enumerate(con):
        # Hiz icin her 10 elemanda bir cizim yap (Rapor icin yeterli netlik saglar)
        if i % 10 == 0:
            try:
                # Sütun kaymasına karsı koruma (ID, N1, N2...)
                if len(elem) >= 4:
                    n1_id, n2_id = int(elem[1]), int(elem[2])
                else:
                    n1_id, n2_id = int(elem[0]), int(elem[1])
                
                # KRITIK: Dosyadaki ID'yi node_map ile matris sirasina cevir
                if n1_id in node_map and n2_id in node_map:
                    s_idx = node_map[n1_id]
                    e_idx = node_map[n2_id]
                    
                    # Orijinal Yapı (Gri Kesikli)
                    plt.plot([xy[s_idx, 0], xy[e_idx, 0]], [xy[s_idx, 1], xy[e_idx, 1]], 
                             'gray', linestyle='--', linewidth=0.2, alpha=0.1)
                    # Deforme Yapı (Mavi)
                    plt.plot([xy_def[s_idx, 0], xy_def[e_idx, 0]], [xy_def[s_idx, 1], xy_def[e_idx, 1]], 
                             'blue', linewidth=0.7)
                    drawn_count += 1
            except:
                continue

    plt.title(f"ODTU CE-4011: Deflected Shape (Scale: x{scale_factor})")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.axis('equal')
    plt.grid(True, linestyle=':', alpha=0.3)
    
    output_path = "data/deflection_plot.png"
    print(f"Grafik kaydediliyor: {output_path}")
    plt.savefig(output_path, dpi=300)
    plt.show()

# --- ANA PROGRAM ---
def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, "data", "large_design.txt")
    
    print("\n" + "="*50)
    print("    ODTU STRUCTURAL ANALYSIS ENGINE v2.0")
    print("="*50)

    if not os.path.exists(input_file):
        print(f"HATA: {input_file} bulunamadi! Once generate_data.py calismali.")
        return

    # 1. VERI OKUMA
    print("Adim 1: Veri seti yukleniyor...")
    parser = InputParser(input_file)
    parser.parse_txt()
    # node_map artik hayati bir önem tasiyor
    xy, m_props, con, supports, loads, node_map = parser.get_structural_data()

    # 2. ANALIZ
    print(f"Adim 2: Matrisler kuruluyor ve cozucu baslatiliyor...")
    # Analyzer artik node_map'i taniyacak sekilde guncellenmis olmali
    analyzer = FrameAnalyzer(xy, m_props, con, supports, loads, node_map)
    displacements = analyzer.solve()

    # 3. SONUC
    # Max deplasmanı 'u' ve 'v' bilesenlerine gore bul (theta'yı dahil etme)
    # Sadece 0. ve 1. DOF'lar (X ve Y deplasmanlari)
    uv_disp = []
    for i in range(len(xy)):
        uv_disp.append(displacements[i*3])     # u
        uv_disp.append(displacements[i*3 + 1]) # v
    
    max_disp = np.max(np.abs(uv_disp))
    
    print("\n" + "!"*40)
    print(f"ANALIZ TAMAMLANDI!")
    print(f"Maksimum Deplasman: {max_disp:.6f} m")
    if max_disp > 100:
        print("UYARI: Deplasman cok buyuk! Malzeme rijitligini (E) kontrol et.")
    print("!"*40)

    # 4. GÖRSELLEŞTİRME
    secim = input("\nGrafigi gormek istiyor musun? (e/h): ")
    if secim.lower() == 'e':
        # Eger deplasman cok buyukse (1713m gibi), olcegi kucultelim:
        scale = 1000 if max_disp < 1 else 1
        plot_deflection(xy, con, displacements, node_map, scale_factor=scale)

if __name__ == "__main__":
    main()
