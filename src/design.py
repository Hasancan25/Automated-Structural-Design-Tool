import numpy as np

class DesignChecker:
    """AISC 360-16 Standartlarına Göre Çelik Eleman Tasarım ve Kapasite Kontrol Modülü."""
    
    def __init__(self, phi_b=0.90, phi_c=0.90):
        self.phi_b = phi_b  # Eğilme için LRFD dayanım azaltma katsayısı
        self.phi_c = phi_c  # Aksiyel (Çekme/Basınç) için LRFD dayanım azaltma katsayısı

    def compute_member_dc(self, elem):
        """
        Tek bir elemanın i ve j uçlarındaki AISC 360-16 Demand/Capacity (D/C) 
        oranlarını LRFD etkileşim denklemlerini kullanarak hesaplar.
        """
        # Elemanın malzeme özelliklerini güvenli bir şekilde oku (main.py'de elem.material altına yazılıyor)
        Fy = getattr(elem.material, 'Fy', 250000.0)  # Varsayılan Akma Gerilmesi: 250 MPa (kN/m2)
        A = getattr(elem.material, 'A', 0.01)        # Kesit Alanı (m2)
        I = getattr(elem.material, 'I', 1e-4)        # Atalet Momenti (m4)
        
        # KRİTİK GÜNCELLEME: main.py kesit derinliğini direkt eleman (elem) üzerine 'section_d' olarak basıyor
        d = getattr(elem, 'section_d', 0.3)          # Profil Derinliği (m)
        
        # KRİTİK GÜNCELLEME: Plastik mukavemet momenti direkt eleman üzerindeki 'section_Z' niteliğinden okunur
        if hasattr(elem, 'section_Z') and elem.section_Z is not None:
            Z = elem.section_Z
        else:
            S = (2.0 * I) / d if d > 0 else 1e-4
            Z = 1.15 * S  # Şekil faktörü yaklaşımı (Shape factor ~ 1.15)

        # LRFD Nominal Dayanımların Hesaplanması
        Pn = Fy * A  # Nominal eksenel kapasite
        Mn = Fy * Z  # Nominal eğilme momenti kapasitesi
        
        phi_Pn = self.phi_c * Pn
        phi_Mn = self.phi_b * Mn

        # Solver tarafından hesaplanan iç kuvvetleri kontrol et
        forces = getattr(elem, 'internal_forces', None)
        if not forces:
            return {'i': {'dc': 0.0}, 'j': {'dc': 0.0}}

        # i-Ucu (Eleman Başlangıcı) Etkileşim Kontrolü
        Pu_i = abs(forces['Ni'])
        Mu_i = abs(forces['Mi'])
        dc_i = self._aisc_interaction(Pu_i, Mu_i, phi_Pn, phi_Mn)

        # j-Ucu (Eleman Bitişi) Etkileşim Kontrolü
        Pu_j = abs(forces['Nj'])
        Mu_j = abs(forces['Mj'])
        dc_j = self._aisc_interaction(Pu_j, Mu_j, phi_Pn, phi_Mn)

        return {
            'i': {'dc': round(dc_i, 4)},
            'j': {'dc': round(dc_j, 4)}
        }

    def _aisc_interaction(self, Pu, Mu, phi_Pn, phi_Mn):
        """AISC 360-16 H1.1 Eksenel Kuvvet ve Eğilme Momenti Etkileşim Formülleri"""
        if phi_Pn == 0 or phi_Mn == 0:
            return 0.0
        
        axial_ratio = Pu / phi_Pn
        
        # AISC Denklem H1-1a ve H1-1b Sınır Kontrolü
        if axial_ratio >= 0.2:
            dc = axial_ratio + (8.0 / 9.0) * (Mu / phi_Mn)
        else:
            dc = (axial_ratio / 2.0) + (Mu / phi_Mn)
            
        return dc

    def check_all_elements(self, elements):
        """
        Sistemdeki tüm elemanları tarar ve visualization.py ile tam uyumlu
        bir kapasite zarfı (envelope_results) sözlüğü döndürür.
        """
        envelope_results = {}
        for elem in elements:
            envelope_results[elem.id] = self.compute_member_dc(elem)
        return envelope_results
