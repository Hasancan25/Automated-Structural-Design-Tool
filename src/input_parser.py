class InputParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.materials = []
        self.nodes = []
        self.elements = []
        self.supports = []
        self.nodal_loads = []

    def parse_txt(self):
        """Dosyayı okur ve verileri ilgili listelere ayırır."""
        current_section = None
        with open(self.file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): 
                    continue
                
                if line.startswith('*'):
                    current_section = line
                    continue

                # Hem virgüllü hem boşluklu formatı desteklemek için önce virgülleri temizliyoruz
                data = line.replace(',', ' ').split()
                if not data: 
                    continue

                try:
                    # Sayısal değerleri float listesine çevir
                    val = [float(x) for x in data]
                    
                    if current_section == "*MATERIALS":
                        self.materials.append(val)
                    elif current_section == "*NODES":
                        self.nodes.append(val)
                    elif current_section == "*ELEMENTS":
                        self.elements.append(val)
                    elif current_section == "*SUPPORTS":
                        self.supports.append(val)
                    elif current_section == "*NODAL_LOADS":
                        self.nodal_loads.append(val)
                except (ValueError, IndexError):
                    continue

    def get_structural_data(self):
        """
        main.py dosyasının beklediği 5 ana veri grubunu 
        FrameAnalyzer sınıfına uygun formatta hazırlar ve döner.
        """
        # 1. xy: Sadece koordinatlar [[x, y], [x, y], ...]
        # Düğüm listesindeki ilk eleman (ID) atlanır.
        xy = [n[1:3] for n in self.nodes]
        
        # 2. m_props: Malzeme özellikleri [[id, E, A, I], ...]
        m_props = self.materials
        
        # 3. con: Eleman bağlantıları [[start, end, mat_id], ...]
        # Eleman listesindeki ilk eleman (elem_id) atlanır.
        con = [e[1:4] for e in self.elements]
        
        # 4. supports: Mesnetler [[node_id, r1, r2, r3], ...]
        supports = self.supports
        
        # 5. loads: Yükler [[node_id, fx, fy, m], ...]
        loads = self.nodal_loads
        
        return xy, m_props, con, supports, loads
