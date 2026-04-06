import numpy as np

class InputParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.nodes = []
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
                
                # Bölüm başlıklarını yakala
                if line.startswith('*') or line.isupper():
                    current_section = line.replace('*', '').strip()
                    continue

                # SATIRI TEMİZLE VE PARÇALA (Virgül veya Boşluk fark etmez)
                # "1, 0.0, 0.0" -> ["1", "0.0", "0.0"]
                parts = line.replace(',', ' ').split()
                data = [float(x) for x in parts]

                if current_section == "MATERIALS":
                    self.materials.append(data)
                elif current_section == "NODES":
                    self.nodes.append(data[1:]) # ID'yi atla, X ve Y'yi al
                elif current_section == "ELEMENTS":
                    self.elements.append(data)
                elif current_section == "SUPPORTS":
                    self.supports.append(data)
                elif current_section == "LOADS":
                    self.loads.append(data)

    def get_structural_data(self):
        # Matris işlemlerine uygun formatta döndür
        return (np.array(self.nodes), np.array(self.materials), 
                np.array(self.elements), self.supports, self.loads)
