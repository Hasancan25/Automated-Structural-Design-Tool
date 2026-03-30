import math
from src.matrix_lib import BandedSymmetricMatrix
from src.solver import Solver

class FrameAnalyzer:
    """
    PURPOSE: Executes structural analysis for frames with dynamic node/member counts.
    Handles nodal loads and equivalent member loads (UDL, Point Loads).
    """
    def __init__(self, xy, m_props, connectivity, supports, nodal_loads, member_loads, half_bw):
        self.xy = xy
        self.m_props = m_props
        self.connectivity = connectivity
        self.supports = supports
        self.nodal_loads = nodal_loads
        self.member_loads = member_loads # New: List of loads on members
        self.half_bw = half_bw
        
        self.num_node = len(xy)
        self.num_elem = len(connectivity)
        self.e_array = []
        self.num_eq = 0

    def label_active_dof(self):
        """Step 1-8: Assigns global equation numbers based on supports."""
        self.e_array = [[0, 0, 0] for _ in range(self.num_node)]
        count = 0
        for i in range(self.num_node):
            for j in range(3):
                if self.supports[i][j] == 0:
                    count += 1
                    self.e_array[i][j] = count
        self.num_eq = count
        return self.num_eq

    def get_element_matrices(self, elem_id):
        """Step 9-10: Generates k_local and transforms to k_global."""
        s_node, e_node, mat_id = self.connectivity[elem_id]
        x1, y1 = self.xy[s_node - 1]
        x2, y2 = self.xy[e_node - 1]
        
        L = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        c, s = (x2-x1)/L, (y2-y1)/L
        A, I, E = self.m_props[mat_id - 1]

        # Standard 2D Frame Stiffness Matrix (Local)
        k_loc = [[0.0]*6 for _ in range(6)]
        # ... (Stiffness terms: EA/L, 12EI/L^3 etc. go here) ...
        
        # Transformation k_glob = T_transp * k_loc * T
        # ... (Transformation logic) ...
        return k_glob, L, c, s

    def assemble_and_solve(self):
        """Step 11-12: Assemblies K and F, then solves for displacements."""
        K = BandedSymmetricMatrix(self.num_eq, self.half_bw)
        F = [0.0] * self.num_eq

        # A. Add Nodal Loads to F
        for i in range(self.num_node):
            for j in range(3):
                eq = self.e_array[i][j]
                if eq > 0: F[eq-1] += self.nodal_loads[i][j]

        # B. Process Elements (Stiffness + Member Loads)
        for i in range(self.num_elem):
            k_glob, L, c, s = self.get_element_matrices(i)
            # 1. Assemble Stiffness into K
            # ... (Standard assembly logic using e_array) ...

            # 2. Handle Member Loads (UDL/Point)
            # Eğer bu eleman üzerinde yük varsa, FEF hesapla ve F'den çıkar
            fef_glob = self.calculate_fef_global(i, L, c, s)
            self.assemble_fef_to_global_f(F, i, fef_glob)

        # C. Solve
        solver = Solver()
        D = solver.solve_banded_system(K, F)
        return D

    def calculate_fef_global(self, elem_id, L, c, s):
        """Calculates Fixed End Forces and transforms them to global."""
        fef_loc = [0.0] * 6
        # Member loads listesini gez, bu elemana ait olanları bul ve fef_loc'a ekle
        # Örn: Vertical UDL için fef_loc[1] = wL/2, fef_loc[2] = wL^2/12 ...
        # Sonra fef_glob = T_transp * fef_loc
        return fef_glob
