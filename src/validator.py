# src/validator.py
from pydantic import BaseModel, ValidationError, Field
from typing import List, Optional, Dict

# Düğüm tanımları
class Node(BaseModel):
    id: int
    x: float
    y: float

# Eleman tanımları
class Element(BaseModel):
    id: int
    node_i: int
    node_j: int
    load_patterns: Optional[Dict[str, float]] = Field(default_factory=dict)

# Düğüm yükleri
class NodalLoad(BaseModel):
    node_id: int
    fx: float = 0.0
    fy: float = 0.0
    mz: float = 0.0
    load_patterns: Optional[Dict[str, float]] = Field(default_factory=dict)

# Ana şema: input.json dosyasının tüm yapısı
class StructuralInput(BaseModel):
    nodes: List[Node]
    elements: List[Element]
    nodal_loads: Optional[List[NodalLoad]] = []

def validate_input(json_data: dict) -> bool:
    """
    input.json dosyasını şemaya göre doğrular. 
    Hata varsa hangi alanda olduğunu detaylı raporlar.
    """
    try:
        StructuralInput(**json_data)
        print(" [✓] Input verisi doğrulandı, analiz başlatılıyor...")
        return True
    except ValidationError as e:
        print(f"\n" + "!"*50)
        print(" [!] GİRDİ HATASI (input.json):")
        # Hataları daha okunaklı döküyoruz
        for error in e.errors():
            loc = " -> ".join([str(l) for l in error['loc']])
            msg = error['msg']
            print(f"    - Konum: {loc} | Hata: {msg}")
        print("!"*50 + "\n")
        return False
