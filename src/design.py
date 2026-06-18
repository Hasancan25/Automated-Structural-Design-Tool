import numpy as np

class AISCSteelDesigner:
    """
    AISC 360-16 (Çelik Yapıların Tasarım Yönetmeliği) standartlarına göre 
    çubuk elemanların narinlik, burkulma ve kapasite etkileşim tahkiklerini 
    tamamen nesne tabanlı yürüten Çelik Tasarım Motoru sınıfı.
    """
    def __init__(self, Fy=275000.0, E=2.0e8, phi_c=0.90, phi_b=0.90):
        self.Fy = Fy          # Çelik akma dayanımı (kPa - SI Entegrasyonu)
        self.E = E            # Çelik elastisite modülü (kPa)
        self.phi_c = phi_c    # Basınç/Eksenel emniyet katsayısı (AISC Chapter E)
        self.phi_b = phi_b    # Eğilme/Moment emniyet katsayısı (AISC Chapter F)

    def calculate_dc_ratio(self, elem, uc):
        """
        Belirtilen eleman ucu ('i' veya 'j') için AISC Chapter H1-1 
        etkileşim (Kapasite/Zorlanma - D/C) oranını bağımsız hesaplar.
        """
        f = getattr(elem, 'internal_forces', None)
        if not f:
            return 0.0

        # Eleman geometrik ve mekanik nesne özniteliklerini oku
        L = elem.get_length()
        A = elem.material.A
        I = elem.material.I
        Z = getattr(elem, 'section_Z', 0.0)

        if A <= 0 or I <= 0:
            return 0.0

        # 1. NARİNLİK VE KRİTİK BURKULMA GERİLMESİ HESABI (AISC Chapter E)
        r = np.sqrt(I / A)
        slenderness = L / r
        
        # Euler burkulma gerilmesi (Fe)
        Fe = (np.pi**2 * self.E) / (slenderness**2) if slenderness > 0 else 1.0e10
        lambda_lim = 4.71 * np.sqrt(self.E / self.Fy)
        
        # Kritik burkulma gerilmesi (Fcr)
        Fcr = (0.658**(self.Fy / Fe)) * self.Fy if slenderness <= lambda_lim else 0.877 * Fe

        # 2. UÇ KUVVETLERİNİN AYRIŞTIRILMASI
        N_force = f['N' + uc]
        Pu = abs(N_force)
        Mu = abs(f['M' + uc])

        # 3. NOMİNAL EKSENEL KAPASİTE HESABI (Pn)
        if N_force < 0:
            # Eleman basınçta ise burkulma tahkiki (AISC Chapter E)
            Pn = Fcr * A
        else:
            # Eleman çekmede ise akma tahkiki (AISC Chapter D)
            Pn = self.Fy * A

        # 4. NOMİNAL EĞİLME MOMENTİ KAPASİTE HESABI (Mn - AISC Chapter F)
        Mn = self.Fy * Z

        if Pn <= 0 or Mn <= 0:
            return 0.0

        # 5. AISC H1-1 ETKİLEŞİM DENKLEM SETLERİ (Chapter H)
        ratio_P = Pu / (self.phi_c * Pn)
        ratio_M = Mu / (self.phi_b * Mn)

        if ratio_P >= 0.2:
            # Baskın eksenel yük denklemi (AISC Eq. H1-1a)
            dc = ratio_P + (8.0 / 9.0) * ratio_M
        else:
            # Baskın eğilme momenti denklemi (AISC Eq. H1-1b)
            dc = (ratio_P / 2.0) + ratio_M

        return dc
