import numpy as np
from scipy.sparse import lil_matrix

class SparseStiffnessMatrix:
    def __init__(self, size):
        self.size = size
        # LIL formatı kurulum (assemble) sırasında hızlıdır
        self.matrix = lil_matrix((size, size))

    def assemble(self, row, col, value):
        # Python 1-tabanlı indexten 0-tabanlıya geçiş
        self.matrix[row-1, col-1] += value
