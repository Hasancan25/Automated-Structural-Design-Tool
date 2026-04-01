import numpy as np
from src.matrix_lib import SparseStiffnessMatrix
from src.solver import Solver

class FrameAnalyzer:
    def __init__(self, xy, m_props, con, supports, nodal_loads, member_loads, bw=None):
        self.xy = np.array(xy)
        self.m_props = m_props
        self.con = con
        self.supports = supports
        self.nodal_loads = nodal_loads
        self.member_loads = member_loads
        
        self.num_node = len(xy)
        self.num_elem = len(con)
        self.e_array = np.zeros((self.num_node, 3), dtype=int)

    def label_active_dof(self):
        """Mesnetleri ve serbestlik derecelerini güvenli bir şekilde etiketler."""
        count = 0
        support_dict = {}
        for s in self.supports:
            if len(s) >= 4:
                try:
                    node_id = int(float(str(s[0]).replace(',', '').strip()))
                    restraints = [int(float(str(x).replace(',', '').strip())) for x in s[1:4]]
                    support_dict[node_id] = restraints
                except: continue

        for i in range(1, self.num_node + 1):
            if i in support_dict:
                restraints = support_dict[i]
                for j in range(3):
                    if j < len(restraints) and restraints[j] == 0:
                        count += 1
                        self.e_array[i-1][j] = count
            else:
                for j in range(3):
                    count += 1
                    self.e_array[i-1][j] = count
        return count

    def get_k_global(self, i_elem):
        """Eleman rijitlik matrisini E, A, I kontrolü yaparak hesaplar."""
        s_n, e_n, m_id = self.con[i_elem]
        m_id_clean = int(float(str(m_id).replace(',', '').strip()))
        prop_list = self.m_props[m_id_clean - 1]
        
        if len(prop_list) >= 4:
            E, A, I = [float(str(x).replace(',', '').strip()) for x in prop_list[1:4]]
        else:
            E, A, I = [float(str(x).replace(',', '').strip()) for x in prop_list]

        s_idx = int(float(str(s_n).replace(',', '').strip())) - 1
        e_idx = int(float(str(e_n).replace(',', '').strip())) - 1
        x1, y1 = self.xy[s_idx]
        x2, y2 = self.xy[e_idx]
        L = np.sqrt((x2-x1)**2 + (y2-y1)**2)
        c, s = (x2-x1)/L, (y2-y1)/L

        k_loc = np.array([
            [E*A/L, 0, 0, -E*A/L, 0, 0],
            [0, 12*E*I/L**3, 6*E*I/L**2, 0, -12*E*I/L**3, 6*E*I/L**2],
            [0, 6*E*I/L**2, 4*E*I/L, 0, -6*E*I/L**2, 2*E*I/L],
            [-E*A/L, 0, 0, E*A/L, 0, 0],
            [0, -12*E*I/L**3, -6*E*I/L**2, 0, 12*E*I/L**3, -6*E*I/L**2],
            [0, 6*E*I/L**2, 2*E*I/L, 0, 6*E*I/L**2, 4*E*I/L]
        ])
        T = np.array([[c,s,0,0,0,0],[-s,c,0,0,0,0],[0,0,1,0,0,0],[0,0,0,c,s,0],[0,0,0,-s,c,0],[0,0,0,0,0,1]])
        return T.T @ k_loc @ T

    def solve(self):
        print("Adım 1: Serbestlik dereceleri etiketleniyor...")
        num_eq = self.label_active_dof()
        
        print(f"Adım 2: Global Matris ve Yuk Vektoru Hazirlaniyor ({num_eq} denklem)...")
        K_obj = SparseStiffnessMatrix(num_eq)
        F = np.zeros(num_eq)

        # Yük Montajı
        for l in self.nodal_loads:
            if len(l) >= 2:
                try:
                    n_id = int(float(str(l[0]).replace(',', '').strip()))
                    for j in range(len(l)-1):
                        if j < 3:
                            val = float(str(l[j+1]).replace(',', '').strip())
                            eq = self.e_array[n_id-1][j]
                            if eq > 0: F[eq-1] += val
                except: continue

        # Eleman Montajı (COO Hızıyla)
        print(f"Adım 3: {self.num_elem} eleman monte ediliyor...")
        for i in range(self.num_elem):
            k_g = self.get_k_global(i)
            s_idx = int(float(str(self.con[i][0]).replace(',', '').strip())) - 1
            e_idx = int(float(str(self.con[i][1]).replace(',', '').strip())) - 1
            dofs = list(self.e_array[s_idx]) + list(self.e_array[e_idx])
            for r in range(6):
                for c in range(6):
                    if dofs[r] > 0 and dofs[c] > 0:
                        K_obj.assemble(dofs[r], dofs[c], k_g[r][c])

        # Matrisi Finalize et ve Çözücüye Gönder
        K_sparse = K_obj.finalize()
        print("Adım 4: Sistem cozucuye gonderiliyor...")
        solver = Solver()
        return solver.solve_sparse_system(K_sparse, F)
