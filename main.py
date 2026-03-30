from src.input_parser import InputParser
from src.analyzer import FrameAnalyzer

def main():
    print("--- Automated Structural Design Tool ---")
    
    # 1. Parse Input Data (Dynamic)
    parser = InputParser('data/input.json')
    xy, m_props, con, supports, nodal_loads = parser.get_structural_data()
    half_bw = parser.calculate_optimized_bandwidth()
    
    # Member loads (Bilinmeyen tasarımdan gelen yayılı yükler)
    member_loads = parser.data.get('member_loads', [])

    # 2. Initialize Analyzer
    analyzer = FrameAnalyzer(xy, m_props, con, supports, nodal_loads, member_loads, half_bw)
    
    # 3. Execute Analysis
    num_eq = analyzer.label_active_dof()
    print(f"Analysis started with {num_eq} active equations.")
    
    displacements = analyzer.assemble_and_solve()
    
    # 4. Report Results
    print("\nNodal Displacements:")
    for i, d in enumerate(displacements):
        print(f"D[{i+1}]: {d: .6e}")

if __name__ == "__main__":
    main()
