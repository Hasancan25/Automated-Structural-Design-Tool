import os

def generate_skyscraper_data():
    # Klasör kontrolü
    if not os.path.exists('data'):
        os.makedirs('data')
        
    filename = "data/large_design.txt"
    num_stories = 200  # 200 Katlı Gökdelen
    nodes_per_floor = 500 # Toplam 100.500 düğüm
    
    print(f"--- {num_stories} katli devasa veri seti uretiliyor... ---")
    
    with open(filename, "w") as f:
        # 1. Malzeme Özellikleri: [E, A, I]
        # Betonarme/Çelik karışımı bir rijitlik (Örn: E=30GPa, A=1m2, I=0.1m4)
        f.write("MATERIALS\n")
        f.write("1 3.0e10 1.0 0.1\n")
        
        # 2. Düğümler (Nodes): [ID, X, Y]
        f.write("\nNODES\n")
        node_id = 1
        for floor in range(num_stories + 1):
            y = floor * 3.5  # Kat yüksekliği 3.5m
            for n in range(nodes_per_floor):
                x = n * 5.0 # Açıklık 5m
                f.write(f"{node_id} {x} {y}\n")
                node_id += 1
        
        total_nodes = node_id - 1
        
        # 3. Elemanlar (Elements): [ID1, ID2, MatID]
        f.write("\nELEMENTS\n")
        # Kirişler ve Kolonlar (Basit bir çerçeve sistemi)
        for floor in range(num_stories + 1):
            start_node = floor * nodes_per_floor + 1
            for n in range(nodes_per_floor - 1):
                # Kirişler
                f.write(f"{start_node + n} {start_node + n + 1} 1\n")
            
            if floor < num_stories:
                for n in range(nodes_per_floor):
                    # Kolonlar
                    f.write(f"{start_node + n} {start_node + n + nodes_per_floor} 1\n")
        
        # 4. Mesnetler (Supports): [NodeID, DOF, Value]
        f.write("\nSUPPORTS\n")
        # Zemin kattaki (Y=0) tüm düğümler ankastre
        for n in range(nodes_per_floor):
            f.write(f"{n + 1} 1 0.0\n") # X sabit
            f.write(f"{n + 1} 2 0.0\n") # Y sabit
            f.write(f"{n + 1} 3 0.0\n") # Dönme sabit
            
        # 5. Yükler (Loads): [NodeID, DOF, Force]
        f.write("\nLOADS\n")
        # Tüm binaya rüzgar yükü (X yönünde)
        for node in range(nodes_per_floor + 1, total_nodes + 1):
            # En üst katlara daha fazla yük (Rüzgar profili)
            force = 5000.0  # 5 kN
            f.write(f"{node} 1 {force}\n")

    print(f"Bitti! {filename} hazir. Toplam Dugum: {total_nodes}")

if __name__ == "__main__":
    generate_skyscraper_data()
