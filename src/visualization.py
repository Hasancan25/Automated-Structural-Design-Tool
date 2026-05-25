import matplotlib.pyplot as plt
import numpy as np

class StructuralVisualizer:
    """Analiz sonuçlarını grafiksel olarak işleyen ve görselleştiren OOP modülü."""
    
    @staticmethod
    def plot_deformed_shape(nodes, elements, scale=25.0):
        """Çerçevenin orijinal hali ile P-Delta deformasyon şeklini üst üste çizer."""
        plt.figure(figsize=(10, 8))
        
        # Düğüm koordinat haritasını hızlı okuma için sözlüğe alıyoruz
        node_dict = {n.id: n for n in nodes}
        
        # 1. Döngü: Çerçevenin Çıplak/Orijinal Halini Gri Çiz (Undeformed)
        for elem in elements:
            ni = node_dict[elem.node_i_id if hasattr(elem, 'node_i_id') else elem.node_i.id]
            nj = node_dict[elem.node_j_id if hasattr(elem, 'node_j_id') else elem.node_j.id]
            
            plt.plot([ni.x, nj.x], [ni.y, nj.y], color='#A0A0A0', linestyle='--', linewidth=1.0)
            
        # 2. Döngü: Deforme Olmuş Şekli Çiz (Deformed Shape)
        for elem in elements:
            ni = node_dict[elem.node_i_id if hasattr(elem, 'node_i_id') else elem.node_i.id]
            nj = node_dict[elem.node_j_id if hasattr(elem, 'node_j_id') else elem.node_j.id]
            
            # Düğümlerin deplasmanlarını al (u: X deplasmanı, v: Y deplasmanı)
            ni_u = getattr(ni, 'u', 0.0)
            ni_v = getattr(ni, 'v', 0.0)
            nj_u = getattr(nj, 'u', 0.0)
            nj_v = getattr(nj, 'v', 0.0)
            
            # Ölçeklendirilmiş yeni koordinatlar
            xi_new = ni.x + ni_u * scale
            yi_new = ni.y + ni_v * scale
            xj_new = nj.x + nj_u * scale
            yj_new = nj.y + nj_v * scale
            
            # Eleman tipine göre renk ataması (Kolon mavi, Kiriş turuncu)
            color = '#1f77b4' if abs(ni.x - nj.x) < 1e-3 else '#ff7f0e'
            plt.plot([xi_new, xj_new], [yi_new, yj_new], color=color, linewidth=2.0)
            
        plt.title(f"Yapisal Deformasyon Sekli (Deformed Shape) - Olcek: {scale}x")
        plt.xlabel("X Koordinati (m)")
        plt.ylabel("Y Koordinati (m)")
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.axis('equal')
        plt.show()

    @staticmethod
    def plot_capacity_heatmap(nodes, elements, envelope_results):
        """AISC 360 D/C oranlarına göre elemanları renk kodlu kapasite haritası olarak çizer."""
        plt.figure(figsize=(10, 8))
        node_dict = {n.id: n for n in nodes}
        
        for elem in elements:
            ni = node_dict[elem.node_i_id if hasattr(elem, 'node_i_id') else elem.node_i.id]
            nj = node_dict[elem.node_j_id if hasattr(elem, 'node_j_id') else elem.node_j.id]
            
            # Elemanın zarftaki (envelope) maksimum D/C oranını bul
            dc_i = envelope_results.get(elem.id, {}).get('i', {}).get('dc', 0.0)
            dc_j = envelope_results.get(elem.id, {}).get('j', {}).get('dc', 0.0)
            max_dc = max(dc_i, dc_j)
            
            # OOP Renk Süzgeci: Güvenliyse Yeşil, Sınır Aşmıssa Kıpkırmızı!
            if max_dc > 1.0:
                color = '#D62728' # Canlı Kırmızı
                linewidth = 3.0
            elif max_dc > 0.85:
                color = '#BCBD22' # Uyarı Sarısı
                linewidth = 2.5
            else:
                color = '#2CA02C' # Güvenli Yeşil
                linewidth = 2.0
                
            plt.plot([ni.x, nj.x], [ni.y, nj.y], color=color, linewidth=linewidth)
            
        plt.title("AISC 360-16 Kesit Mukavemet Kapasite Haritasi (D/C Heatmap)")
        plt.xlabel("X Koordinati (m)")
        plt.ylabel("Y Koordinati (m)")
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.axis('equal')
        plt.show()
