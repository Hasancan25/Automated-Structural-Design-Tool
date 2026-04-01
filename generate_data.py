import os

def generate_mega_structure():
    # Klasör kontrolü
    folder = "data"
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    file_path = os.path.join(folder, "large_design.txt")
    
    # Yapı Parametreleri
    stories = 200          # 200 Katlı bina
    nodes_per_floor = 500   # Her katta 500 düğüm
    h = 3.5                # Kat yüksekliği (m)
    w = 5.0                # Açıklık (m)
    
    print(f"--- {stories * nodes_per_floor + nodes_per_floor} Düğümlü Model Oluşturuluyor ---")

    with open(file_path, 'w') as f:
        # 1. MALZEME (E, A, I)
        # Betonarme benzeri değerler: E=30GPa, A=0.25m2, I=0.005m4
        f.write("*MATERIALS\n")
        f.write("1, 30000000000.0, 0.25, 0.005\n\n")

        # 2. DÜĞÜMLER (NODES)
        f.write("*NODES\n")
        node_id = 1
        for s in range(stories + 1): # Temelden çatıya
            y = s * h
            for n in range(nodes_per_floor):
                x = n * w
                f.write(f"{node_id}, {x:.2f}, {y:.2f}\n")
                node_id += 1
        
        # 3. ELEMANLAR (ELEMENTS)
        f.write("\n*ELEMENTS\n")
        elem_id = 1
        
        # Kolonlar (Düşey elemanlar)
        for s in range(stories):
            for n in range(nodes_per_floor):
                start_node = s * nodes_per_floor + n + 1
                end_node = (s + 1) * nodes_per_floor + n + 1
                f.write(f"{elem_id}, {start_node}, {end_node}, 1\n")
                elem_id += 1
                
        # Kirişler (Yatay elemanlar)
        for s in range(1, stories + 1):
            for n in range(nodes_per_floor - 1):
                start_node = s * nodes_per_floor + n + 1
                end_node = start_node + 1
                f.write(f"{elem_id}, {start_node}, {end_node}, 1\n")
                elem_id += 1

        # 4. MESNETLER (SUPPORTS)
        f.write("\n*SUPPORTS\n")
        # Zemin kattaki (s=0) tüm düğümler ankastre (1, 1, 1)
        for i in range(1, nodes_per_floor + 1):
            f.write(f"{i}, 1, 1, 1\n")

        # 5. NODAL YÜKLER (LOADS)
        f.write("\n*NODAL_LOADS\n")
        # En üst kattaki tüm düğümlere şiddetli rüzgar yükü (X yönünde)
        top_floor_start = stories * nodes_per_floor + 1
        top_floor_end = (stories + 1) * nodes_per_floor
        
        print(f"Yükleme yapılıyor: Düğüm {top_floor_start} ile {top_floor_end} arası.")
        
        for node in range(top_floor_start, top_floor_end + 1):
            # 10 Milyon Newton yükü her düğüme basıyoruz
            f.write(f"{node}, 10000000.0, 0.0, 0.0\n")

    print(f"BAŞARILI: {file_path} dosyası oluşturuldu.")

if __name__ == "__main__":
    generate_mega_structure()
