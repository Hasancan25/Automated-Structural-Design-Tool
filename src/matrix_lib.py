import numpy as np
from scipy.sparse import coo_matrix

class SparseStiffnessMatrix:
    def __init__(self, size):
        self.size = size
        # Verileri (Satır, Sütun, Değer) olarak listelerde biriktiriyoruz
        self.row_indices = []
        self.col_indices = []
        self.data_values = []

    def assemble(self, row, col, value):
        """Veriyi listeye ekler (COO formatı için en hızlı yöntemdir)."""
        if value != 0:
            self.row_indices.append(row - 1)
            self.col_indices.append(col - 1)
            self.data_values.append(value)

    def finalize(self):
        """Listelerdeki veriyi tek seferde CSR Sparse Matrix'e dönüştürür."""
        print(f"-> {len(self.data_values)} adet matris hücresi birleştiriliyor...")
        K = coo_matrix(
            (self.data_values, (self.row_indices, self.col_indices)),
            shape=(self.size, self.size)
        )
        # Hesaplama hızı için CSR formatına çeviriyoruz
        return K.tocsr()
