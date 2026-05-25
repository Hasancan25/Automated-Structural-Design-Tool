import json
import os
import re
import numpy as np
from src.section import SectionFactory
from src.load_combination import LoadCombination, EnvelopeManager # OOP Yapısal Bağlantı Köprüsü

def generate_structure():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'data', 'grid_config.json')
    db_path = os.path.join(current_dir, 'data', 'sections_db.json')
    bu_db_path = os.path.join(current_dir, 'data', 'built_up_db.json')
    output_path = os.path.join(current_dir, 'data', 'input.json')

    # 1. Konfigürasyonları Yükle
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    if os.path.exists(db_path):
        with open(db_path, 'r', encoding='utf-8') as f:
            section_db = json.load(f)
    else:
        section_db = {}

    if os.path.exists(bu_db_path):
        with open(bu_db_path, 'r', encoding='utf-8') as f:
            built_up_db = json.load(f)
    else:
        built_up_db = {}

    bays = config['grid']['bay_widths']
    stories = config['grid']['story_heights']
    mat_id = config['grid'].get('material_id', 1)
    has_bracing = config['grid'].get('has_bracing', False)
    brace_seq = config['grid'].get('bracing_sequence', [list(range(len(bays)))])
    
    # --- ÇİFT KÜTÜPHANELİ HİBRİT PROFİL SEÇİM MOTORU (OOP FABRİKASINA BAĞLANDI) ---
    raw_col = config['grid'].get('column_section', 'IPE200')
    raw_beam = config['grid'].get('beam_section', 'HEA300')
    raw_brace = config['grid'].get('brace_section', 'IPE200')

    # Fabrika sınıfı üzerinden kesit özelliklerini doğrudan CrossSection nesnesi olarak üretiyoruz
    col_sec = SectionFactory.create_section(raw_col, section_db, built_up_db)
    beam_sec = SectionFactory.create_section(raw_beam, section_db, built_up_db)
    brace_sec = SectionFactory.create_section(raw_brace, section_db, built_up_db)

    # input.json için 3 ayrı bağımsız malzeme kartı tanımlıyoruz (Nesne Öznitelikleri Doğrudan Aktarılır)
    materials = [
        {"id": 1, "name": f"Column_{raw_col}", "E": 200000000.0, "A": col_sec.A, "I": col_sec.I},
        {"id": 2, "name": f"Beam_{raw_beam}", "E": 200000000.0, "A": beam_sec.A, "I": beam_sec.I},
        {"id": 3, "name": f"Brace_{raw_brace}", "E": 200000000.0, "A": brace_sec.A, "I": brace_sec.I}
    ]
    
    nodes = []
    elements = []
    bc = []
    loads = []

    # --- 1. KOORDİNAT HESABI ---
    x_coords = [0.0]; cur_x = 0.0
    for w in bays: cur_x += w; x_coords.append(cur_x)
    y_coords = [0.0]; cur_y = 0.0
    for h in stories: cur_y += h; y_coords.append(cur_y)

    # --- 2. DÜĞÜM ÜRETİMİ ---
    node_id = 0; node_map = {}
    for j, y in enumerate(y_coords):
        for i, x in enumerate(x_coords):
            nodes.append({"id": node_id, "x": x, "y": y})
            node_map[(i, j)] = node_id
            if j == 0:
                for dof in [0, 1, 2]: bc.append({"node_id": node_id, "dof": dof, "value": 0})
            node_id += 1

    # --- 3. ELEMAN ÜRETİMİ ---
    elem_id = 0
    num_x = len(x_coords); num_y = len(y_coords)

    # A. Kolonlar -> Malzeme ID: 1 (Yük desenleri sıfırlanmış olarak)
    for i in range(num_x):
        for j in range(num_y - 1):
            elements.append({
                "id": elem_id, "node_i": node_map[(i, j)], "node_j": node_map[(i, j+1)], "material_id": 1,
                "load_patterns": {"DEAD": 0.0, "LIVE": 0.0, "SNOW": 0.0}
            })
            elem_id += 1

    # B. Kirişler -> Malzeme ID: 2 (DEAD, LIVE ve SNOW yükleri kat bazlı ayrıştırılır)
    for j in range(1, num_y):
        is_roof = (j == num_y - 1)
        d_val = config['loads']['roof_dead_udl'] if is_roof else config['loads']['dead_floor_udl']
        l_val = config['loads']['roof_live_udl'] if is_roof else config['loads']['live_floor_udl']
        s_val = config['loads']['snow_udl'] if is_roof else 0.0
        
        for i in range(num_x - 1):
            elements.append({
                "id": elem_id, "node_i": node_map[(i, j)], "node_j": node_map[(i+1, j)], "material_id": 2,
                "load_patterns": {"DEAD": d_val, "LIVE": l_val, "SNOW": s_val}
            })
            elem_id += 1

    # C. Dinamik X-Bracing -> Malzeme ID: 3 (DÖNGÜ DIŞINA ÇIKARILDI - MÜKERRER ELEMANLAR ENGELLENDİ)
    if has_bracing:
        print(f"[+] Caprazlar sirali olarak diziliyor. Desen uzunlugu: {len(brace_seq)}")
        for j in range(num_y - 1):
            pattern_idx = (num_y - 2 - j) % len(brace_seq)
            current_floor_pattern = brace_seq[pattern_idx]

            for i in range(num_x - 1):
                if i in current_floor_pattern:
                    # X-Brace (\)
                    elements.append({
                        "id": elem_id, "node_i": node_map[(i, j)], "node_j": node_map[(i+1, j+1)], "material_id": 3,
                        "load_patterns": {"DEAD": 0.0, "LIVE": 0.0, "SNOW": 0.0}
                    })
                    elem_id += 1
                    # X-Brace (/)
                    elements.append({
                        "id": elem_id, "node_i": node_map[(i+1, j)], "node_j": node_map[(i, j+1)], "material_id": 3,
                        "load_patterns": {"DEAD": 0.0, "LIVE": 0.0, "SNOW": 0.0}
                    })
                    elem_id += 1

    # --- 4. YÜKLER (PARAMETRİK HİBRİT DAĞITIM - WIND & SEISMIC) ---
    # TBDY 2018 / ASCE 7 üçgensel kat dağılımı için gerçek kümülatif payda hesabı (3.0m Sınırı Kaldırıldı)
    total_mh = sum(y_coords[k] for k in range(1, num_y))
    
    for j in range(1, num_y):
        level_wind = config['loads']['wind_base'] + (j-1) * config['loads']['wind_increment']
        # Deprem yükü kat ağırlık merkezi yüksekliği (y_coords[j]) ile tam parametrik çarpılır
        level_seismic = (config['loads']['seismic_base_shear_v'] * y_coords[j]) / total_mh if total_mh > 0 else 0.0
        
        loads.append({
            "node_id": node_map[(0, j)],
            "load_patterns": {
                "WIND": level_wind,
                "SEISMIC": level_seismic
            }
        })

    # --- 5. KAYIT ---
    final_data = {
        "materials": materials,
        "nodes": nodes, 
        "elements": elements, 
        "boundary_conditions": bc, 
        "nodal_loads": loads, 
        "structural_effects": []
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4)

    print(f"\n[✓] Dinamik Profil Senkronizasyonlu yapi uretildi. Toplam {len(elements)} eleman.")

if __name__ == "__main__":
    generate_structure()
