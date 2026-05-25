import re

def standardize_section_name(name):
    """Kullanıcının yazdığı HEA300, HEB200 gibi isimleri veri tabanındaki HE300A, HE200B formatına dönüştürür."""
    if not isinstance(name, str):
        return name
    name = name.upper().replace(" ", "")
    match = re.match(r'HE([ABM])(\d+)', name)
    if match:
        suffix, num = match.groups()
        return f"HE{num}{suffix}"
    return name

class CrossSection:
    def __init__(self, name, area=0.0, moment_of_inertia=0.0, plastic_modulus=0.0, depth=0.0):
        self.name = name
        self.A = area
        self.I = moment_of_inertia
        self.Z = plastic_modulus
        self.d = depth

class SectionFactory:
    """Hadde ve Yapma kesitlerin üretimini OOP felsefesiyle tek merkezden yönetir."""
    @staticmethod
    def create_section(name, section_db, built_up_db):
        name_upper = name.upper().replace(" ", "")
        
        # 1. Senaryo: Yapma Kesit Tanımlaması (Built-Up)
        if name_upper in built_up_db or name_upper.startswith("BU"):
            if name_upper in built_up_db:
                props = built_up_db[name_upper]
                bf1 = float(props['bf1'])
                tf1 = float(props['tf1'])
                tw  = float(props['tw'])
                hw  = float(props['hw'])
                bf2 = float(props['bf2'])
                tf2 = float(props['tf2'])
            else:
                match = re.match(r'BU_?(\d+)X(\d+)X(\d+)X(\d+)X(\d+)X(\d+)', name_upper)
                if match:
                    bf1, tf1, tw, hw, bf2, tf2 = map(float, match.groups())
                else:
                    # Formata uymuyorsa güvenli varsayılan hadde profil parametresi döndürür
                    return CrossSection(name, 2.85e-3, 1.943e-5, 2.21e-4, 0.200)

            # Milimetreden Metreye Çevrim (SI Entegrasyonu)
            bf1 /= 1000.0; tf1 /= 1000.0; tw /= 1000.0; hw /= 1000.0; bf2 /= 1000.0; tf2 /= 1000.0
            
            d = tf1 + hw + tf2
            A = (bf1 * tf1) + (hw * tw) + (bf2 * tf2)
            
            # Elastik Nötr Eksen (Ağırlık Merkezi)
            y_bar = ((bf1 * tf1) * (tf2 + hw + tf1 / 2.0) + (hw * tw) * (tf2 + hw / 2.0) + (bf2 * tf2) * (tf2 / 2.0)) / A
            
            # Atalet Momenti (Ix) -> Paralel Eksen Teoremi
            I_top = (bf1 * tf1**3) / 12.0 + (bf1 * tf1) * (tf2 + hw + tf1 / 2.0 - y_bar)**2
            I_web = (tw * hw**3) / 12.0 + (hw * tw) * (tf2 + hw / 2.0 - y_bar)**2
            I_bot = (bf2 * tf2**3) / 12.0 + (bf2 * tf2) * (tf2 / 2.0 - y_bar)**2
            I = I_top + I_web + I_bot
            
            # Plastik Nötr Eksen (PNA) Konumu
            half_A = A / 2.0
            if (bf2 * tf2) >= half_A:
                y_pna = half_A / bf2
            elif ((bf2 * tf2) + (hw * tw)) >= half_A:
                y_pna = tf2 + (half_A - (bf2 * tf2)) / tw
            else:
                y_pna = tf2 + hw + (half_A - (bf2 * tf2) - (hw * tw)) / bf1
                
            # Plastik Mukavemet Momenti (Zx) -> Dilim Entegrasyonu
            rectangles = [(0.0, tf2, bf2), (tf2, tf2 + hw, tw), (tf2 + hw, tf2 + hw + tf1, bf1)]
            Z = 0.0
            for y_l, y_h, w in rectangles:
                if y_h <= y_pna:
                    Z += (y_h - y_l) * w * abs(((y_l + y_h) / 2.0) - y_pna)
                elif y_l >= y_pna:
                    Z += (y_h - y_l) * w * abs(((y_l + y_h) / 2.0) - y_pna)
                else:
                    Z += (y_pna - y_l) * w * abs(((y_l + y_pna) / 2.0) - y_pna)
                    Z += (y_h - y_pna) * w * abs(((y_pna + y_h) / 2.0) - y_pna)
            
            # Nesneyi paketleyip fırlatır
            return CrossSection(name=name, area=A, moment_of_inertia=I, plastic_modulus=Z, depth=d)
            
        # 2. Senaryo: Standart Hadde Profil (sections_db.json)
        else:
            std_name = standardize_section_name(name_upper)
            props = section_db.get(std_name, {"A": 2.85e-3, "I": 1.943e-5, "Z": 2.21e-4, "d": 0.200})
            return CrossSection(name=name, area=props["A"], moment_of_inertia=props["I"], plastic_modulus=props["Z"], depth=props["d"])
