import numpy as np
from scipy.sparse.linalg import cg
import time

class Solver:
    """
    Yüksek performanslı yapısal analiz çözücü.
    Conjugate Gradient (CG) ve Sparse Matrix teknolojisi ile 
    milyonlarca bilinmeyeni saniyeler içinde çözer.
    """
    def solve_sparse_system(self, K_sparse, F_vector):
        print(f"--- Iterative Solver (CG) Baslatildi ---")
        start_time = time.time()
        
        # 1. Adım: Seyrek matrisi en hızlı işlem formatı olan CSR'a çevir
        K_csr = K_sparse.tocsr()
        
        # 2. Adım: Yük vektörünü sayısal hesaplama dizisine çevir
        F_arr = np.array(F_vector, dtype=float)
        
        # 3. Adım: Conjugate Gradient Çözücü
        # tol=1e-10 hassasiyeti temsil eder, maxiter ise maksimum deneme sayısıdır
        displacement, info = cg(K_csr, F_arr, tol=1e-10, maxiter=5000)
        
        if info == 0:
            elapsed = time.time() - start_time
            print(f"Basari: {len(F_arr)} serbestlik dereceli sistem {elapsed:.2f} saniyede cozuldu.")
        else:
            print(f"Uyari: Cozucu {info} iterasyonda tam yakinliğa ulasamadi!")
            
        return displacement
