import os
import json
import numpy as np
import traceback
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from src.io_handler import IOHandler
from src.solver import StructuralSolver
from src.effects import MemberLoadEffect
import re
from src.section import SectionFactory
from src.load_combination import LoadCombination, EnvelopeManager
from src.design import DesignChecker  # GÜNCELLEME: Yeni OOP Tasarım Motoru Bağlantısı
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Konsoldaki FPDF kütüphanesi uyarı kirliliğini engellemek için filtre (Ürün kalitesi için)
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

def standardize_section_name(name):
    """Kullanıcının yazdığı HEA300, HEB200 gibi isimleri veri tabanındaki HE300A, HE200B formatına dönüştürür."""
    if not isinstance(name, str):
        return name
    name = name.upper().replace(" ", "")
    # HEA300 -> HE300A | HEB200 -> HE200B | HEM200 -> HE200M dönüşümü yapar
    match = re.match(r'HE([ABM])(\d+)', name)
    if match:
        suffix, num = match.groups()
        return f"HE{num}{suffix}"
    return name

def tr_clean(text):
    """FPDF standart fontlarının patlamaması için Türkçe karakterleri Latin muadillerine çevirir."""
    if not isinstance(text, str):
        return text
    tr_map = {
        'Ğ': 'G', 'ğ': 'g', 'Ş': 'S', 'ş': 's', 'İ': 'I', 'ı': 'i',
        'Ç': 'C', 'ç': 'c', 'Ö': 'O', 'ö': 'o', 'Ü': 'U', 'ü': 'u'
    }
    for tr_char, lat_char in tr_map.items():
        text = text.replace(tr_char, lat_char)
    return text

def calculate_built_up_properties(name, built_up_db):
    """
    Built-up kesit özelliklerini tamamen dinamik ve parametrik olarak hesaplar.
    1. Yol: Önce built_up_db.json içindeki kurumsal anahtarlara bakar (Örn: BU_KOLON_AĞIR).
    2. Yol: Bulamazsa doğrudan "BU_350X20X12X600X400X25" ham metin formatını havada ayrıştırır.
    İçerisinde hiçbir sabit (hardcoded) sihirli varsayılan ölçü barındırmaz.
    """
    name = name.upper().replace(" ", "")
    
    # 1. YOL: built_up_db.json kütüphanesinde tam eşleşme arama
    if name in built_up_db:
        props = built_up_db[name]
        bf1 = float(props['bf1'])
        tf1 = float(props['tf1'])
        tw  = float(props['tw'])
        hw  = float(props['hw'])
        bf2 = float(props['bf2'])
        tf2 = float(props['tf2'])
    else:
        # 2. YOL: Doğrudan ham parametrik metin ayrıştırma (Örn: BU_350X20X12X600X400X25)
        match = re.match(r'BU_?(\d+)X(\d+)X(\d+)X(\d+)X(\d+)X(\d+)', name)
        if match:
            bf1, tf1, tw, hw, bf2, tf2 = map(float, match.groups())
        else:
            return None # Yapma profil değilse veya formata uymuyorsa çözücüye pasla (Hadde profil kontrolü için)
    
    # Metre cinsine dönüştür (SI Entegrasyonu)
    bf1 /= 1000.0
    tf1 /= 1000.0
    tw  /= 1000.0
    hw  /= 1000.0
    bf2 /= 1000.0
    tf2 /= 1000.0
    
    d = tf1 + hw + tf2  # Toplam kesit derinliği
    
    # Bileşen Alanları
    A_top = bf1 * tf1
    A_web = hw * tw
    A_bot = bf2 * tf2
    A = A_top + A_web + A_bot
    
    # Elemanların tabandan (y=0) yerel ağırlık merkezleri
    y_bot = tf2 / 2.0
    y_web = tf2 + hw / 2.0
    y_top = tf2 + hw + tf1 / 2.0
    
    # Yapının Ağırlık Merkezi (Tarafsız Eksen)
    y_bar = (A_top * y_top + A_web * y_web + A_bot * y_bot) / A
    
    # Atalet Momenti (Ix) -> Asimetrik Paralel Eksen Teoremi Çekirdeği
    I_top = (bf1 * tf1**3) / 12.0 + A_top * (y_top - y_bar)**2
    I_web = (tw * hw**3) / 12.0 + A_web * (y_web - y_bar)**2
    I_bot = (bf2 * tf2**3) / 12.0 + A_bot * (y_bot - y_bar)**2
    I = I_top + I_web + I_bot
    
    # Plastik Nötr Eksen (PNA) Konumu (Alanın tam ikiye bölündüğü yer: A/2)
    half_A = A / 2.0
    if A_bot >= half_A:
        y_pna = half_A / bf2
    elif (A_bot + A_web) >= half_A:
        y_pna = tf2 + (half_A - A_bot) / tw
    else:
        y_pna = tf2 + hw + (half_A - A_bot - A_web) / bf1
        
    # Plastik Mukavemet Momenti (Zx) -> AISC Moment Kapasite Hesabı İçin Dilim Entegrasyonu
    rectangles = [
        (0.0, tf2, bf2),                # Alt Flanş
        (tf2, tf2 + hw, tw),            # Gövde (Web)
        (tf2 + hw, tf2 + hw + tf1, bf1) # Üst Flanş
    ]
    
    Z = 0.0
    for y_l, y_h, w in rectangles:
        if y_h <= y_pna:  # PNA'in tamamen altında
            Z += (y_h - y_l) * w * abs(((y_l + y_h) / 2.0) - y_pna)
        elif y_l >= y_pna:  # PNA'in tamamen üstünde
            Z += (y_h - y_l) * w * abs(((y_l + y_h) / 2.0) - y_pna)
        else:  # PNA kesiti bölüyor
            Z += (y_pna - y_l) * w * abs(((y_l + y_pna) / 2.0) - y_pna)
            Z += (y_h - y_pna) * w * abs(((pypna + y_h) / 2.0) - y_pna)
            
    return {"A": A, "I": I, "Z": Z, "d": d}

def export_results(nodes, elements, envelope_results, combo_summaries, config_info):
    """Her eleman için en kritik senaryoyu (Zarf) içeren detaylı raporlar üretir."""
    print("\n" + "="*50)
    print(" [+] DETAYLI RAPORLAMA BAŞLATILDI ".center(50, "="))
    
    # Tüm düğüm verilerini hazırla (Ondalık ayraç: virgül)
    node_list = []
    for node in nodes:
        node_list.append([
            str(node.id),
            f"{getattr(node, 'u', 0.0):.8f}".replace('.', ','),
            f"{getattr(node, 'v', 0.0):.8f}".replace('.', ','),
            f"{getattr(node, 'rz', 0.0):.8f}".replace('.', ',')
        ])

    # --- 1. EXCEL EXPORT (Zarf Sonuçları) ---
    excel_path = "Analiz_Raporu.xlsx"
    try:
        df_n = pd.DataFrame(node_list, columns=["Node ID", "u (X) [m]", "v (Y) [m]", "rz (Rot) [rad]"])
        
        flat_elem_list = []
        for e_id in sorted(envelope_results.keys()):
            for uc in ["i", "j"]:
                res = envelope_results[e_id][uc]
                flat_elem_list.append([
                    str(e_id), res['type'], uc, res['N'], res['V'], res['M'], res['dc'], res['combo'], res['status']
                ])
                
        df_e = pd.DataFrame(flat_elem_list, columns=["Elem ID", "Tip", "Uc", "Axial (kN)", "Shear (kN)", "Moment (kNm)", "D/C Ratio", "Governing Combo", "Status"])
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df_n.to_excel(writer, sheet_name='Deplasmanlar', index=False)
            df_e.to_excel(writer, sheet_name='AISC_Zarf_Tasarim', index=False)
        print(f" [✓] Excel Raporu (Eksiksiz Zarf): {excel_path}")
    except Exception as e:
        print(f" [!] Excel Yazma Hatasi: {e}")

    # --- 2. PDF EXPORT ---
    pdf_path = "Analiz_Raporu.pdf"
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Başlık Bölümü
        pdf.set_font("Times", "B", 20)
        pdf.set_text_color(0, 0, 0) # Tam Siyah
        pdf.cell(0, 20, "YAPISAL ANALIZ RAPORU", ln=True, align="C", border=1)
        
        # Yapı Özeti
        pdf.ln(10)
        pdf.set_font("Times", "B", 12)
        pdf.cell(0, 8, f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True)
        
        status = "CAPRAZLI (Braced)" if config_info.get('has_bracing') else "CAPRAZSIZ (Moment Frame)"
        pdf.cell(0, 8, f"Yapi Tipi: {status}", ln=True)
        
        clean_col = tr_clean(str(config_info.get('column_section', 'Belirtilmedi')))
        clean_beam = tr_clean(str(config_info.get('beam_section', 'Belirtilmedi')))
        pdf.cell(0, 8, f"Secilen Kolon Profili: {clean_col}", ln=True)
        pdf.cell(0, 8, f"Secilen Kiris Profili: {clean_beam}", ln=True)
        
        # --- 100+ KOMBİNASYON İÇİN GLOBAL KRİTİK GOVERNING SENARYO TARAYICISI ---
        abs_max_u = 0.0
        abs_critical_combo = "Belirlenmedi"
        any_drift_warning = False
        any_strength_warning = False
        
        for c_name, summary in combo_summaries.items():
            if summary['max_u'] > abs_max_u:
                abs_max_u = summary['max_u']
                abs_critical_combo = c_name
            if summary['drift_warning']: any_drift_warning = True
            if summary['design_warning']: any_strength_warning = True

        max_overall_dc = 0.0
        max_dc_combo = "Belirlenmedi"
        for e_id, uces in envelope_results.items():
            for uc in ["i", "j"]:
                if uces[uc]["dc"] > max_overall_dc:
                    max_overall_dc = uces[uc]["dc"]
                    max_dc_combo = uces[uc]["combo"]

        # --- DİNAMİK YÜK KOMBİNASYONU (DENKLEM) GÖSTERİM BÖLÜMÜ (SADECE KRİTİKLER FİLTRELENDİ) ---
        pdf.ln(5)
        pdf.set_font("Times", "B", 13)
        pdf.cell(0, 8, "Kritik Yuk Kombinasyonlari (Critical Load Combinations):", ln=True)
        pdf.set_font("Times", "", 10)
        
        # Deplasman lider kombinasyonunun matematiksel denklemini dök
        if abs_critical_combo in combo_summaries:
            f_dict = combo_summaries[abs_critical_combo].get('factors', {})
            f_equation = " + ".join([f"{v}*{k}" for k, v in f_dict.items() if v != 0.0])
            if not f_equation: f_equation = "0.0"
            pdf.cell(0, 6, f" > [Deplasman Kritik] {tr_clean(abs_critical_combo)} = {tr_clean(f_equation)}", ln=True)
            
        # Mukavemet lider kombinasyonunun matematiksel denklemini dök (Eğer deplasman liderinden farklıysa)
        if max_dc_combo in combo_summaries and max_dc_combo != abs_critical_combo:
            f_dict = combo_summaries[max_dc_combo].get('factors', {})
            f_equation = " + ".join([f"{v}*{k}" for k, v in f_dict.items() if v != 0.0])
            if not f_equation: f_equation = "0.0"
            pdf.cell(0, 6, f" > [Mukavemet Kritik] {tr_clean(max_dc_combo)} = {tr_clean(f_equation)}", ln=True)

        pdf.ln(5)
        pdf.set_font("Times", "B", 12)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(0, 10, f" KRITIK YONETEN SENARYO (Maksimum Deplasman): {tr_clean(abs_critical_combo)}", ln=True, border=1, fill=True)
        pdf.cell(0, 10, f" KRITIK YONETEN SENARYO (Maksimum Kesit Mukavemeti): {tr_clean(max_dc_combo)} (Max D/C: {max_overall_dc:.3f})", ln=True, border=1, fill=True)
        pdf.cell(0, 10, f" KUMULATIF MAKSIMUM DEPLASMAN: {abs_max_u:.6e} m", ln=True, border=1)
        
        # GÖRELİ ÖTELENME GLOBAL BAŞARI/UYARI BANNERI
        pdf.ln(2)
        if any_drift_warning:
            pdf.set_fill_color(255, 230, 230) 
            pdf.set_text_color(180, 0, 0)
            pdf.set_font("Times", "B", 12)
            pdf.cell(0, 10, tr_clean(" UYARI: KRITIK KATLARDA GORELI OTELENME SINIRI ASILDI! (Theta > 0.008)"), ln=True, border=1, fill=True)
        else:
            pdf.set_fill_color(230, 245, 230) 
            pdf.set_text_color(0, 120, 0)
            pdf.set_font("Times", "B", 12)
            pdf.cell(0, 10, tr_clean(" SINIR DEGER KONTROLU: Tum Katlarda Yanal Salinimlar Guvenli Sinirlar Icinde."), ln=True, border=1, fill=True)
            
        # AISC 360 MUKAVEMET KAPASİTE GLOBAL BANNERI
        pdf.ln(1)
        if any_strength_warning:
            pdf.set_fill_color(255, 210, 210) 
            pdf.set_text_color(150, 0, 0)
            pdf.set_font("Times", "B", 12)
            pdf.cell(0, 10, tr_clean(" UYARI: BAZI ELEMANLARDA AISC 360 MUKAVEMET KAPASITESI ASILDI! (D/C > 1,00)"), ln=True, border=1, fill=True)
        else:
            pdf.set_fill_color(210, 255, 210) 
            pdf.set_text_color(0, 100, 0)
            pdf.set_font("Times", "B", 12)
            pdf.cell(0, 10, tr_clean(" KESIT MUKAVEMETI: Tum Elemanlar AISC 360 Standartlarina Gore Emniyetlidir."), ln=True, border=1, fill=True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.set_font("Times", "I", 10)
        pdf.cell(0, 8, f"Istatistik: {len(nodes)} Dugum | {len(elements)} Eleman", ln=True)

        # GÖRELİ KAT ÖTELENMELERİ TABLOSU
        pdf.ln(8)
        pdf.set_font("Times", "B", 14)
        pdf.cell(0, 10, tr_clean("Goreli Kat Otelenmesi Kontrolleri (TBDY 2018 / ASCE 7)"), ln=True)
        
        pdf.set_font("Times", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(15, 8, "Kat", 1, 0, 'C', True)
        pdf.cell(35, 8, tr_clean("Kat Yuksekligi [m]"), 1, 0, 'C', True)
        pdf.cell(45, 8, tr_clean("Kat Arasi Fark [m]"), 1, 0, 'C', True)
        pdf.cell(45, 8, tr_clean("Drift Orani (Theta)"), 1, 0, 'C', True)
        pdf.cell(45, 8, tr_clean("Durum (Limit: 0.008)"), 1, 1, 'C', True)
        
        pdf.set_font("Times", "", 10)
        for d in config_info.get('drift_results', []):
            pdf.cell(15, 6, str(d['story']), 1, 0, 'C')
            pdf.cell(35, 6, f"{d['h']:.2f}".replace('.', ','), 1, 0, 'C')
            pdf.cell(45, 6, f"{d['delta']:.5f}".replace('.', ','), 1, 0, 'C')
            pdf.cell(45, 6, f"{d['theta']:.6f}".replace('.', ','), 1, 0, 'C')
            
            if d['status'] == "LIMIT ASILDI":
                pdf.set_text_color(180, 0, 0)
                pdf.set_font("Times", "B", 10)
            else:
                pdf.set_text_color(0, 100, 0)
                pdf.set_font("Times", "", 10)
                
            pdf.cell(45, 6, tr_clean(d['status']), 1, 1, 'C')
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Times", "", 10)

        # DÜĞÜM DEPLASMANLARI TABLOSU
        pdf.ln(10)
        pdf.set_font("Times", "B", 14)
        pdf.cell(0, 10, tr_clean("Dugum Deplasman Sonuclari"), ln=True)
        
        pdf.set_font("Times", "B", 11)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(20, 8, "Node", 1, 0, 'C', True)
        pdf.cell(55, 8, "u (X) [m]", 1, 0, 'C', True)
        pdf.cell(55, 8, "v (Y) [m]", 1, 0, 'C', True)
        pdf.cell(55, 8, "rz (Rot) [rad]", 1, 1, 'C', True)
        
        pdf.set_font("Times", "", 11)
        for row in node_list:
            pdf.cell(20, 7, row[0], 1, 0, 'C')
            pdf.cell(55, 7, row[1], 1, 0, 'C')
            pdf.cell(55, 7, row[2], 1, 0, 'C')
            pdf.cell(55, 7, row[3], 1, 1, 'C')

        # --- KAPSAMLI ELEMAN TABLOSU ---
        pdf.ln(15)
        pdf.set_font("Times", "B", 14)
        pdf.cell(0, 10, tr_clean("Eleman Zarf Ic Kuvvet ve AISC 360-16 Tasarim Sonuclari"), ln=True)
        
        pdf.set_font("Times", "B", 9)
        pdf.set_fill_color(200, 220, 240) 
        pdf.cell(10, 8, "ID", 1, 0, 'C', True)
        pdf.cell(32, 8, tr_clean("Tip (Profil)"), 1, 0, 'C', True)
        pdf.cell(8,  8, "Uc", 1, 0, 'C', True)
        pdf.cell(22, 8, "Axial(kN)", 1, 0, 'C', True)
        pdf.cell(22, 8, "Shear(kN)", 1, 0, 'C', True)
        pdf.cell(22, 8, "Moment(kNm)", 1, 0, 'C', True)
        pdf.cell(18, 8, "Max D/C", 1, 0, 'C', True) 
        pdf.cell(31, 8, "Yoneten Komb.", 1, 0, 'C', True)
        pdf.cell(20, 8, "Durum", 1, 1, 'C', True)    
        
        pdf.set_font("Times", "", 8)
        for e_id in sorted(envelope_results.keys()):
            for uc in ["i", "j"]:
                res = envelope_results[e_id][uc]
                pdf.cell(10, 6, str(e_id), 1, 0, 'C')
                pdf.cell(32, 6, tr_clean(res['type']), 1, 0, 'L')
                pdf.cell(8,  6, uc, 1, 0, 'C')
                pdf.cell(22, 6, f"{res['N']:.2f}".replace('.', ','), 1, 0, 'R')
                pdf.cell(22, 6, f"{res['V']:.2f}".replace('.', ','), 1, 0, 'R')
                pdf.cell(22, 6, f"{res['M']:.2f}".replace('.', ','), 1, 0, 'R')
                pdf.cell(18, 6, f"{res['dc']:.3f}".replace('.', ','), 1, 0, 'C')
                pdf.cell(31, 6, tr_clean(res['combo']), 1, 0, 'C')
                
                if res['dc'] > 1.0:
                    pdf.set_text_color(180, 0, 0)
                    pdf.set_font("Times", "B", 8)
                else:
                    pdf.set_text_color(0, 100, 0)
                    pdf.set_font("Times", "", 8)
                    
                pdf.cell(20, 6, tr_clean(res['status']), 1, 1, 'C')
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Times", "", 8)

        pdf.output(pdf_path)
        print(f" [✓] PDF Zarf Raporu (Farkli Kombinasyon Süzgeçli): {pdf_path}")
    except Exception as e:
        print(f" [!] PDF Yazma Hatasi (Dosya acik olabilir): {e}")

    print("="*50)

class StructuralVisualizer:
    @staticmethod
    def plot_deformed_shape(nodes, elements, config, scale=30.0, total_width=0.0, total_height=0.0):
        plt.rcParams['font.family'] = 'sans-serif'
        fig, ax = plt.subplots(figsize=(10, 8))
        node_dict = {n.id: n for n in nodes}
        
        # 1. Sabit Arka Plan (Orijinal Yapı - ÇAPRAZLARI HARİÇ TUT)
        for elem in elements:
            # Attribute kontrolü
            mat_id = getattr(elem, 'material_id', getattr(elem, 'material', 0))
            if hasattr(mat_id, 'id'): mat_id = mat_id.id
            
            # Çaprazsa arka planda çizme
            if mat_id == 3: continue 
            
            ni = node_dict[elem.node_i.id]
            nj = node_dict[elem.node_j.id]
            ax.plot([ni.x, nj.x], [ni.y, nj.y], color='#CCCCCC', linestyle='--', linewidth=1.0, zorder=1)
            
        lines = []

        # A. Kolon ve Kirişleri Ekle (SADECE ÇAPRAZ OLMAYANLAR)
        for elem in elements:
            mat_id = getattr(elem, 'material_id', getattr(elem, 'material', 0))
            if hasattr(mat_id, 'id'): mat_id = mat_id.id
            if mat_id == 3: continue 

            ni = node_dict[elem.node_i.id]
            nj = node_dict[elem.node_j.id]
            color = '#1f77b4' if abs(ni.x - nj.x) < 1e-3 else '#ff7f0e'
            line, = ax.plot([], [], color=color, linewidth=3.0, zorder=10)
            lines.append((line, ni, nj))

        # B. BRACING (Çaprazlar - SADECE TRUE OLANLAR - KOYU TURUNCU)
        grid_conf = config.get('grid', {})
        if grid_conf.get('has_bracing', False):
            seq = grid_conf.get('bracing_sequence', [])
            bay_widths = grid_conf.get('bay_widths', [])
            heights = grid_conf.get('story_heights', [])
            
            for story_idx, story_braces in enumerate(seq):
                y_base = sum(heights[:story_idx])
                y_top = y_base + heights[story_idx]
                current_x = 0.0
                for bay_idx, is_braced in enumerate(story_braces):
                    bay_w = bay_widths[bay_idx]
                    
                    if is_braced:
                        n_bl = next((n for n in nodes if abs(n.x - current_x) < 0.2 and abs(n.y - y_base) < 0.2), None)
                        n_tr = next((n for n in nodes if abs(n.x - (current_x + bay_w)) < 0.2 and abs(n.y - y_top) < 0.2), None)
                        n_br = next((n for n in nodes if abs(n.x - (current_x + bay_w)) < 0.2 and abs(n.y - y_base) < 0.2), None)
                        n_tl = next((n for n in nodes if abs(n.x - current_x) < 0.2 and abs(n.y - y_top) < 0.2), None)
                        
                        if n_bl and n_tr:
                            line1, = ax.plot([], [], color='#D35400', linewidth=3.0, zorder=15)
                            lines.append((line1, n_bl, n_tr))
                        if n_br and n_tl:
                            line2, = ax.plot([], [], color='#D35400', linewidth=3.0, zorder=15)
                            lines.append((line2, n_br, n_tl))
                    current_x += bay_w
            
        ax.set_title("Dinamik Deformasyon (P-Delta)", fontsize=14)
        ax.axis('equal')
        
        def update(frame):
            t = np.sin((frame / 60) * np.pi * 2)
            for line, ni, nj in lines:
                xi = ni.x + getattr(ni, 'u', 0.0) * scale * t
                yi = ni.y + getattr(ni, 'v', 0.0) * scale * t
                xj = nj.x + getattr(nj, 'u', 0.0) * scale * t
                yj = nj.y + getattr(nj, 'v', 0.0) * scale * t
                line.set_data([xi, xj], [yi, yj])
            return [l[0] for l in lines]

        ani = animation.FuncAnimation(fig, update, frames=60, interval=30, blit=True)
        try: ani.save("deformed_animation.gif", writer='pillow', fps=20)
        except Exception as e: print(f"GIF hatası: {e}")
        
        update(15) 
        plt.savefig("deformed_shape.png", dpi=300)
        plt.close()

    @staticmethod
    def plot_capacity_heatmap(nodes, elements, envelope_results, config):
        fig, ax = plt.subplots(figsize=(10, 8))
        node_dict = {n.id: n for n in nodes}
        
        # 1. Heatmap (SADECE ELEMANLAR, BRACE HARİÇ)
        for elem in elements:
            mat_id = getattr(elem, 'material_id', getattr(elem, 'material', 0))
            if hasattr(mat_id, 'id'): mat_id = mat_id.id
            if mat_id == 3: continue 
            
            ni = node_dict[elem.node_i.id]
            nj = node_dict[elem.node_j.id]
            dc = max(envelope_results.get(elem.id, {}).get('i', {}).get('dc', 0), envelope_results.get(elem.id, {}).get('j', {}).get('dc', 0))
            color = '#D62728' if dc > 1.0 else ('#BCBD22' if dc > 0.85 else '#2CA02C')
            ax.plot([ni.x, nj.x], [ni.y, nj.y], color=color, linewidth=4.0, zorder=2)

        # 2. Bracing (KOYU TURUNCU - SADECE TRUE)
        grid_conf = config.get('grid', {})
        if grid_conf.get('has_bracing', False):
            seq = grid_conf.get('bracing_sequence', [])
            bay_widths = grid_conf.get('bay_widths', [])
            heights = grid_conf.get('story_heights', [])
            for story_idx, story_braces in enumerate(seq):
                y_base = sum(heights[:story_idx])
                y_top = y_base + heights[story_idx]
                current_x = 0.0
                for bay_idx, is_braced in enumerate(story_braces):
                    bay_w = bay_widths[bay_idx]
                    if is_braced:
                        ax.plot([current_x, current_x + bay_w], [y_base, y_top], color='#D35400', linewidth=3.0, linestyle='-', alpha=1.0, zorder=10)
                        ax.plot([current_x + bay_w, current_x], [y_base, y_top], color='#D35400', linewidth=3.0, linestyle='-', alpha=1.0, zorder=10)
                    current_x += bay_w
                    
        ax.set_title("AISC Kapasite Haritası")
        ax.axis('equal')
        plt.savefig("capacity_heatmap.png", dpi=300)
        plt.close()

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "data", "input.json")
    config_path = os.path.join(current_dir, "data", "grid_config.json")
    db_path = os.path.join(current_dir, "data", "sections_db.json")
    bu_path = os.path.join(current_dir, "data", "built_up_db.json")
    combo_db_path = os.path.join(current_dir, "data", "load_combos_db.json")
    
    # Raporlama değişkenlerini döngü dışına tanımlıyoruz (Crash olmaması için)
    nodes, elements = [], []
    envelope_results, combo_summaries = {}, {}
    
    try:
        # Verileri yükle
        with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
        with open(db_path, 'r', encoding='utf-8') as f: section_db = json.load(f)
        with open(bu_path, 'r', encoding='utf-8') as f: built_up_db = json.load(f)
        with open(combo_db_path, 'r', encoding='utf-8') as f: combo_db = json.load(f)
        with open(json_path, 'r', encoding='utf-8') as f: raw_input = json.load(f)
        
        from src.validator import validate_input
        if not validate_input(raw_input): return 

        active_combos = config.get("active_combinations", ["COMB_01"])
        if "ALL" in active_combos or "all" in active_combos: active_combos = list(combo_db.keys())
        
        envelope_manager = EnvelopeManager()
        
        # Kombinasyonları ilklendir
        for c in active_combos:
            envelope_manager.combo_summaries[c] = {
                "max_u": 0.0, "drift_warning": False, "design_warning": False, "factors": combo_db.get(c, {})
            }
        
        envelope_results = envelope_manager.envelope_results
        combo_summaries = envelope_manager.combo_summaries
        
        column_profile = config['grid'].get('column_section', 'IPE200')
        beam_profile = config['grid'].get('beam_section', 'HEA300')
        col_sec = SectionFactory.create_section(column_profile, section_db, built_up_db)
        beam_sec = SectionFactory.create_section(beam_profile, section_db, built_up_db)

        # Helper fonksiyon
        def apply_member_properties(elements, col_sec, beam_sec, column_profile, beam_profile, factors=None, raw_elems=None):
            STEEL_DENSITY = 7850.0
            for elem in elements:
                if abs(elem.node_i.x - elem.node_j.x) < 1e-3: 
                    elem.section_name, elem.material.A, elem.material.I = column_profile, col_sec.A, col_sec.I
                    elem.section_Z, elem.section_d = col_sec.Z, col_sec.d
                else: 
                    elem.section_name, elem.material.A, elem.material.I = beam_profile, beam_sec.A, beam_sec.I
                    elem.section_Z, elem.section_d = beam_sec.Z, beam_sec.d
                
                if factors and raw_elems:
                    pats = raw_elems.get(elem.id, {"DEAD": 0.0, "LIVE": 0.0, "SNOW": 0.0})
                    elem.udl = (pats.get("DEAD", 0.0) * factors.get("DEAD", 0.0)) + (pats.get("LIVE", 0.0) * factors.get("LIVE", 0.0)) + (pats.get("SNOW", 0.0) * factors.get("SNOW", 0.0))
                
                length = np.sqrt((elem.node_i.x - elem.node_j.x)**2 + (elem.node_i.y - elem.node_j.y)**2)
                elem.mass = elem.material.A * length * STEEL_DENSITY
                elem.mass_moment_inertia = elem.mass * (length**2) / 12.0 if length > 0 else 1e-6

        # 1. Modal Analiz Ön Hazırlık
        nodes_init, elements_init, bc_init, _, _ = IOHandler.load_input(json_path, ndof=3)
        apply_member_properties(elements_init, col_sec, beam_sec, column_profile, beam_profile)
        
        print(f"\n[+] Modal Analiz Başlıyor...")
        try:
            modal_solver = StructuralSolver(nodes_init, elements_init, bc_init, ndof=3, penalty=1e12)
            modal_solver.run_modal_analysis(num_modes=3)
        except Exception as e:
            print(f" [!] Modal analiz hatası: {e}")

        # 2. Kombinasyon Döngüsü
        print("DEBUG: Kombinasyon döngüsüne giriliyor...")
        for c_name in active_combos:
            try:
                if c_name not in combo_db: continue
                factors = combo_db[c_name]
                nodes, elements, bc, _, _ = IOHandler.load_input(json_path, ndof=3)
                
                raw_elems = {e['id']: e.get('load_patterns', {"DEAD": 0.0, "LIVE": 0.0, "SNOW": 0.0}) for e in raw_input.get('elements', [])}
                nodal_loads = raw_input.get('nodal_loads', [])
                
                apply_member_properties(elements, col_sec, beam_sec, column_profile, beam_profile, factors, raw_elems)
                scaled_nodal_loads = [{"node_id": nl["node_id"], "fx": (nl.get("load_patterns", {}).get("WIND", 0.0) * factors.get("WIND", 0.0)) + (nl.get("load_patterns", {}).get("SEISMIC", 0.0) * factors.get("SEISMIC", 0.0)), "fy": 0.0, "mz": 0.0} for nl in nodal_loads]

                solver = StructuralSolver(nodes, elements, bc, nodal_loads=scaled_nodal_loads, ndof=3, penalty=1e12)
                MemberLoadEffect().apply(solver)
                
                u_linear = solver.solve().copy()
                u_pdelta = solver.solve_pdelta() 
                
                # Tasarım Kontrolü
                designer = DesignChecker()
                for elem in elements:
                    f = getattr(elem, 'internal_forces', None)
                    if not f: continue
                    type_str = f"Kolon ({column_profile})" if abs(elem.node_i.x - elem.node_j.x) < 1e-3 else f"Kiris ({beam_profile})"
                    dc_results = designer.compute_member_dc(elem)
                    for uc in ["i", "j"]:
                        dc = dc_results[uc]['dc']
                        envelope_manager.update_element_envelope(c_name, elem.id, type_str, uc, f['N'+uc], f['V'+uc], f['M'+uc], dc)

                max_u = np.max(np.abs(u_pdelta[0::3]))
                envelope_manager.combo_summaries[c_name]["max_u"] = max_u
                print(f" [✓] Analiz {c_name} tamamlandı.")
            except Exception as e:
                print(f" [!] {c_name} hata verdi: {e}")

        # 3. Raporlama
        if nodes:
            # GÜVENLİ DRIFT HESABI
            try:
                envelope_manager.calculate_story_drifts(nodes, 3.0)
            except AttributeError:
                print(" [!] HATA: src/load_combination.py içinde 'calculate_story_drifts' bulunamadı.")
            
            x_coords_raw = [node.x for node in nodes]
            y_coords_raw = [node.y for node in nodes]
            total_width = max(x_coords_raw) - min(x_coords_raw)
            total_height = max(y_coords_raw) - min(y_coords_raw)
            
            config_info = {
                'has_bracing': config['grid'].get('has_bracing', False),
                'drift_results': envelope_manager.global_last_drift_results,
                'drift_warning': envelope_manager.drift_warning_global,
                'column_section': column_profile,
                'beam_section': beam_profile
            }
            export_results(nodes, elements, envelope_results, combo_summaries, config_info)
            StructuralVisualizer.plot_deformed_shape(nodes, elements, config, scale=30.0, total_width=total_width, total_height=total_height)
            StructuralVisualizer.plot_capacity_heatmap(nodes, elements, envelope_results, config)
        
        print("\n" + "="*50)
        print(" ANALİZ TAMAMLANDI ".center(50, "="))
        print("="*50)
    except Exception as e:
        traceback.print_exc()
        input("Hata oluştu, ENTER ile kapat...")

if __name__ == "__main__":
    main()
