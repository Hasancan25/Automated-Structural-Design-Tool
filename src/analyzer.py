import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import cg
import time

class FrameAnalyzer:
    def __init__(self, xy, m_props, con, supports, loads, design_params):
        self.xy = np.array(xy)
        self.m_props = np.array(m_props)
        self.con = np.array(con)
        self.supports = supports
        self.loads = loads
        self.num_nodes = len(xy)
        self.num_dof = self.num_nodes * 3

    def solve(self):
        print(f"\n--- Analiz Basladi: {self.num_nodes} Dugum, {len(self.con)} Eleman ---")
        
        K_global = lil_matrix((self.num_dof, self.num_dof))
        F_global = np.zeros(self.num_dof)

        # 1. Eleman Montajı
        print("Adim 1: Elemanlar monte ediliyor...")
        for elem in self.con:
            n1, n2, mat_id = int(elem[0])-1, int(elem[1])-1, int(elem[2])-1
            E, A, I = self.m_props[mat_id][:3]
            
            x1, y1 = self.xy[n1]
            x2, y2 = self.xy[n2]
            L = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            c, s = (x2-x1)/L, (y2-y1)/L
            
            k_local = np.array([
                [E*A/L, 0, 0, -E*A/L, 0, 0],
                [0, 12*E*I/L**3, 6*E*I/L**2, 0, -12*E*I/L**3, 6*E*I/L**2],
                [0, 6*E*I/L**2, 4*E*I/L, 0, -6*E*I/L**2, 2*E*I/L],
                [-E*A/L, 0, 0, E*A/L, 0, 0],
                [0, -12*E*I/L**3, -6*E*I/L**2, 0, 12*E*I/L**3, 6*E*I/L**2],
                [0, 6*E*I/L**2, 2*E*I/L, 0, -6*E*I/L**2, 4*E*I/L]
            ])
            T = np.array([[c,s,0,0,0,0],[-s,c,0,0,0,0],[0,0,1,0,0,0],[0,0,0,c,s,0],[0,0,0,-s,c,0],[0,0,0,0,0,1]])
            K_e = T.T @ k_local @ T
            
            dofs = [n1*3, n1*3+1, n1*3+2, n2*3, n2*3+1, n2*3+2]
            for r in range(6):
                for col in range(6):
                    K_global[dofs[r], dofs[col]] += K_e[r, col]

# 2. Yükleri Eşleştirme (KORUMALI VERSİYON)
        print("Adim 2: Yukler sisteme dahil ediliyor...")
        load_count = 0
        
        for i, l_entry in enumerate(self.loads):
            try:
                # Veriyi al (node_id, dof, force)
                raw_id, dof, force = l_entry[:3]
                node_id = int(float(raw_id))
                
                # İndeks hesabı: (Düğüm No - 1) * 3 + (DOF - 1)
                idx = (node_id - 1) * 3 + (int(dof) - 1)
                
                # GÜVENLİK KONTROLÜ: İndeks sınırlar içindeyse işle
                if 0 <= idx < self.num_dof:
                    F_global[idx] += force
                    load_count += 1
                else:
                    # Sadece ilk 3 hatayı terminale yazalım ki ekran dolmasın
                    if load_count < 3:
                        print(f"[UYARI] Satir {i}: ID {node_id} gecersiz! (Index: {idx}) Bu yuk atlandi.")
            except Exception as e:
                continue
        
        print(f"-> Toplam {load_count} adet yuk sisteme basariyla asildi.")

        # 3. Mesnetler (Penalty Method)
        print("Adim 3: Mesnetler isleniyor...")
        penalty = 1e20
        for s_entry in self.supports:
            raw_id, dof, val = s_entry[:3]
            node_idx = int(raw_id) - min_id
            if 0 <= node_idx < self.num_nodes:
                idx = node_idx * 3 + (int(dof) - 1)
                K_global[idx, idx] += penalty
                F_global[idx] += val * penalty

        # 4. Çözücü
        print("\n--- Iterative Solver (CG) Baslatildi ---")
        K_sparse = K_global.tocsr()
        start_time = time.time()
        
        displacements, info = cg(K_sparse, F_global, rtol=1e-10, atol=1e-10, maxiter=50000)
        
        print(f"Cozum Suresi: {time.time() - start_time:.2f} saniye.")
        return displacements
