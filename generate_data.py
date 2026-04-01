import os

def generate_mega_structure():
    folder = "data"
    if not os.path.exists(folder): os.makedirs(folder)
    file_path = os.path.join(folder, "large_design.txt")
    
    stories = 200          
    nodes_per_floor = 500   
    h, w = 3.5, 5.0                
    
    print(f"--- {stories * nodes_per_floor + nodes_per_floor} Düğümlü Model Yazılıyor ---")

    with open(file_path, 'w') as f:
        # 1. MALZEME (E A I) - Virgülleri kaldırdık
        f.write("*MATERIALS\n")
        f.write("1 30000000000.0 0.25 0.005\n\n")

        # 2. DÜĞÜMLER (NODES) - Sadece boşluk
        f.write("*NODES\n")
        node_id = 1
        for s in range(stories + 1):
            y = s * h
            for n in range(nodes_per_floor):
                x = n * w
                f.write(f"{node_id} {x:.2f} {y:.2f}\n")
                node_id += 1
        
        # 3. ELEMANLAR (ELEMENTS)
        f.write("\n*ELEMENTS\n")
        elem_id = 1
        for s in range(stories): # Kolonlar
            for n in range(nodes_per_floor):
                start, end = s*nodes_per_floor+n+1, (s+1)*nodes_per_floor+n+1
                f.write(f"{elem_id} {start} {end} 1\n")
                elem_id += 1
        for s in range(1, stories + 1): # Kirişler
            for n in range(nodes_per_floor - 1):
                start = s*nodes_per_floor+n+1
                f.write(f"{elem_id} {start} {start+1} 1\n")
                elem_id += 1

        # 4. MESNETLER (SUPPORTS)
        f.write("\n*SUPPORTS\n")
        for i in range(1, nodes_per_floor + 1):
            f.write(f"{i} 1 1 1\n")

        # 5. NODAL YÜKLER (En kritik yer burası)
        f.write("\n*NODAL_LOADS\n")
        top_floor_start = stories * nodes_per_floor + 1
        top_floor_end = (stories + 1) * nodes_per_floor
        
        for node in range(top_floor_start, top_floor_end + 1):
            # 10 Milyon Newton (X yönünde rüzgar)
            f.write(f"{node} 10000000.0 0.0 0.0\n")

    print(f"BAŞARILI: {file_path} hazır. Artık yükler 0 çıkamaz!")

if __name__ == "__main__":
    generate_mega_structure()
