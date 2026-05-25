class LoadCombination:
    """Tek bir yük kombinasyon senaryosunu ve katsayı matrisini temsil eden OOP sınıfı."""
    def __init__(self, name, factors):
        self.name = name
        self.factors = factors  # {"DEAD": 1.2, "LIVE": 1.6, "WIND": 1.0, ...}

    def get_equation(self):
        """Katsayısı 0.0 olmayan yük tiplerini '1.2*DEAD + 1.6*LIVE' formatında dinamik döner."""
        equation_parts = [f"{v}*{k}" for k, v in self.factors.items() if v != 0.0]
        return " + ".join(equation_parts) if equation_parts else "0.0"


class EnvelopeManager:
    """100+ kombinasyonun analiz ve tasarım sonuçlarını tarayıp en kritik durumları bulan zarf motoru."""
    def __init__(self):
        self.envelope_results = {}
        self.combo_summaries = {}
        self.abs_max_u = 0.0
        self.abs_critical_combo = "Belirlenmedi"
        self.max_overall_dc = 0.0
        self.max_dc_combo = "Belirlenmedi"
        self.drift_warning_global = False
        
        # --- KRİTİK GÜNCELLEME: KAT BAZLI KUMULATİF ZARF MATRİSLERİ ---
        self.drift_envelope = {}  # Kat kat en kötü durumları biriktireceğimiz hafıza sözlüğü
        self.global_last_drift_results = []  # main.py ve PDF tablosuyla %100 uyumlu nihai sıralı liste

    def initialize_combo_summary(self, combo_name, max_u, max_theta, drift_warning, drift_results, factors):
        """Her kombinasyon çözüldüğünde deplasman ve kat drift özetlerini nesneye işler."""
        # 1. Global maksimum deplasman (yanal ötelenme) kontrolü
        if max_u > self.abs_max_u:
            self.abs_max_u = max_u
            self.abs_critical_combo = combo_name

        # 2. Global drift uyarı bayrağı takibi (Herhangi bir kombide aşım varsa True kalır)
        if drift_warning:
            self.drift_warning_global = True

        # --- 3. AKILLI KAT BAZLI DRIFT ZARF ALGORİTMASI ---
        for d in drift_results:
            s_id = d['story']
            # Eğer bu kat hafızada yoksa, ilk kombinasyon verisiyle ilklendir
            if s_id not in self.drift_envelope:
                self.drift_envelope[s_id] = {
                    'story': s_id,
                    'h': d['h'],
                    'delta': d['delta'],
                    'theta': d['theta'],
                    'status': d['status'],
                    'governing_combo': combo_name  # Jüride 'Bu katı hangi kombi patlattı?' derlerse elimizde dursun
                }
            else:
                # Eğer bu kombinasyondaki kat arası drift oranı (theta), zarftaki mevcut maksimumdan büyükse güncelle!
                if d['theta'] > self.drift_envelope[s_id]['theta']:
                    self.drift_envelope[s_id]['delta'] = d['delta']
                    self.drift_envelope[s_id]['theta'] = d['theta']
                    self.drift_envelope[s_id]['status'] = d['status']
                    self.drift_envelope[s_id]['governing_combo'] = combo_name

        # PDF tablosuna kat matrisini (1. kattan 22. kata kadar) kusursuz sırada beslemek için sıralayıp listeye döküyoruz
        self.global_last_drift_results = [self.drift_envelope[k] for k in sorted(self.drift_envelope.keys())]

        # Kombinasyon genel özet sözlüğünü ilk değerlerle doldur
        self.combo_summaries[combo_name] = {
            "max_u": max_u,
            "max_drift": max_theta,
            "drift_status": "LIMIT ASILDI" if drift_warning else "GUVENLI",
            "drift_warning": drift_warning,
            "design_warning": False,  # Eleman kontrollerinde tetiklenecek
            "factors": factors
        }

    def update_element_envelope(self, combo_name, elem_id, type_str, uc, N, V, M, dc):
        """Elemanların uç noktalarındaki D/C oranlarını karşılaştırarak mukavemet zarfını (envelope) günceller."""
        if elem_id not in self.envelope_results:
            self.envelope_results[elem_id] = {
                "i": {"dc": -1.0, "combo": "Belirlenmedi", "status": "GUVENLI"},
                "j": {"dc": -1.0, "combo": "Belirlenmedi", "status": "GUVENLI"}
            }

        # Eğer bu kombinasyondaki zorlanma (dc), zarftaki mevcut değerden büyükse zarfı güncelle
        if dc > self.envelope_results[elem_id][uc]["dc"]:
            self.envelope_results[elem_id][uc] = {
                "type": type_str,
                "N": N, "V": V, "M": M,
                "dc": dc,
                "combo": combo_name,
                "status": "LIMIT ASILDI" if dc > 1.0 else "GUVENLI"
            }

        # 100 kombinasyon arasından çerçevenin kaderini belirleyen en kritik mukavemet liderini bul
        if dc > self.max_overall_dc:
            self.max_overall_dc = dc
            self.max_dc_combo = combo_name

        # Eğer eleman kapasiteyi aştıysa, ilgili kombinasyonun tasarımını 'uyarılı' konuma getir
        if dc > 1.0:
            self.combo_summaries[combo_name]["design_warning"] = True
