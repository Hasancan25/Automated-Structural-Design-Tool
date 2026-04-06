import numpy as np

class InputParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.nodes = {} 
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
                
                # Başlıkları yakala (Yıldızları ve boşlukları temizle)
                if line.startswith('*') or line.isupper():
                    current_section = line.replace('*', '').strip().upper()
                    continue

                # Virgülleri boşluğa çevir ve sayıları ayıkla
                parts = line.replace(',', ' ').split()
                try:
                    data = [float(x) for x in parts]
                except: continue

                if current_section == "MATERIALS":
                    self.materials.append(data)
                elif current_section == "NODES":
                    self.nodes[int(data[0])] = [data[1], data[2]]
                elif "ELEMENT" in current_section:
                    self.elements.append(data)
                elif "SUPPORT" in current_section:
                    self.supports.append(data)
                elif "LOAD" in current_section:
                    self.loads.append(data)

    def get_structural_data(self):
        node_ids = sorted(self.nodes.keys())
        xy_coords = np.array([self.nodes[i] for i in node_ids])
        # Dosyadaki ID'yi listedeki sıraya (0, 1, 2...) bağlayan kritik harita
        node_map = {id_val: i for i, id_val in enumerate(node_ids)}
        return xy_coords, np.array(self.materials), np.array(self.elements), self.supports, self.loads, node_map
