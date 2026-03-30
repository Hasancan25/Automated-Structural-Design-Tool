import math

def get_element_matrices(self, elem_id):
    # 1. Geometriyi al
    s_node, e_node, mat_id = self.connectivity[elem_id]
    x1, y1 = self.xy[s_node - 1]
    x2, y2 = self.xy[e_node - 1]
    
    L = math.sqrt((x2-x1)**2 + (y2-y1)**2)
    c, s = (x2-x1)/L, (y2-y1)/L
    A, I, E = self.m_props[mat_id - 1]

    # 2. Local Stiffness Matrix [k] (6x6)
    k_loc = [[0.0]*6 for _ in range(6)]
    # Eksenel
    k_loc[0][0] = k_loc[3][3] = E*A/L
    k_loc[0][3] = k_loc[3][0] = -E*A/L
    # Eğilme ve Kesme
    k_loc[1][1] = k_loc[4][4] = 12*E*I/(L**3)
    k_loc[1][4] = k_loc[4][1] = -12*E*I/(L**3)
    k_loc[1][2] = k_loc[2][1] = k_loc[1][5] = k_loc[5][1] = 6*E*I/(L**2)
    k_loc[4][2] = k_loc[2][4] = k_loc[4][5] = k_loc[5][4] = -6*E*I/(L**2)
    k_loc[2][2] = k_loc[5][5] = 4*E*I/L
    k_loc[2][5] = k_loc[5][2] = 2*E*I/L
    
    # 3. Global Transformation k_glob = T_transp * k_loc * T
    # (Bu kısmı bir önceki ödevde yazdığın gibi T matrisiyle çarparak yapabilirsin)
    return k_glob, L, c, s
