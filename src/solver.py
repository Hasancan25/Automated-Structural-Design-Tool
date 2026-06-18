import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve
from scipy.linalg import eigh  # Modal Analiz (Eigenvalue) çözücüsü için eklendi

class StructuralSolver:
    def __init__(self, nodes, elements, boundary_conditions, nodal_loads=None, ndof=3, penalty=1e12):
        self.nodes = nodes
        self.elements = elements
        self.bc = boundary_conditions
        self.nodal_loads = nodal_loads if nodal_loads is not None else []
        self.ndof = ndof
        self.penalty = penalty
        self.num_dof = len(self.nodes) * self.ndof
        self.node_map = {node.id: i for i, node in enumerate(self.nodes)}
        
        self.K_global = lil_matrix((self.num_dof, self.num_dof))
        self.F_global = np.zeros(self.num_dof)

    def get_transformation_matrix(self, elem):
        L = elem.get_length()
        cos = (elem.node_j.x - elem.node_i.x) / L
        sin = (elem.node_j.y - elem.node_i.y) / L
        R = np.array([[cos, sin, 0], [-sin, cos, 0], [0, 0, 1]])
        T = np.zeros((6, 6))
        T[0:3, 0:3] = R; T[3:6, 3:6] = R
        return T

    def get_local_k(self, elem):
        L = elem.get_length()
        E, A, I = elem.material.E, elem.material.A, elem.material.I
        # Stiffness katsayıları
        a, b, c, d, e = E*A/L, 12*E*I/L**3, 6*E*I/L**2, 4*E*I/L, 2*E*I/L
        return np.array([
            [ a,  0,  0, -a,  0,  0],
            [ 0,  b,  c,  0, -b,  c],
            [ 0,  c,  d,  0, -c,  e],
            [ -a, 0,  0,  a,  0,  0],
            [ 0, -b, -c,  0,  b, -c],
            [ 0,  c,  e,  0, -c,  d]
        ])

    def _get_element_udl_fea(self, elem):
        """Standard Fixed-End Forces for a beam under UDL"""
        L = elem.get_length()
        w = float(getattr(elem, 'udl', 0.0))
        return np.array([0.0, -w*L/2.0, -w*L**2/12.0, 0.0, -w*L/2.0, w*L**2/12.0])

    def assemble(self):
        self.K_global = lil_matrix((self.num_dof, self.num_dof))
        self.F_global = np.zeros(self.num_dof)

        for elem in self.elements:
            T = self.get_transformation_matrix(elem)
            k_glob = T.T @ self.get_local_k(elem) @ T
            
            i_idx = self.node_map[elem.node_i.id] * 3
            j_idx = self.node_map[elem.node_j.id] * 3
            dofs = list(range(i_idx, i_idx+3)) + list(range(j_idx, j_idx+3))
            
            for i, r_idx in enumerate(dofs):
                for j, c_idx in enumerate(dofs):
                    self.K_global[r_idx, c_idx] += k_glob[i, j]
            
            w = float(getattr(elem, 'udl', 0.0))
            if abs(w) > 1e-9:
                fef_loc = self._get_element_udl_fea(elem)
                self.F_global[dofs] -= T.T @ fef_loc
                elem.total_fea_loc = fef_loc
            else:
                elem.total_fea_loc = np.zeros(6)

        for load in self.nodal_loads:
            nid = load.get("node_id")
            if nid in self.node_map:
                base = self.node_map[nid] * 3
                self.F_global[base + 0] += float(load.get("fx", 0))
                self.F_global[base + 1] += float(load.get("fy", 0))
                self.F_global[base + 2] += float(load.get("mz", 0))

    def solve(self):
        self.assemble()
        
        # --- KRİTİK DÜZELTME BURADA ---
        for bc_data in self.bc:
            # IOHandler veriyi tuple olarak (n_id, dof, val) şeklinde gönderdiği için:
            n_id, dof, val = bc_data 
            
            if n_id in self.node_map:
                idx = self.node_map[n_id] * 3 + int(dof)
                self.K_global[idx, idx] += self.penalty
                self.F_global[idx] += float(val) * self.penalty
        
        self.displacements = spsolve(self.K_global.tocsr(), self.F_global)
        self.calculate_internal_forces()
        return self.displacements

    def calculate_internal_forces(self):
        for node in self.nodes:
            idx = self.node_map[node.id] * 3
            node.u, node.v, node.rz = self.displacements[idx : idx + 3]

        for elem in self.elements:
            i_idx = self.node_map[elem.node_i.id] * 3
            j_idx = self.node_map[elem.node_j.id] * 3
            u_glob = np.concatenate([self.displacements[i_idx:i_idx+3], self.displacements[j_idx:j_idx+3]])
            T = self.get_transformation_matrix(elem)
            f_loc = (self.get_local_k(elem) @ (T @ u_glob)) + getattr(elem, 'total_fea_loc', np.zeros(6))
            
            elem.internal_forces = {
                'Ni': f_loc[0], 'Vi': f_loc[1], 'Mi': f_loc[2],
                'Nj': f_loc[3], 'Vj': f_loc[4], 'Mj': f_loc[5]
            }

    # =========================================================================
    # KÜMÜLATİF EKLEMELER: P-DELTA GEOMETRİK RİJİTLİK VE İTERATİF ÇÖZÜCÜ
    # =========================================================================

    def get_local_kg(self, elem, N):
        """
        Elemanın yerel (local) geometrik rijitlik matrisini (Kg) hesaplar.
        N: Eksenel Kuvvet (Tension: +, Compression: -)
        """
        L = elem.get_length()
        kg = np.zeros((6, 6))
        
        if abs(N) < 1e-8:
            return kg
            
        factor = N / L
        
        # Standart Euler-Bernoulli Çerçeve Elemanı Geometrik Rijitlik Terimleri
        kg[1, 1] = 6.0 / 5.0
        kg[1, 2] = L / 10.0
        kg[1, 4] = -6.0 / 5.0
        kg[1, 5] = L / 10.0
        
        kg[2, 1] = L / 10.0
        kg[2, 2] = (2.0 * L**2) / 15.0
        kg[2, 4] = -L / 10.0
        kg[2, 5] = -(L**2) / 30.0
        
        kg[4, 1] = -6.0 / 5.0
        kg[4, 2] = -L / 10.0
        kg[4, 4] = 6.0 / 5.0
        kg[4, 5] = -L / 10.0
        
        kg[5, 1] = L / 10.0
        kg[5, 2] = -(L**2) / 30.0
        kg[5, 4] = -L / 10.0
        kg[5, 5] = (2.0 * L**2) / 15.0
        
        return kg * factor

    def solve_pdelta(self, max_iter=20, tolerance=1e-5):
        """
        Sistemi P-Delta (İkinci Derece) etkilerini hesaba katarak iteratif olarak çözer.
        """
        print("\n" + "-"*50)
        print("[+] PROGRESSIVE P-DELTA SOLVER BAŞLATILDI".center(50, " "))
        print("-"*50)
        
        u_old = self.solve().copy()
        
        for iteration in range(1, max_iter + 1):
            self.assemble()
            
            for elem in self.elements:
                N = elem.internal_forces['Nj']
                
                T = self.get_transformation_matrix(elem)
                kg_local = self.get_local_kg(elem, N)
                kg_global = T.T @ kg_local @ T
                
                i_idx = self.node_map[elem.node_i.id] * 3
                j_idx = self.node_map[elem.node_j.id] * 3
                dofs = list(range(i_idx, i_idx+3)) + list(range(j_idx, j_idx+3))
                
                for i, r_idx in enumerate(dofs):
                    for j, c_idx in enumerate(dofs):
                        self.K_global[r_idx, c_idx] += kg_global[i, j]
            
            for bc_data in self.bc:
                n_id, dof, val = bc_data
                if n_id in self.node_map:
                    idx = self.node_map[n_id] * 3 + int(dof)
                    self.K_global[idx, idx] += self.penalty
                    self.F_global[idx] += float(val) * self.penalty
            
            self.displacements = spsolve(self.K_global.tocsr(), self.F_global)
            self.calculate_internal_forces()
            u_new = self.displacements
            
            norm_diff = np.linalg.norm(u_new - u_old)
            norm_ref = np.linalg.norm(u_new)
            error = norm_diff / (norm_ref + 1e-12)
            
            print(f" -> Iterasyon {iteration:02d}: Hata Oranı = {error:.6e}")
            
            if error < tolerance:
                print(f"\n[✓] P-Delta Analizi {iteration}. iterasyonda başarıyla yakınsadı!")
                print("-"*50)
                return self.displacements
                
            u_old = u_new.copy()
            
        print("\n[!] UYARI: P-Delta maksimum iterasyona ulaştı ama hedeflenen toleransa yakınsayamadı!")
        print("-"*50)
        return self.displacements

    # =========================================================================
    # YENİ EKLENTİ: DİNAMİK MODAL (DOĞAL FREKANS) ANALİZ MOTORU
    # =========================================================================

    def run_modal_analysis(self, num_modes=3):
        print("\n[+] Yapısal Dinamik (Modal) Analiz Başlatılıyor...")
        
        # 1. Kütle Matrisini oluştur
        M_global = np.eye(self.num_dof) * 1e-3 
        
        for elem in self.elements:
            # main.py'de atadığımız mass değerini direkt çek
            m_total = getattr(elem, 'mass', 1.0)
            inertia = getattr(elem, 'mass_moment_inertia', 1e-3)
            
            m_node = m_total / 2.0
            
            i_idx = self.node_map[elem.node_i.id] * 3
            j_idx = self.node_map[elem.node_j.id] * 3
            
            # Kütleleri ekle
            for idx in [i_idx, i_idx+1, j_idx, j_idx+1]:
                M_global[idx, idx] += m_node
            
            # Rotasyonel atalet
            M_global[i_idx+2, i_idx+2] += inertia / 2.0
            M_global[j_idx+2, j_idx+2] += inertia / 2.0

        self.assemble() # K matrisini kur
        
        # Sınır şartlarını K'ya ekle
        for bc_data in self.bc:
            n_id, dof, val = bc_data
            idx = self.node_map[n_id] * 3 + int(dof)
            self.K_global[idx, idx] += self.penalty
            # Sınır şartı olan düğüme kütle ekle (Matris dengesi için)
            M_global[idx, idx] += 1.0

        K_dense = self.K_global.toarray()
        
        try:
            eigenvalues, eigenvectors = eigh(K_dense, M_global)
        except Exception as e:
            print(f"[!] Modal hata: {e}")
            return []

        valid_idx = eigenvalues > 1e-5
        w_squared = eigenvalues[valid_idx]
        periods = 2 * np.pi / np.sqrt(w_squared)
        
        results = []
        for i in range(min(num_modes, len(periods))):
            T = periods[i]
            freq = 1.0 / T if T > 0 else 0
            results.append({'mode': i + 1, 'period': T, 'frequency': freq})
            
        return results
