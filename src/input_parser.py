class InputParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.materials = []
        self.nodes = []
        self.elements = []
        self.supports = []
        self.nodal_loads = []

    def parse_txt(self):
        current_section = None
        with open(self.file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                
                if line.startswith('*'):
                    current_section = line
                    continue

                # KRİTİK DÜZELTME: Hem virgülü hem boşluğu temizleyip parçalara ayırır
                data = line.replace(',', ' ').split()
                if not data: continue

                try:
                    if current_section == "*MATERIALS":
                        self.materials.append([float(x) for x in data])
                    elif current_section == "*NODES":
                        self.nodes.append([float(x) for x in data])
                    elif current_section == "*ELEMENTS":
                        self.elements.append([float(x) for x in data])
                    elif current_section == "*SUPPORTS":
                        self.supports.append([float(x) for x in data])
                    elif current_section == "*NODAL_LOADS":
                        self.nodal_loads.append([float(x) for x in data])
                except (ValueError, IndexError):
                    continue

    def get_data(self):
        return (self.nodes, self.materials, self.elements, 
                self.supports, self.nodal_loads, [])
