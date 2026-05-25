from abc import ABC, abstractmethod
import numpy as np

class StructuralEffect(ABC):
    @abstractmethod
    def apply(self, solver):
        pass

class MemberLoadEffect(StructuralEffect):
    def apply(self, solver):
        ndof = solver.ndof
        for elem in solver.elements:
            if abs(elem.udl) > 1e-9:
                # 1. Lokal FEA'yı al (Solver'daki release-aware metodu kullanır)
                fea_loc = solver._get_element_udl_fea(elem)
                
                # 2. Global dönüşüm ve F_global güncelleme
                T = solver.get_transformation_matrix(elem)
                fea_glob = T.T @ fea_loc
                
                idx_i = solver.node_map[elem.node_i.id] * ndof
                idx_j = solver.node_map[elem.node_j.id] * ndof
                indices = list(range(idx_i, idx_i + ndof)) + list(range(idx_j, idx_j + ndof))
                
                solver.F_global[indices] -= fea_glob

                # 3. DİNAMİK BİRİKTİRME: Bu yükü eleman hafızasına kazı
                if not hasattr(elem, 'total_fea_loc'):
                    elem.total_fea_loc = np.zeros(2 * ndof)
                elem.total_fea_loc += fea_loc

class SupportSettlement(StructuralEffect):
    def __init__(self, node_id, dof, value):
        self.node_id = node_id
        self.dof = dof 
        self.value = value

    def apply(self, solver):
        # Mesnet çökmesi için Penalty Method
        idx = solver.node_map[self.node_id] * solver.ndof + self.dof
        solver.K_global[idx, idx] += solver.penalty
        solver.F_global[idx] += self.value * solver.penalty

class ThermalEffect(StructuralEffect):
    def __init__(self, alpha, delta_t_avg, delta_t_grad=0, h=1.0):
        self.alpha = alpha           
        self.delta_t_avg = delta_t_avg 
        self.delta_t_grad = delta_t_grad 
        self.h = h                   

    def apply(self, solver):
        ndof = solver.ndof
        for elem in solver.elements:
            # P_th = E * A * alpha * delta_T_avg[cite: 3]
            axial_f = elem.material.E * elem.material.A * self.alpha * self.delta_t_avg
            # M_th = E * I * alpha * delta_T_grad / h[cite: 3]
            bending_m = elem.material.E * elem.material.I * self.alpha * self.delta_t_grad / self.h
            
            # [Ax_i, Vy_i, M_i, Ax_j, Vy_j, M_j]
            fea_loc = np.array([-axial_f, 0, bending_m, axial_f, 0, -bending_m])
            
            T = solver.get_transformation_matrix(elem)
            fea_glob = T.T @ fea_loc
            
            idx_i = solver.node_map[elem.node_i.id] * ndof
            idx_j = solver.node_map[elem.node_j.id] * ndof
            indices = list(range(idx_i, idx_i + ndof)) + list(range(idx_j, idx_j + ndof))
            
            solver.F_global[indices] -= fea_glob
            
            # DİNAMİK BİRİKTİRME: Üst üste binen termal etkileri kaydet[cite: 3]
            if not hasattr(elem, 'total_fea_loc'):
                elem.total_fea_loc = np.zeros(2 * ndof)
            elem.total_fea_loc += fea_loc
