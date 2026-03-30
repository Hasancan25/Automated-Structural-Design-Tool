class InputParser:
    """
    PURPOSE: Reads a formatted .txt file to build structural models dynamically.
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.nodes = []
        self.elements = []
        self.materials = []
        self.supports = []
        self.nodal_loads = []
        self.member_loads = []

    def parse_txt(self):
        """PURPOSE: Reads the .txt file line by line and populates structural lists."""
        current_section = None
        try:
            with open(self.file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'): continue # Boş satır/yorum geç
                    
                    if line.startswith('*'):
                        current_section = line.upper()
                        continue
                    
                    data = [d.strip() for d in line.split(',')]
                    
                    if current_section == "*NODES":
                        self.nodes.append({'id': int(data[0]), 'x': float(data[1]), 'y': float(data[2])})
                    
                    elif current_section == "*ELEMENTS":
                        self.elements.append({'id': int(data[0]), 'start': int(data[1]), 'end': int(data[2]), 'mat': int(data[3])})
                    
                    elif current_section == "*MATERIALS":
                        self.materials.append({'id': int(data[0]), 'E': float(data[1]), 'A': float(data[2]), 'I': float(data[3])})
                    
                    elif current_section == "*SUPPORTS":
                        self.supports.append({'node_id': int(data[0]), 'rx': int(data[1]), 'ry': int(data[2]), 'rz': int(data[3])})
                    
                    elif current_section == "*NODAL_LOADS":
                        self.nodal_loads.append({'node_id': int(data[0]), 'fx': float(data[1]), 'fy': float(data[2]), 'mz': float(data[3])})
                    
                    elif current_section == "*MEMBER_LOADS":
                        self.member_loads.append({'elem_id': int(data[0]), 'type': data[1], 'value': float(data[2])})
            
            print(f"Successfully parsed: {len(self.nodes)} nodes and {len(self.elements)} elements.")
        except Exception as e:
            print(f"Error parsing file: {e}")

    def get_structural_data(self):
        """PURPOSE: Formats the parsed data for the FrameAnalyzer engine."""
        xy = [[n['x'], n['y']] for n in self.nodes]
        m_props = [[m['A'], m['I'], m['E']] for m in self.materials]
        con = [[e['start'], e['end'], e['mat']] for e in self.elements]
        
        # Supports & Loads array initialization
        num_n = len(xy)
        supp_array = [[0, 0, 0] for _ in range(num_n)]
        for s in self.supports: supp_array[s['node_id']-1] = [s['rx'], s['ry'], s['rz']]
        
        load_array = [[0.0, 0.0, 0.0] for _ in range(num_n)]
        for l in self.nodal_loads: load_array[l['node_id']-1] = [l['fx'], l['fy'], l['mz']]
        
        return xy, m_props, con, supp_array, load_array

    def calculate_optimized_bandwidth(self):
        """Calculates BW dynamically from parsed elements."""
        max_diff = 0
        for e in self.elements:
            diff = abs(e['start'] - e['end'])
            if diff > max_diff: max_diff = diff
        return (max_diff + 1) * 3 - 1
