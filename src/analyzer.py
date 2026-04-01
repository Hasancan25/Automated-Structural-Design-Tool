import numpy as np
from src.matrix_lib import SparseStiffnessMatrix
from src.solver import Solver

class FrameAnalyzer:
    # ... (init kısımları aynı kalabilir) ...

    def solve(self):
        num_eq = self.label_active_dof()
        K = SparseStiffnessMatrix(num_eq)
        F = np.zeros(num_eq)

        # Nodal Yükler
        for i in range(self.num_node):
            for j in range(3):
                eq = self.e_array[i][j]
                if eq > 0: F[eq-1] += self.nodal_loads[i][j]

        # Eleman Matrislerinin Montajı
        print("Global Matris Kuruluyor (Mega Assembly)...")
        for i in range(self.num_elem):
            k_g = self.get_k_global(i)
            s_n, e_n, _ = self.con[i]
            idx = self.e_array[s_n-1] + self.e_array[e_n-1]
            
            for r in range(6):
                for c in range(6):
                    if idx[r] > 0 and idx[c] > 0:
                        K.assemble(idx[r], idx[c], k_g[r][c])

        return Solver().solve_sparse_system(K.matrix, F)
