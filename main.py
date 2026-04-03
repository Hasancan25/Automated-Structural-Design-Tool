import matplotlib.pyplot as plt
import numpy as np

def plot_deflection(xy, con, displacements, scale_factor=500):
    """
    xy: Orijinal koordinatlar [[x, y], ...]
    con: Eleman baglantilari [[start, end, mat_id], ...]
    displacements: Cozulmus deplasmanlar [u1, v1, theta1, u2, v2, ...]
    scale_factor: Deplasmanlari gormek icin buyutme katsayisi
    """
    print(f"Grafik ciziliyor (Olcek: x{scale_factor})...")
    plt.figure(figsize=(10, 12))
    
    # 1. Orijinal Koordinatlari Hazırla
    xy = np.array(xy)
    
    # 2. Deforme Olmus Koordinatlari Hesapla
    # Her dugumun 3 serbestlik derecesi var (u, v, theta)
    num_node = len(xy)
    xy_def = np.zeros_like(xy)
    
    for i in range(num_node):
        # u (x yonu) ve v (y yonu) deplasmanlarini al (theta ihmal edilir)
        u = displacements[i*3]
        v = displacements[i*3 + 1]
        
        xy_def[i, 0] = xy[i, 0] + u * scale_factor
        xy_def[i, 1] = xy[i, 1] + v * scale_factor

    # 3. Elemanlari Ciz (Hiz icin sadece belirli bir kismi veya tumunu secebilirsin)
    # 200.000 elemani cizmek zaman alabilir, sadece kolon ve kirisleri donguyle ciziyoruz
    for elem in con:
        s_idx = int(elem[0]) - 1
        e_idx = int(elem[1]) - 1
        
        # Orijinal Yapi (Gri ve Kesikli)
        plt.plot([xy[s_idx, 0], xy[e_idx, 0]], 
                 [xy[s_idx, 1], xy[e_idx, 1]], 
                 'gray', linestyle='--', linewidth=0.5, alpha=0.3)
        
        # Deforme Olmus Yapi (Mavi ve Net)
        plt.plot([xy_def[s_idx, 0], xy_def[e_idx, 0]], 
                 [xy_def[s_idx, 1], xy_def[e_idx, 1]], 
                 'blue', linewidth=1)

    plt.title(f"Bina Deformasyon Grafigi (Olcek: x{scale_factor})")
    plt.xlabel("X Koordinati (m)")
    plt.ylabel("Y Koordinati (m)")
    plt.axis('equal')
    plt.grid(True, linestyle=':', alpha=0.6)
    
    print("Grafik kaydediliyor: data/deflection_plot.png")
    plt.savefig("data/deflection_plot.png", dpi=300)
    plt.show()
