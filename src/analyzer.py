import math
from src.matrix_lib import BandedSymmetricMatrix
from src.solver import Solver

class FrameAnalyzer:
    """
    PURPOSE: Executes the 13-step Matrix Displacement Method for 2D Frames.
    This version is generic and handles any number of nodes, members, and loads.
    """
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
        self.num_eq = 0
        self.e_array = []

    def label_active_dof(self):
        """Steps 1-8: Assign global equation numbers to active (free) DOFs."""
        self.e_array = [[0, 0, 0] for _ in range(self.num_node)]
        count = 0
        for i in range(self.num_node):
            for j in range(3): # ux, uy, rz
                if self.supports[i][j] == 0: # If it's a free DOF
                    count += 1
                    self.e_array[i][j] = count
        self.num_eq = count
        return self.num_eq

    def get_k_global(self, elem_id):
        """Steps 9-10: Formulates k_local and transforms it to k_global (6x6)."""
        s_node, e_node, mat_id = self.con[elem_id]
        x1, y1 = self.xy[s_node - 1]
        x2, y2 = self.xy[e_node - 1]
        
        L = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        c = (x2-x1)/L # cos
        s = (y2-y1)/L # sin
        A, I, E = self.m_props[mat_id - 1]

        # 1. Local Stiffness Matrix [k_local] (6x6)
        k_loc = [[0.0]*6 for _ in range(6)]
        # Axial terms
        k_loc[0][0] = k_loc[3][3] = E*A/L
        k_loc[0][3] = k_loc[3][0] = -E*A/L
        # Bending & Shear terms
        k_loc[1][1] = k_loc[4][4] = 12*E*I/(L**3)
        k_loc[1][4] = k_loc[4][1] = -12*E*I/(L**3)
        k_loc[1][2] = k_loc[2][1] = k_loc[1][5] = k_loc[5][1] = 6*E*I/(L**2)
        k_loc[4][2] = k_loc[2][4] = k_loc[4][5] = k_loc[5][4] = -6*E*I/(L**2)
        k_loc[2][2] = k_loc[5][5] = 4*E*I/L
        k_loc[2][5] = k_loc[5][2] = 2*E*I/L

        # 2. Rotation Matrix [T] (6x6)
        T = [[0.0]*6 for _ in range(6)]
        T[0][0] = T[1][1] = T[3][3] = T[4][4] = c
        T[0][1] = T[3][4] = s
        T[1][0] = T[4][3] = -s
        T[2][2] = T[5][5] = 1.0

        # 3. Global Transformation: k_glob = T_transpose * k_loc * T
        # (This is the standard manual matrix multiplication for efficiency)
        k_glob = self._multiply_matrices_T_transpose_k_T(T, k_loc)
        
        return k_glob, L, c, s

    def _multiply_matrices_T_transpose_k_T(self, T, k):
        """Helper to compute k_glob = T^T * k * T for 6x6 matrices."""
        # result = k * T
        temp = [[0.0]*6 for _ in range(6)]
        for i in range(6):
            for j in range(6):
                for k_idx in range(6):
                    temp[i][j] += k[i][k_idx] * T[k_idx][j]
        
        # result = T^T * temp
        final = [[0.0]*6 for _ in range(6)]
        for i in range(6):
            for j in range(6):
                for k_idx in range(6):
                    final[i][j] += T[k_idx][i] * temp[k_idx][j]
        return final

    def solve(self):
        """Step 11-13: Assembly, Solving and Output."""
        # Initialize Banded Matrix and Load Vector
        K = BandedSymmetricMatrix(self.num_eq, self.half_bw)
        F = [0.0] * self.num_eq

        # A. Assembly of Load Vector (Nodal Loads)
        for i in range(self.num_node):
            for j in range(3):
                eq = self.e_array[i][j]
                if eq > 0:
                    F[eq-1] += self.nodal_loads[i][j]

        # B. Assembly of Global Stiffness Matrix K
        for i in range(self.num_elem):
            k_glob, _, _, _ = self.get_k_global(i)
            s_node, e_node, _ = self.con[i]
            
            # Eleman düğümlerinin global DOF numaraları (E-array)
            indices = self.e_array[s_node-1] + self.e_array[e_node-1]
            
            for row in range(6):
                for col in range(6):
                    eq_row = indices[row]
                    eq_col = indices[col]
                    if eq_row > 0 and eq_col > 0:
                        K.assemble(eq_row, eq_col, k_glob[row][col])

        # C. Solver
        solver = Solver()
        displacements = solver.solve_banded_system(K, F)
        return displacements
