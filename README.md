# Automated-Structural-Design-Tool
Generic 2D Frame Analyzer & Structural SolverOverviewThis repository contains a professional-grade structural analysis engine designed to solve 2D Frame systems with dynamic geometry. Unlike static solvers, this program is built to handle structures where the number of nodes and members is unknown or variable, making it a robust tool for automated design and structural optimization.The project transitions from a fixed-input approach to a generalized solver that automatically parses structural data, determines system topology, and executes the Matrix Displacement Method with high computational efficiency.Key FeaturesDynamic Topology Parsing: Automatically identifies the number of nodes, members, and degrees of freedom (DOF) from input data without manual pre-definition.Automated Bandwidth Optimization: Features a pre-processing algorithm that calculates the optimal half-bandwidth (BW) based on node connectivity to minimize memory usage in the BandedSymmetricMatrix.Zero-Dependency Core: Developed using Pure Python. It does not require external libraries like NumPy, ensuring full transparency of the mathematical processes and solver logic.Object-Oriented Architecture (OOP): Modular design separating the InputParser, MatrixLibrary, StructuralSolver, and FrameAnalyzer for maximum maintainability.High-Precision Solver: Utilizes an optimized Gaussian Elimination algorithm specifically tailored for banded symmetric systems.

/Generic-Structural-Analyzer
│
├── /data               # Input files (txt/json) defining dynamic frame geometries
├── /src                # Core source modules
│   ├── input_parser.py # Logic for dynamic node/member discovery
│   ├── matrix_lib.py   # Specialized BandedSymmetricMatrix implementation
│   ├── solver.py       # Optimized linear system solver
│   └── analyzer.py     # Structural analysis engine (13-step algorithm)
├── main.py             # Entry point for the analysis
└── README.md

Mathematical BackgroundThe solver is based on the Matrix Displacement Method. It executes the following core operations:Coordinate transformation from local member frames to the global system using rotation matrices ([R]).Assembly of element stiffness matrices (k_{global}) into a compact global stiffness matrix (K).Solving for nodal displacements (D) via [K]{D} = {F}.Recovery of internal member forces (Axial, Shear, Moment) in local coordinates.


Author
Hasancan Doğan Civil Engineering Student

Middle East Technical University (METU)
