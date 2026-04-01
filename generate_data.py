import os

def generate_super_clean_data():
    folder = "data"
    if not os.path.exists(folder): os.makedirs(folder)
    file_path = os.path.join(folder, "large_design.txt")
    
    stories, nodes_per_floor = 200, 500
    h, w = 3.5, 5.0
    
    print("--- Virgulsüz Temiz Veri Olusturuluyor ---")
    with open(file_path, 'w') as f:
        # 1. MALZEME (Sadece bosluk)
        f.write("*MATERIALS\n1 30000000000.0 0.25 0.005\n\n")

        # 2. DÜĞÜMLER
        f.write("*NODES\n")
        node_id = 1
        for s in range(stories + 1):
            for n in range(nodes_per_floor):
                f.write(f"{node_id} {n*w:.2f} {s*h:.2f}\n")
                node_id += 1
        
        # 3. ELEMANLAR
        f.write("\n*ELEMENTS\n")
        elem_id = 1
        for s in range(stories): # Kolonlar
            for n in range(nodes_per_floor):
                f.write(f"{elem_id} {s*nodes_per_floor+n+1} {(s+1)*nodes_per_floor+n+1} 1\n")
                elem_id += 1
        for s in range(1, stories + 1): # Kirisler
            for n in range(nodes_per_floor - 1):
                f.write(f"{elem_id} {s*nodes_per_floor+n+1} {s*nodes_per_floor+n+2} 1\n")
                elem_id += 1

        # 4. MESNETLER
        f.write("\n*SUPPORTS\n")
        for i in range(1, nodes_per_floor + 1):
            f.write(f"{i} 1 1 1\n")

        # 5. YÜKLER (BASLIGI DEGISTIRDIK - PARSER GARANTISI)
        f.write("\n*NODAL_LOADS\n")
        top_start = stories * nodes_per_floor + 1
        for node in range(top_start, top_start + nodes_per_floor):
            f.write(f"{node} 10000000.0 0.0 0.0\n")

    print(f"Bitti! {file_path} hazir.")

if __name__ == "__main__":
    generate_super_clean_data()
