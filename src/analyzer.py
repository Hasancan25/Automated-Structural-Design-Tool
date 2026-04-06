import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import cg
import time

class FrameAnalyzer:
    def __init__(self, xy, m_props, con, supports, loads, node_map):
        self.xy = xy
        self.m_props = m_props
        self.con = con
        self.supports = supports
        self.loads = loads
        self.node_map = node_map
        self.num_nodes = len(xy)
        self.num_dof = self.num_nodes * 3

    def solve(self):
        print(f"\n--- Analiz Basladi: {self.num_nodes} Dugum ---")
        K_global = lil_matrix((self.num_dof, self.num_dof))
        F_global = np.zeros(self.num_dof)

        print("Adim 1: Elemanlar monte ediliyor...")
        for elem in self.con:
            # Sütun kaymasına karşı koruma: [ID, N1, N2, Mat]
            if len(elem) >= 4: n1_id, n2_id, mat_id = int(elem[1]), int(elem[2]), int(elem[3])-1
            else: n1_id, n2_id, mat_id = int(elem[0]), int(elem[1]), int(elem[2])-1
            
            n1, n2 = self.node_map[n1_id], self.node_map[n2_id]
            E, A, I = self.m_props[mat_id if mat_id < len(self.m_props) else 0][:3]
            
            L = np.sqrt(np.sum((self.xy[n2] - self.xy[n1])**2))
            c, s = (self.xy[n2,0]-self.xy[n1,0])/L, (self.xy[n2,1]-self.xy[n1,1])/L
            
            # Lokal rijitlik matrisi
            k_local = np.array([[E*A/L,0,0,-E*A/L,0,0],[0,12*E*I/L**3,6*E*I/L**2,0,-12*E*I/L**3,6*E*I/L**2],[0,6*E*I/L**2,4*E*I/L,0,-6*E*I/L**2,2*E*I/L],[-E*A/L,0,0,E*A/L,0,0],[0,-12*E*I/L**3,-6*E*I/L**2,0,12*E*I/L**3,6*E*I/L**2],[0,6*E*I/L**2,2*E*I/L,0,-6*E*I/L**2,4*E*I/L]])
            T = np.array([[c,s,0,0,0,0],[-s,c,0,0,0,0],[0,0,1,0,0,0],[0,0,0,c,s,0],[0,0,0,-s,c,0],[0,0,0,0,0,1]])
            K_e = T.T @ k_local @ T
            
            dofs = [n1*3, n1*3+1, n1*3+2, n2*3, n2*3+1, n2*3+2]
            for r in range(6):
                for col in range(6): K_global[dofs[r], dofs[col]] += K_e[r, col]

# 2. Yükleri ve Mesnetleri Akıllıca As (KORUMALI)
        print("Adim 2: Yukler ve Mesnetler asiliyor...")
        applied_loads = 0
        for l in self.loads:
            try:
                # Sütunlarda kaç veri olursa olsun temizle
                vals = [x for x in l if not np.isnan(x)]
                if len(vals) < 3: continue
                
                # MÜHENDİS MANTIĞI: 
                # 1. Genelde en büyük sayı (10^6 gibi) 'Kuvvet'tir.
                # 2. 1, 2 veya 3 olan sayı 'Yön'dür (DOF).
                # 3. Geri kalan sayı 'Düğüm ID'dir.
                
                force = max(vals)
                dof_list = [v for v in vals if v in [1.0, 2.0, 3.0]]
                dof = int(dof_list[0]) if dof_list else 1
                
                # ID'yi bulmak için kalan sayıyı al
                remaining = [v for v in vals if v != force and v != dof]
                nid = int(remaining[0]) if remaining else int(vals[0])

                if nid in self.node_map:
                    idx = self.node_map[nid] * 3 + (dof - 1)
                    if 0 <= idx < self.num_dof:
                        F_global[idx] += force
                        applied_loads += 1
            except Exception as e:
                continue
                
        print(f"-> Basariyla asilan yuk: {applied_loads}")
        penalty = 1e20
        for s in self.supports:
            nid = int(s[0])
            if nid in self.node_map:
                idx = self.node_map[nid]*3 + (int(s[1])-1)
                K_global[idx, idx] += penalty
                F_global[idx] += s[2] * penalty

        print("\n--- Solver Baslatildi ---")
        K_sparse = K_global.tocsr()
        start = time.time()
        displacements, info = cg(K_sparse, F_global, rtol=1e-10, atol=1e-10, maxiter=50000)
        print(f"[BAŞARI] Cozum Suresi: {time.time() - start:.2f} saniye.")
        return displacements
