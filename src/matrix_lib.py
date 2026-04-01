import numpy as np
from scipy.sparse import coo_matrix

class SparseStiffnessMatrix:
    def __init__(self, size):
        self.size = size
        # Verileri biriktirmek için listeler kullanıyoruz
        self.row_indices = []
        self.col_indices = []
        self.data_values = []

    def assemble(self, row, col, value):
        """Veriyi listeye ekler (LIL'den çok daha hızlıdır)."""
        if value != 0:
            self.row_indices.append(row - 1)
            self.col_indices.append(col - 1)
            self.data_values.append(value)

    def finalize(self):
        """Listelerdeki veriyi tek seferde Sparse Matrix'e dönüştürür."""
        print(f"Birim matrisler birleştiriliyor (Toplam {len(self.data_values)} giriş)...")
        K = coo_matrix(
            (self.data_values, (self.row_indices, self.col_indices)),
            shape=(self.size, self.size)
        )
        return K.tocsr() # Hesaplama için CSR formatına çevir
