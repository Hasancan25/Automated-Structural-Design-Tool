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
                    node_id = int(float(s[0]))
                    restraints = [int(float(x)) for x in s[1:4]]
                    support_dict[node_id] = restraints
                except (ValueError, IndexError):
                    continue

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
        
        # Akıllı Malzeme Verisi Okuma (Unpack hatasını çözen kısım)
        prop_list = self.m_props[int(float(m_id))-1]
        if len(prop_list) >= 4:
            E, A, I = [float(x) for x in prop_list[1:4]]
        elif len(prop_list) == 3:
            E, A, I = [float(x) for x in prop_list]
        else:
            raise ValueError(f"Eleman {i_elem+1} malzeme verisi hatali!")

        x1, y1 = self.xy[int(float(s_n))-1]
        x2, y2 = self.xy[int(float(e_n))-1]
        L = np.sqrt((x2-x1)**2 + (y2-y1)**2)
        c = (x2-x1)/L
        s = (y2-y1)/L

        # Lokal matris kurulumu
        k_loc = np.array([
            [E*A/L, 0, 0, -E*A/L, 0, 0],
            [0, 12*E*I/L**3, 6*E*I/L**2, 0, -12*E*I/L**3, 6*E*I/L**2],
            [0, 6*E*I/L**2, 4*E*I/L, 0, -6*E*I/L**2, 2*E*I/L],
            [-E*A/L, 0, 0, E*A/L, 0, 0],
            [0, -12*E*I/L**3, -6*E*I/L**2, 0, 12*E*I/L**3, -6*E*I/L**2],
            [0, 6*E*I/L**2, 2*E*I/L, 0, 6*E*I/L**2, 4*E*I/L]
        ])

        # Dönüşüm matrisi
        T = np.array([
            [c, s, 0, 0, 0, 0],
            [-s, c, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0],
            [0, 0, 0, c, s, 0],
            [0, 0, 0, -s, c, 0],
            [0, 0, 0, 0, 0, 1]
        ])
        
        return T.T @ k_loc @ T

    def solve(self):
        num_eq = self.label_active_dof()
        print(f"Global Matris Kuruluyor ({num_eq} denklem)...")
        K = SparseStiffnessMatrix(num_eq)
        F = np.zeros(num_eq)

        # Nodal Yüklerin Montajı
        for l in self.nodal_loads:
            if len(l) >= 4:
                node_id = int(float(l[0]))
                for j in range(3):
                    eq = self.e_array[node_id-1][j]
                    if eq > 0:
                        F[eq-1] += float(l[j+1])

        # Elemanların Matrise Yerleştirilmesi
        print(f"{self.num_elem} eleman monte ediliyor...")
        for i in range(self.num_elem):
            k_g = self.get_k_global(i)
            s_n, e_n, _ = self.con[i]
            dofs = list(self.e_array[int(float(s_n))-1]) + list(self.e_array[int(float(e_n))-1])
            
            for r in range(6):
                for c in range(6):
                    if dofs[r] > 0 and dofs[c] > 0:
                        K.assemble(dofs[r], dofs[c], k_g[r][c])

        # Çözücüye Gönder
        solver = Solver()
        return solver.solve_sparse_system(K.matrix, F)
