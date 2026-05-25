import numpy as np

class Material:
    def __init__(self, material_id, name, E, A, I, alpha=0.0, h=0.0, Fy=250000.0):
        self.id = material_id
        self.name = name
        self.E, self.A, self.I = float(E), float(A), float(I)
        self.alpha, self.h = float(alpha), float(h)
        self.Fy = float(Fy)  # AISC 360-16 LRFD Kontrolleri için Akma Gerilmesi (kN/m2 - Varsayılan: 250 MPa)

class Node:
    def __init__(self, node_id, x, y, ndof=3, nodal_loads=None):
        self.id = int(node_id)
        self.x, self.y = float(x), float(y)
        self.ndof = ndof
        self.displacements = np.zeros(ndof)
        self.reactions = np.zeros(ndof)
        self.nodal_loads = np.zeros(ndof)
        
        # KRİTİK: Yük okuma mantığı 'fx', 'fy', 'm' ve 'dof' destekler hale getirildi
        if nodal_loads:
            for L in nodal_loads:
                # 1. Yöntem: Sözlük içinde 'fx', 'fy', 'm' anahtarları varsa
                if 'fx' in L: self.nodal_loads[0] += float(L.get('fx', 0.0))
                if 'fy' in L: self.nodal_loads[1] += float(L.get('fy', 0.0))
                if 'm' in L and ndof > 2: self.nodal_loads[2] += float(L.get('m', 0.0))
                
                # 2. Yöntem: 'dof' ve 'value' anahtarları varsa
                if 'dof' in L:
                    dof_idx = int(L['dof'])
                    if 0 <= dof_idx < ndof:
                        self.nodal_loads[dof_idx] += float(L.get('value', 0.0))

        # Aliasing
        self.loads = self.load = self.forces = self.force = self.P = self.F = self.nodal_loads

class Element:
    def __init__(self, elem_id, node_i, node_j, material, elem_type="frame", udl=0.0, release_i=False, release_j=False):
        self.id = int(elem_id)
        self.node_i, self.node_j = node_i, node_j
        self.material = material
        self.type = elem_type
        self.releases = [release_i, release_j]
        self.udl = float(udl)
        self.member_loads = []
        self.dT_uniform = self.dT_gradient = 0.0
        
        # --- DESIGNCHECKER ENTEGRASYON KATMANI ---
        # Kullanıcı doğrudan input.json ile başlarsa (User Manual - Path 2) kodun patlamaması için güvenli varsayılanlar
        self.section_name = "Unknown"
        self.section_d = 0.3   # Varsayılan kesit yüksekliği (m)
        self.section_Z = 1e-3  # Varsayılan plastik mukavemet momenti (m3)
        
        # GÜVENLİK GÜNCELLEMESİ: Material None ise çökme
        if material:
            self.h = material.h if material.h > 0 else 0.1
        else:
            self.h = 0.1

    def get_length(self):
        return np.sqrt((self.node_j.x - self.node_i.x)**2 + (self.node_j.y - self.node_i.y)**2)

    def get_angle(self):
        return np.arctan2(self.node_j.y - self.node_i.y, self.node_j.x - self.node_i.x)
