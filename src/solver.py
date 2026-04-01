from scipy.sparse.linalg import cg
import time

class Solver:
    def solve_sparse_system(self, K_sparse, F_vector):
        print(f"--- Iterative Solver Baslatildi ({K_sparse.shape[0]} Bilinmeyen) ---")
        start_time = time.time()
        
        # CSR formatına çevir (hesaplama için en hızlısı)
        K_csr = K_sparse.tocsr()
        F_arr = np.array(F_vector)
        
        # Conjugate Gradient Çözücü
        displacement, info = cg(K_csr, F_arr, tol=1e-10, maxiter=5000)
        
        if info == 0:
            print(f"Basari: Sistem {time.time() - start_time:.2f} saniyede cozuldu.")
        else:
            print("Uyari: Cozucu istenen hassasiyete ulasamadi!")
            
        return displacement
