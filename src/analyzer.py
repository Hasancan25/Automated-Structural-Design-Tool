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
        self.node_map = node_map # ID -> İndeks haritası
        self.num_nodes = len(xy)
        self.num_dof = self.num_nodes * 3

    def solve(self):
        print(f"\n--- Analiz Basladi: {self.num_nodes} Dugum ---")
        K_global = lil_matrix((self.num_dof, self.num_dof))
        F_global = np.zeros(self.num_dof)

        # 1. Eleman Montajı
        print("Adim 1: Elemanlar monte ediliyor...")
        for elem in self.con:
            # Satırdaki ID'leri gerçek indekse çevir
            if len(elem) >= 4: n1_id, n2_id, mat_id = int(elem[1]), int(elem[2]), int(elem[3])-1
            else: n1_id, n2_id, mat_id = int(elem[0]), int(elem[1]), int(elem[2])-1
            
            n1, n2 = self.node_map[n1_id], self.node_map[n2_id]
            E, A, I = self.m_props[mat_id if mat_id < len(self.m_props) else 0][:3]
            
            x1, y1 = self.xy[n1]; x2, y2 = self.xy[n2]
            L = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            c, s = (x2-x1)/L, (y2-y1)/L
            
            # Lokal rijitlik ve transformasyon (Standart FEA)
            k_local = np.array([[E*A/L,0,0,-E*A/L,0,0],[0,12*E*I/L**3,6*E*I/L**2,0,-12*E*I/L**3,6*E*I/L**2],[0,6*E*I/L**2,4*E*I/L,0,6*E*I/L**2,2*E*I/L],[-E*A/L,0,0,E*A/L,0,0],[0,-12*E*I/L**3,-6*E*I/L**2,0,12*E*I/L**3,6*E*I/L**2],[0,6*E*I/L**2,2*E*I/L,0,-6*E*I/L**2,4*E*I/L]])
            T = np.array([[c,s,0,0,0,0],[-s,c,0,0,0,0],[0,0,1,0,0,0],[0,0,0,c,s,0],[0,0,0,-s,c,0],[0,0,0,0,0,1]])
            K_e = T.T @ k_local @ T
            
            dofs = [n1*3, n1*3+1, n1*3+2, n2*3, n2*3+1, n2*3+2]
            for r in range(6):
                for col in range(6): K_global[dofs[r], dofs[col]] += K_e[r, col]

        # 2. Yükleri ve Mesnetleri As (Hata Buradaydı!)
        print("Adim 2: Yukler ve Mesnetler asiliyor...")
        applied_loads = 0
        for l in self.loads:
            nid, dof, force = int(l[0]), int(l[1]), float(l[2])
            if nid in self.node_map:
                F_global[self.node_map[nid]*3 + (dof-1)] += force
                applied_loads += 1
        print(f"-> Basariyla asilan yuk: {applied_loads}")

        penalty = 1e20
        for s in self.supports:
            nid, dof, val = int(s[0]), int(s[1]), float(s[2])
            if nid in self.node_map:
                idx = self.node_map[nid]*3 + (dof-1)
                K_global[idx, idx] += penalty
                F_global[idx] += val * penalty

        # 3. Çözücü
        print("\n--- Solver Baslatildi ---")
        K_sparse = K_global.tocsr()
        start = time.time()
        displacements, info = cg(K_sparse, F_global, rtol=1e-10, atol=1e-10, maxiter=50000)
        print(f"Bitti! Sure: {time.time()-start:.2f} saniye.")
        return displacements
