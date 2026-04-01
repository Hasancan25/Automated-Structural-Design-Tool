import numpy as np
from scipy.sparse.linalg import cg
import time

class Solver:
    """
    Yüksek performanslı yapısal analiz çözücü.
    SciPy 1.11+ ve Python 3.13 uyumlu versiyon.
    """
    def solve_sparse_system(self, K_sparse, F_vector):
        print(f"--- Iterative Solver (CG) Baslatildi ---")
        start_time = time.time()
        
        # 1. Adım: Seyrek matrisi CSR formatına çevir
        K_csr = K_sparse.tocsr()
        
        # 2. Adım: Yük vektörünü NumPy dizisine çevir
        F_arr = np.array(F_vector, dtype=float)
        
        # 3. Adım: Conjugate Gradient Çözücü
        # DİKKAT: Yeni SciPy sürümlerinde 'tol' yerine 'rtol' kullanılır.
        displacement, info = cg(K_csr, F_arr, rtol=1e-10, maxiter=5000)
        
        if info == 0:
            elapsed = time.time() - start_time
            print(f"Basari: {len(F_arr)} serbestlik dereceli sistem {elapsed:.2f} saniyede cozuldu.")
        else:
            print(f"Uyari: Cozucu {info} iterasyonda tam yakinliga ulasamadi!")
            
        return displacement
