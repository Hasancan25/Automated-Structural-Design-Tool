import numpy as np

class InputParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.nodes = {} # Sözlük yapısı: {ID: [X, Y]}
        self.materials = []
        self.elements = []
        self.supports = []
        self.loads = []

    def parse_txt(self):
        current_section = None
        with open(self.file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                if line.startswith('*') or line.isupper():
                    current_section = line.replace('*', '').strip()
                    continue

                # Virgülleri temizle ve sayıya çevir
                parts = line.replace(',', ' ').split()
                data = [float(x) for x in parts]

                if current_section == "MATERIALS":
                    self.materials.append(data)
                elif current_section == "NODES":
                    # ID'yi anahtar (key), X ve Y'yi değer (value) yapıyoruz
                    self.nodes[int(data[0])] = [data[1], data[2]]
                elif current_section == "ELEMENTS":
                    self.elements.append(data)
                elif current_section == "SUPPORTS":
                    self.supports.append(data)
                elif current_section == "LOADS":
                    self.loads.append(data)

    def get_structural_data(self):
        # Analyzer için veriyi hazırla
        node_ids = sorted(self.nodes.keys())
        xy_coords = np.array([self.nodes[i] for i in node_ids])
        # ID'den dizi indeksine hızlı erişim haritası
        node_map = {id: i for i, id in enumerate(node_ids)}
        return xy_coords, np.array(self.materials), np.array(self.elements), self.supports, self.loads, node_map
