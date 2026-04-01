import os

def create_100k_node_model():
    # Dosyanın kaydedileceği yer
    folder = "data"
    if not os.path.exists(folder): os.makedirs(folder)
    filename = os.path.join(folder, "large_design.txt")
    
    stories = 200      # 200 Kat
    nodes_per_floor = 500 # Her katta 500 Aks (Toplam ~100.000 Düğüm)
    h, w = 3.5, 5.0

    print("--- 100.000 Düğümlü Mega-Model Oluşturuluyor ---")
    with open(filename, 'w') as f:
        f.write("*MATERIALS\n1, 210000000, 0.05, 0.0002\n\n*NODES\n")
        
        node_id = 1
        for s in range(stories + 1):
            for n in range(nodes_per_floor):
                f.write(f"{node_id}, {n*w:.1f}, {s*h:.1f}\n")
                node_id += 1
        
        f.write("\n*ELEMENTS\n")
        elem_id = 1
        # Kolonlar
        for s in range(stories):
            for n in range(nodes_per_floor):
                start = s * nodes_per_floor + n + 1
                end = (s + 1) * nodes_per_floor + n + 1
                f.write(f"{elem_id}, {start}, {end}, 1\n")
                elem_id += 1
        # Kirişler
        for s in range(1, stories + 1):
            for n in range(nodes_per_floor - 1):
                start = s * nodes_per_floor + n + 1
                end = start + 1
                f.write(f"{elem_id}, {start}, {end}, 1\n")
                elem_id += 1
        
        f.write("\n*SUPPORTS\n")
        for i in range(1, nodes_per_floor + 1):
            f.write(f"{i}, 1, 1, 1\n")
            
        f.write("\n*NODAL_LOADS\n")
        top_left_node = stories * nodes_per_floor + 1
        f.write(f"{top_left_node}, 1000.0, 0.0, 0.0\n")

    print(f"Bitti! Dosya hazır: {filename}")

if __name__ == "__main__":
    create_100k_node_model()
