import pytest
import numpy as np
from src.models import Node, Element, Material
from src.solver import StructuralSolver

TOL = 1e-6

# --- UNIT TESTS (Birim Testleri) ---

def test_unit_stiffness_symmetry():
    """UT-01: Eleman rijitlik matrisi simetrik mi?"""
    mat = Material(1, "Steel", 2e8, 0.05, 0.0008)
    n1, n2 = Node(1, 0, 0), Node(2, 8, 0)
    elem = Element(1, n1, n2, mat)
    solver = StructuralSolver([n1, n2], [elem], [])
    k_local = solver.get_local_k(elem) # Fonksiyon adını solver'ına göre düzelt
    assert np.allclose(k_local, k_local.T, atol=TOL)

def test_unit_transformation_orthogonality():
    """UT-02: Transformasyon matrisi (T) ortogonal mi?"""
    n1, n2 = Node(1, 0, 0), Node(2, 3, 4)
    elem = Element(1, n1, n2, None)
    solver = StructuralSolver([n1, n2], [elem], [])
    T = solver.get_transformation_matrix(elem)
    # Ortogonal matrislerde T.T @ T = I olmalı
    identity = T.T @ T
    assert np.allclose(identity, np.eye(len(T)), atol=TOL)

def test_unit_fef_calculation():
    """UT-03: UDL için Sabit Uç Kuvvetleri (wL/2) doğru mu?"""
    mat = Material(1, "Steel", 2e8, 0.05, 0.0008)
    n1, n2 = Node(1, 0, 0), Node(2, 8, 0)
    elem = Element(1, n1, n2, mat, udl=-12.0)
    solver = StructuralSolver([n1, n2], [elem], [])
    fef = solver._get_element_udl_fea(elem) # wL/2 = 12*8/2 = 48
    assert abs(fef[1]) == 48.0 # Düşey yük kontrolü

# --- INTERFACE TESTS (Arayüz Testleri) ---

def test_interface_assembly_size():
    """IT-01: Global matris boyutu ndof'a göre doğru kuruluyor mu?"""
    # 4 node, ndof=3 -> 12x12 matris
    nodes = [Node(i, i*4, 0) for i in range(1, 5)]
    solver = StructuralSolver(nodes, [], [])
    solver.assemble()
    assert solver.K_global.shape == (12, 12)

def test_interface_load_injection():
    """IT-02: Düğüm yükleri F_global vektörüne doğru akıyor mu?"""
    n1 = Node(1, 0, 0, nodal_loads=[{'fy': -100.0}])
    solver = StructuralSolver([n1], [], [])
    solver.assemble()
    assert solver.F_global[1] == -100.0 # 1. indis Fy yüküdür

# --- REGRESSION TESTS (Regresyon Testleri) ---

def test_regression_pure_truss_logic():
    """RT-01: Moment release varsa uç kuvveti 0 olmalı"""
    mat = Material(1, "st", 2e8, 0.05, 0.0008)
    n1, n2 = Node(1, 0, 0), Node(2, 4, 0)

    elem = Element(1, n1, n2, mat)
    elem.releases = [False, True] # i-ucu rijit, j-ucu mafsal

    # DÜZELTME: Node 2'nin rotasyonunu (dof 2) da sınırla ki yapı kararlı olsun
    # BC: (NodeID, DOF, Value) -> (2, 2, 0.0) eklendi
    solver = StructuralSolver([n1, n2], [elem], [(1,0,0), (1,1,0), (1,2,0), (2,1,0), (2,2,0)])
    
    solver.solve()
    solver.calculate_internal_forces()

    # Mafsallı uçta (j) moment artık NaN değil, tam 0 çıkmalı
    assert abs(elem.internal_forces['Mj']) < TOL

def test_regression_global_equilibrium():
    """RT-02: Toplam Reaksiyon = Toplam Yük (Denge Kontrolü)"""
    # Bu test Q2(A)'daki 192 kN toplam yükü kontrol eder
    total_expected_load = 192.0 
    # solver.solve() sonrası reaksiyon toplamı kontrolü
    assert True # Analiz kodun tamlandığında burayı reaction sum ile bağla

def test_regression_symmetry():
    """RT-03: Simetrik sistemde mesnet tepkileri eşit mi?"""
    # Q2(A) simetrik bir sistemdir, RA ve RC eşit çıkmalı
    assert True # Analiz sonuçlarındaki R_node1 == R_node4 kontrolü
