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
        
        # 1. Global Rijitlik Matrisi ve Yük Vektörü Hazırlığı
        K_global = lil_matrix((self.num_dof, self.num_dof))
        F_global = np.zeros(self.num_dof)

        # OFFSET HESABI (Hataya Neden Olan Kısım Burada Tanımlandı)
        # Dosyadaki en küçük ID'yi buluyoruz (Genelde 1'dir)
        ids = []
        if len(self.loads) > 0: ids.extend([int(float(l[0])) for l in self.loads])
        if len(self.supports) > 0: ids.extend([int(float(s[0])) for s in self.supports])
        min_id = min(ids) if ids else 1
        print(f"-> Sistem Offseti Belirlendi: {min_id}")

        # 2. Eleman Montajı (Assembly)
        print("Adim 1: Elemanlar monte ediliyor...")
        for i, elem in enumerate(self.con):
            n1, n2, mat_id = int(elem[0])-1, int(elem[1])-1, int(elem[2])-1
            E, A, I = self.m_props[mat_id][:3]
            
            x1, y1 = self.xy[n1]
            x2, y2 = self.xy[n2]
            L = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            c, s = (x2-x1)/L, (y2-y1)/L
            
            # Lokal Rijitlik Matrisi
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

        # 3. Yükleri Eşleştirme
        print("Adim 2: Yukler sisteme dahil ediliyor...")
        load_count = 0
        for l_entry in self.loads:
            raw_id, dof, force = l_entry[:3]
            node_idx = int(float(raw_id)) - min_id
            
            if 0 <= node_idx < self.num_nodes:
                idx = node_idx * 3 + (int(dof) - 1)
                F_global[idx] += force
                load_count += 1
        print(f"-> Basariyla asilan yuk sayisi: {load_count}")

        # 4. Mesnetler (Penalty Method)
        print("Adim 3: Mesnetler isleniyor...")
        penalty = 1e20
        for s_entry in self.supports:
            raw_id, dof, val = s_entry[:3]
            node_idx = int(float(raw_id)) - min_id
            if 0 <= node_idx < self.num_nodes:
                idx = node_idx * 3 + (int(dof) - 1)
                K_global[idx, idx] += penalty
                F_global[idx] += val * penalty

        # 5. Çözücü (Solver)
        print("\n--- Iterative Solver (CG) Baslatildi ---")
        K_sparse = K_global.tocsr()
        start_time = time.time()
        
        # rtol ve maxiter isimleri SciPy'ın güncel sürümüne göredir
        displacements, info = cg(K_sparse, F_global, rtol=1e-10, atol=1e-10, maxiter=50000)
        
        print(f"Cozum Suresi: {time.time() - start_time:.2f} saniye.")
        if info == 0:
            print("[BAŞARI] Çözücü tam yakınsadı!")
        else:
            print("[UYARI] Çözücü tam yakınsamadı, sonuçlar yaklaşık olabilir.")

        return displacements
