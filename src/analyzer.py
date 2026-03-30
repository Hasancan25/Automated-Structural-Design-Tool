import math
from src.matrix_lib import BandedSymmetricMatrix
from src.solver import Solver

class FrameAnalyzer:
    def __init__(self, xy, m_props, con, supports, nodal_loads, member_loads, half_bw):
        self.xy = xy
        self.m_props = m_props
        self.con = con
        self.supports = supports
        self.nodal_loads = nodal_loads
        self.member_loads = member_loads
        self.half_bw = half_bw
        self.num_node = len(xy)
        self.num_elem = len(con)
        self.e_array = []

    def label_active_dof(self):
        self.e_array = [[0, 0, 0] for _ in range(self.num_node)]
        count = 0
        for i in range(self.num_node):
            for j in range(3):
                if self.supports[i][j] == 0:
                    count += 1
                    self.e_array[i][j] = count
        return count

    def get_k_global(self, elem_id):
        s_node, e_node, mat_id = self.con[elem_id]
        x1, y1 = self.xy[s_node - 1]
        x2, y2 = self.xy[e_node - 1]
        L = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        c, s = (x2-x1)/L, (y2-y1)/L
        A, I, E = self.m_props[mat_id - 1]
        k_loc = [[0.0]*6 for _ in range(6)]
        k_loc[0][0] = k_loc[3][3] = E*A/L
        k_loc[0][3] = k_loc[3][0] = -E*A/L
        k_loc[1][1] = k_loc[4][4] = 12*E*I/(L**3)
        k_loc[1][4] = k_loc[4][1] = -12*E*I/(L**3)
        k_loc[1][2] = k_loc[2][1] = k_loc[1][5] = k_loc[5][1] = 6*E*I/(L**2)
        k_loc[4][2] = k_loc[2][4] = k_loc[4][5] = k_loc[5][4] = -6*E*I/(L**2)
        k_loc[2][2] = k_loc[5][5] = 4*E*I/L
        k_loc[2][5] = k_loc[5][2] = 2*E*I/L
        T = [[0.0]*6 for _ in range(6)]
        T[0][0] = T[1][1] = T[3][3] = T[4][4] = c
        T[0][1] = T[3][4] = s
        T[1][0] = T[4][3] = -s
        T[2][2] = T[5][5] = 1.0
        k_glob = self._transform(T, k_loc)
        return k_glob

    def _transform(self, T, k):
        temp = [[0.0]*6 for _ in range(6)]
        for i in range(6):
            for j in range(6):
                for m in range(6): temp[i][j] += k[i][m] * T[m][j]
        final = [[0.0]*6 for _ in range(6)]
        for i in range(6):
            for j in range(6):
                for m in range(6): final[i][j] += T[m][i] * temp[m][j]
        return final

    def solve(self):
        num_eq = self.label_active_dof()
        K = BandedSymmetricMatrix(num_eq, self.half_bw)
        F = [0.0] * num_eq
        for i in range(self.num_node):
            for j in range(3):
                eq = self.e_array[i][j]
                if eq > 0: F[eq-1] += self.nodal_loads[i][j]
        for i in range(self.num_elem):
            k_g = self.get_k_global(i)
            s_n, e_n, _ = self.con[i]
            idx = self.e_array[s_n-1] + self.e_array[e_n-1]
            for r in range(6):
                for c in range(6):
                    if idx[r] > 0 and idx[c] > 0: K.assemble(idx[r], idx[c], k_g[r][c])
        return Solver().solve_banded_system(K, F)
