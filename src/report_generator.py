import datetime

class ReportGenerator:
    def __init__(self, filename="Analysis_Report.txt"):
        self.filename = filename

    def write_report(self, num_nodes, num_elems, displacements, input_file):
        with open(self.filename, 'w') as f:
            f.write("="*60 + "\n")
            f.write("        STRUCTURAL ANALYSIS REPORT - 2D FRAME\n")
            f.write(f"        Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
            f.write(f"Source Input File: {input_file}\n")
            f.write(f"Nodes Detected: {num_nodes}\n")
            f.write(f"Elements Detected: {num_elems}\n")
            f.write("-" * 30 + "\n\n")
            f.write("NODAL DISPLACEMENTS\n")
            f.write(f"{'DOF No':<10} | {'Displacement (m or rad)':<25}\n")
            f.write("-" * 40 + "\n")
            for i, d in enumerate(displacements):
                f.write(f"{i+1:<10} | {d: .8e}\n")
            f.write("\n" + "="*60 + "\n")
