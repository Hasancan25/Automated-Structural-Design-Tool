# Automated-Structural-Design-Tool

## Overview
This repository contains a professional-grade structural analysis engine designed to solve 2D Frame systems with **dynamic geometry**. Unlike static solvers, this program is built to handle structures where the number of nodes and members is unknown or variable, making it a robust tool for automated design and structural optimization.

The project transitions from a fixed-input approach to a **generalized solver** that automatically parses structural data, determines system topology, and executes the Matrix Displacement Method with high computational efficiency.

## Key Features
* **Dynamic Topology Parsing:** Automatically identifies the number of nodes, members, and degrees of freedom (DOF) from input data without manual pre-definition.
* **Automated Bandwidth Optimization:** Features a pre-processing algorithm that calculates the optimal half-bandwidth (BW) based on node connectivity to minimize memory usage in the `BandedSymmetricMatrix`.
* **Zero-Dependency Core:** Developed using **Pure Python**. It does not require external libraries like NumPy, ensuring full transparency of the mathematical processes and solver logic.
* **Object-Oriented Architecture (OOP):** Modular design separating the `InputParser`, `MatrixLibrary`, `StructuralSolver`, and `FrameAnalyzer` for maximum maintainability.
* **High-Precision Solver:** Utilizes an optimized Gaussian Elimination algorithm specifically tailored for banded symmetric systems.

## Project Structure
```text
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
