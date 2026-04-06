import os
import time
import numpy as np
import matplotlib.pyplot as plt
from src.input_parser import InputParser
from src.analyzer import FrameAnalyzer

def plot_deflection(xy, con, displacements, node_map, scale_factor=1000):
    print(f"\nGrafik ciziliyor (Olcek: x{scale_factor})... Lutfen bekleyin.")
    plt.figure(figsize=(10, 12))
    
    num_node = len(xy) 
    xy_def = np.zeros_like(xy)
    
    for i in range(num_node):
        idx_x, idx_y = i * 3, i * 3 + 1
        if idx_y < len(displacements):
            xy_def[i, 0] = xy[i, 0] + displacements[idx_x] * scale_factor
            xy_def[i, 1] = xy[i, 1] + displacements[idx_y] * scale_factor
        else:
            xy_def[i, :] = xy[i, :]

    print("Elemanlar haritalaniyor...")
    for i, elem in enumerate(con):
        if i % 10 == 0: # Hiz icin her 10 elemanda bir cizim
            if len(elem) >= 4: n1_id, n2_id = int(elem[1]), int(elem[2])
            else: n1_id, n2_id = int(elem[0]), int(elem[1])
            
            s_idx, e_idx = node_map[n1_id], node_map[n2_id]
            plt.plot([xy[s_idx, 0], xy[e_idx, 0]], [xy[s_idx, 1], xy[e_idx, 1]], 
                     'gray', linestyle='--', linewidth=0.2, alpha=0.2)
            plt.plot([xy_def[s_idx, 0], xy_def[e_idx, 0]], [xy_def[s_idx, 1], xy_def[e_idx, 1]], 
                     'blue', linewidth=0.7)

    plt.title(f"ODTU CE-4011: Deflected Shape (Scale: x{scale_factor})")
    plt.xlabel("X (m)"); plt.ylabel("Y (m)"); plt.axis('equal'); plt.grid(True, alpha=0.3)
    plt.savefig("data/deflection_plot.png", dpi=300)
    plt.show()

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, "data", "large_design.txt")
    
    print("\n" + "="*50)
    print("    ODTU STRUCTURAL ANALYSIS ENGINE v2.0")
    print("="*50)

    if not os.path.exists(input_file):
        print(f"HATA: {input_file} bulunamadi!")
        return

    print("Adim 1: Veri seti yukleniyor...")
    parser = InputParser(input_file)
    parser.parse_txt()
    # node_map artik parser'dan geliyor:
    xy, m_props, con, supports, loads, node_map = parser.get_structural_data()

    print(f"Adim 2: Matrisler kuruluyor ve cozucu baslatiliyor...")
    analyzer = FrameAnalyzer(xy, m_props, con, supports, loads, node_map)
    displacements = analyzer.solve()

    max_disp = np.max(np.abs(displacements))
    print("\n" + "!"*40)
    print(f"ANALIZ TAMAMLANDI!")
    print(f"Maksimum Deplasman: {max_disp:.10e} m")
    print("!"*40)

    secim = input("\nGrafigi gormek istiyor musun? (e/h): ")
    if secim.lower() == 'e':
        plot_deflection(xy, con, displacements, node_map)

if __name__ == "__main__":
    main()
