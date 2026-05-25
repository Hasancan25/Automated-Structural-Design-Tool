import json
import os
from src.models import Node, Material, Element 

class IOHandler:
    @staticmethod
    def load_input(file_path, ndof=3):
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.getcwd(), file_path)
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 1. Malzemeleri oku
        mats = {int(m['id']): Material(m['id'], m.get('name'), m['E'], m['A'], m['I'], m.get('alpha',0), m.get('h',0)) for m in data['materials']}
        
        # 2. Düğüm yüklerini (Nodal Loads) haritala
        loads_dict = {}
        for load in data.get('nodal_loads', []):
            nid = int(load.get('node_id', 0))
            if nid not in loads_dict: loads_dict[nid] = []
            loads_dict[nid].append(load)

        # 3. Düğümleri (Nodes) oluştur
        nodes_dict = {int(n['id']): Node(n['id'], n['x'], n['y'], ndof=ndof, nodal_loads=loads_dict.get(int(n['id']), [])) for n in data['nodes']}
        
        # 4. Elemanları (Elements) oluştur - KRİTİK DEĞİŞİKLİK BURADA
        elements = []
        for e in data['elements']:
            elem = Element(
                e['id'], 
                nodes_dict[e['node_i']], 
                nodes_dict[e['node_j']], 
                mats[e['material_id']], 
                e.get('type','frame'),
                udl=e.get('udl', 0.0),            # UDL artık okunuyor!
                release_i=e.get('release_i', False), # Baş mafsal
                release_j=e.get('release_j', False)  # Son mafsal
            )
            elements.append(elem)
            
        # 5. Sınır şartları ve diğer etkiler
        bc = [(int(b['node_id']), int(b['dof']), float(b['value'])) for b in data['boundary_conditions']]
        
        return list(nodes_dict.values()), elements, bc, data.get('constraints', []), data.get('effects', [])
