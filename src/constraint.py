from abc import ABC, abstractmethod

class Constraint(ABC):
    @abstractmethod
    def apply(self, K, F, node_map, penalty_value, ndof): # <--- ndof eklendi
        pass

class AxialRigidConstraint(Constraint):
    def __init__(self, node_i_id, node_j_id, direction='x'):
        self.node_i = node_i_id
        self.node_j = node_j_id
        self.direction = direction

    def apply(self, K, F, node_map, penalty_value, ndof): # <--- ndof eklendi
        idx_i = node_map[self.node_i]
        idx_j = node_map[self.node_j]
        
        offset = 0 if self.direction == 'x' else 1
        
        # Artık ndof neyse (2 veya 3) ona göre indis hesaplıyor
        dof_i = idx_i * ndof + offset
        dof_j = idx_j * ndof + offset
        
        K[dof_i, dof_i] += penalty_value
        K[dof_j, dof_j] += penalty_value
        K[dof_i, dof_j] -= penalty_value
        K[dof_j, dof_i] -= penalty_value
