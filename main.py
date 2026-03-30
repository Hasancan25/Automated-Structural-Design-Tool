import os
from src.input_parser import InputParser
from src.analyzer import FrameAnalyzer

def main():
    # 1. Giriş ve Karşılama
    print("="*50)
    print("   AUTOMATED STRUCTURAL DESIGN TOOL - 2D FRAME")
    print("   Developed by: Hasancan Dogan (METU CE)")
    print("="*50)

    # 2. Dosya Yolunu Belirle (data/test_design.txt)
    input_file = os.path.join('data', 'test_design.txt')
    
    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}")
        return

    # 3. Veriyi Oku ve Parse Et (Dinamik Tasarım Keşfi)
    print("\n[STEP 1] Parsing structural data...")
    parser = InputParser(input_file)
    parser.parse_txt()
    
    # Verileri ayıkla
    xy, m_props, con, supports, loads = parser.get_structural_data()
    bw = parser.calculate_optimized_bandwidth()
    member_loads = parser.member_loads # Parser'daki listeyi doğrudan alıyoruz

    print(f"-> Detected {len(xy)} nodes and {len(con)} elements.")
    print(f"-> Optimized Half-Bandwidth calculated: {bw}")

    # 4. Analiz Motorunu Ateşle (Analyzer)
    print("\n[STEP 2] Initializing Structural Engine...")
    analyzer = FrameAnalyzer(xy, m_props, con, supports, loads, member_loads, bw)
    
    num_eq = analyzer.label_active_dof()
    print(f"-> System degrees of freedom (DOF) assigned. Active equations: {num_eq}")

    # 5. Çözüm (Assembly & Solve)
    print("\n[STEP 3] Assembling K matrix and solving K*D=F...")
    try:
        displacements = analyzer.solve()
        print("-> Solution successfully obtained.")
    except Exception as e:
        print(f"-> Error during solver execution: {e}")
        return

    # 6. Sonuçları Raporla (Output)
    print("\n" + "="*50)
    print("   ANALYSIS RESULTS: NODAL DISPLACEMENTS")
    print("="*50)
    print(f"{'DOF No':<10} | {'Displacement (m or rad)':<25}")
    print("-" * 40)
    
    for i, d in enumerate(displacements):
        print(f"{i+1:<10} | {d: .8e}")
    
    print("\n" + "="*50)
    print("   Analysis Complete. Check your output values.")
    print("="*50)

if __name__ == "__main__":
    main()
