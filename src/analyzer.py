def solve(self):
        num_eq = self.label_active_dof()
        K_obj = SparseStiffnessMatrix(num_eq) # Nesneyi oluştur
        F = np.zeros(num_eq)

        # ... (Yük montajı kısmı aynı kalıyor) ...

        # Elemanların Matrise Yerleştirilmesi
        print(f"Adım 3: {self.num_elem} eleman monte ediliyor...")
        for i in range(self.num_elem):
            k_g = self.get_k_global(i)
            s_idx = int(float(str(self.con[i][0]).replace(',', '').strip())) - 1
            e_idx = int(float(str(self.con[i][1]).replace(',', '').strip())) - 1
            dofs = list(self.e_array[s_idx]) + list(self.e_array[e_idx])
            
            for r in range(6):
                for c in range(6):
                    if dofs[r] > 0 and dofs[c] > 0:
                        K_obj.assemble(dofs[r], dofs[c], k_g[r][c])

        # Matrisi oluştur ve çözücüye gönder
        K_sparse = K_obj.finalize() # İşte yeni ve hızlı adım burası!
        
        print("Adım 4: Sistem çözücüye gönderiliyor...")
        solver = Solver()
        return solver.solve_sparse_system(K_sparse, F)
