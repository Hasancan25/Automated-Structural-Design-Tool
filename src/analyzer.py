import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import cg
import time

class FrameAnalyzer:
    def __init__(self, xy, m_props, con, supports, loads, design_params):
        self.xy = np.array(xy)
        self.m_props = np.array(m_props)  # [E, A, I]
        self.con = np.array(con)          # [node1, node2, mat_id]
        self.supports = supports          # [[node_id, dof, val], ...]
        self.loads = loads                # [[node_id, dof, force], ...]
        self.num_nodes = len(xy)
        self.num_dof = self.num_nodes * 3

    def solve(self):
        print(f"\n--- Analiz Basladi: {self.num_nodes} Dugum, {len(self.con)} Eleman ---")
        
        # 1. Global Rijitlik Matrisini Hazirla (Seyrek Matris Formatinda)
        # 100 bin dugum icin 'lil_matrix' ile insa edip 'csr'ye cevirmek en hızlısıdır.
        K_global = lil_matrix((self.num_dof, self.num_dof))
        F_global = np.zeros(self.num_dof)

        # 2. Eleman Rijitlik Matrislerini Monte Et (Assembly)
        print("Adim 3: Elemanlar sisteme monte ediliyor...")
        for i, elem in enumerate(self.con):
            n1, n2, mat_id = int(elem[0])-1, int(elem[1])-1, int(elem[2])-1
            E, A, I = self.m_props[mat_id][:3]
            
            # Koordinatlar ve Boy
            x1, y1 = self.xy[n1]
            x2, y2 = self.xy[n2]
            L = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            c = (x2-x1)/L # cos
            s = (y2-y1)/L # sin
            
            # Lokal Rijitlik Matrisi (Beam Element)
            # k = [EA/L, 12EI/L^3, 6EI/L^2, ...]
            k_local = np.array([
                [E*A/L, 0, 0, -E*A/L, 0, 0],
                [0, 12*E*I/L**3, 6*E*I/L**2, 0, -12*E*I/L**3, 6*E*I/L**2],
                [0, 6*E*I/L**2, 4*E*I/L, 0, -6*E*I/L**2, 2*E*I/L],
                [-E*A/L, 0, 0, E*A/L, 0, 0],
                [0, -12*E*I/L**3, -6*E*I/L**2, 0, 12*E*I/L**3, 6*E*I/L**2],
                [0, 6*E*I/L**2, 2*E*I/L, 0, -6*E*I/L**2, 4*E*I/L]
            ])
            
            # Transformasyon Matrisi (T)
            T = np.array([
                [c, s, 0, 0, 0, 0],
                [-s, c, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0],
                [0, 0, 0, c, s, 0],
                [0, 0, 0, -s, c, 0],
                [0, 0, 0, 0, 0, 1]
            ])
            
            # Global Eleman Matrisi: Ke = T.T * k_local * T
            K_e = T.T @ k_local @ T
            
            # Global Matrise Yerlestirme
            dofs = [n1*3, n1*3+1, n1*3+2, n2*3, n2*3+1, n2*3+2]
            for r in range(6):
                for col in range(6):
                    K_global[dofs[r], dofs[col]] += K_e[r, col]
        
# 3. Yukleri Uygula (ESLESTIRMELI VE GUVENLI)
        print("Adim 5: Yukler sisteme dahil ediliyor...")
        
        # Dosyadaki ID'ler ile Python indekslerini baglamak icin bir harita (map) kuruyoruz
        node_map = {int(self.xy[i, 0] if self.xy.shape[1] > 2 else i+1): i for i in range(self.num_nodes)}
        # Eger koordinat dosyasinda ID yoksa, varsayilan olarak 1'den baslayan sirayi kullanir:
        if not node_map:
            node_map = {i+1: i for i in range(self.num_nodes)}

        applied_load_count = 0
        for load_entry in self.loads:
            try:
                node_id, dof, force = load_entry[:3]
                target_node_id = int(float(node_id))
                
                if target_node_id in node_map:
                    node_idx = node_map[target_node_id]
                    idx = node_idx * 3 + (int(dof) - 1)
                    F_global[idx] += force
                    applied_load_count += 1
            except:
                continue

        print(f"[BILGI] Toplam {applied_load_count} adet yuk sisteme basariyla asildi.")
            
# 4. Sinir Sartlarini Uygula (Penalty Method)
        print("Adim 6: Sinir sartlari (Mesnetler) isleniyor...")
        penalty = 1e18
        for support_entry in self.supports:
            # SADECE ILK 3 DEGERI AL: Kaç veri olursa olsun hata almayız
            node_id, dof, val = support_entry[:3]
            
            # İndeksi hesapla
            idx = (int(node_id)-1)*3 + (int(dof)-1)
            
            # GÜVENLİK KONTROLÜ
            if 0 <= idx < len(F_global):
                K_global[idx, idx] += penalty
                F_global[idx] += val * penalty
            else:
                # Eğer geçersiz ID gelirse (100001 gibi) uyar ama çökme
                print(f"[UYARI] Gecersiz Mesnet Dugum ID: {node_id}. Atlandi.")

# 5. Cozucu (Solver) - GÜNCEL VERSİYON
        print("\n--- Iterative Solver (CG) Baslatildi ---")
        K_sparse = K_global.tocsr() # Isleme hizli girmek icin CSR formatina gec
        
        start_time = time.time()
        
        # SciPy 1.11+ sürümleri için 'tol' yerine 'rtol' kullanılır.
        # 'atol' ise mutlak hata payını belirler, ikisini de eklemek en güvenlisidir.
        displacements, info = cg(
            K_sparse, 
            F_global, 
            rtol=1e-10,       # 'tol' olan yer 'rtol' yapıldı
            atol=1e-10,       # Mutlak tolerans da eklendi
            maxiter=50000    # 200 katlı bina için inatçı mod
        )
        
        end_time = time.time()

        if info == 0:
            print(f"[BAŞARI] Çözücü yakinsadi! Süre: {end_time - start_time:.2f} saniye.")
        else:
            print(f"[UYARI] Çözücü {max_iter} adimda tam yakinsayamadi, sonuc yaklasik olabilir.")

        return displacements
