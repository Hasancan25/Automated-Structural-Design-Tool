class Solver:
    def solve_banded_system(self, matrix, F):
        n = matrix.size
        hbw = matrix.hbw
        A = matrix.data
        # Forward elimination
        for i in range(n):
            pivot = A[i][0]
            for j in range(1, min(hbw + 1, n - i)):
                factor = A[i][j] / pivot
                for k in range(min(hbw + 1 - j, n - (i + j))):
                    A[i+j][k] -= factor * A[i][j+k]
                F[i+j] -= factor * F[i]
            F[i] /= pivot
        # Back substitution
        for i in range(n - 1, -1, -1):
            for j in range(1, min(hbw + 1, n - i)):
                F[i] -= (A[i][j] / A[i][0]) * F[i+j]
        return F
