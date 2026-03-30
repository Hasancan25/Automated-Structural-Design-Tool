class BandedSymmetricMatrix:
    def __init__(self, size, half_bandwidth):
        self.size = size
        self.hbw = half_bandwidth
        self.data = [[0.0] * (half_bandwidth + 1) for _ in range(size)]

    def assemble(self, row, col, value):
        if row > col: row, col = col, row
        bw_idx = col - row
        if bw_idx <= self.hbw:
            self.data[row-1][bw_idx] += value
