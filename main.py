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
    """Analiz sonuçlarını grafiksel olarak işleyen ve görselleştiren OOP modülü."""
    
    @staticmethod
    def plot_deformed_shape(nodes, elements, scale=30.0, total_width=0.0, total_height=0.0):
        """
        Çerçevenin orijinal hali ile P-Delta deformation şeklini dinamik simülasyon olarak canlandırır.
        Eksenleri temizler, toplam boyutları gösterir ve simülasyonu .gif olarak yerel dizine kaydeder.
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        node_dict = {n.id: n for n in nodes}
        
        # 1. Aşama: Sabit Arka Plan Olarak Çerçevenin Çıplak/Orijinal Halini Gri Çiz (Undeformed)
        for elem in elements:
            ni = node_dict[elem.node_i.id]
            nj = node_dict[elem.node_j.id]
            ax.plot([ni.x, nj.x], [ni.y, nj.y], color='#A0A0A0', linestyle='--', linewidth=1.0)
            
        # Animasyonda güncellenecek çizgi nesnelerini (Line2D instances) ilklendiriyoruz
        lines = []
        for elem in elements:
            ni = node_dict[elem.node_i.id]
            nj = node_dict[elem.node_j.id]
            color = '#1f77b4' if abs(ni.x - nj.x) < 1e-3 else '#ff7f0e'
            line, = ax.plot([], [], color=color, linewidth=2.0)
            lines.append((line, ni, nj))
            
        # --- EKSENLERİ TEMİZLE VE BOYUTLARI SABİTLE ---
        ax.set_title(f"Yapisal Dinamik Simulasyon (Deformed Sway) - Olcek: {scale}x")
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_xticks([])
        ax.set_yticks([])
        
        for spine in ax.spines.values():
            spine.set_visible(False)

        width_text = f"Toplam Aciklik: {total_width:.1f} m"
        height_text = f"Toplam Yukseklik: {total_height:.1f} m"

        plt.figtext(0.5, 0.05, width_text, wrap=True, horizontalalignment='center', fontsize=12, fontweight='bold', color='#1f77b4')
        plt.figtext(0.92, 0.5, height_text, wrap=True, horizontalalignment='right', verticalalignment='center', rotation='vertical', fontsize=12, fontweight='bold', color='#ff7f0e')

        ax.set_aspect('equal')
        
        # Çerçevenin sallanırken model uzayından taşmaması için sınırları esnetiyoruz
        x_coords_raw = [n.x for n in nodes]
        y_coords_raw = [n.y for n in nodes]
        ax.set_xlim(min(x_coords_raw) - total_width * 0.1, max(x_coords_raw) + total_width * 0.3)
        ax.set_ylim(min(y_coords_raw) - total_height * 0.05, max(y_coords_raw) + total_height * 0.1)

        # --- DİNAMİK SİNÜS DALGASI SALLANTI SİMÜLEN MOTORU ---
        num_frames = 60
        def update(frame):
            # t parametresi 0 ile 1 arasında yumuşak periyodik salınım üretir
            t = np.sin((frame / num_frames) * np.pi / 2)
            
            for line, ni, nj in lines:
                ni_u = getattr(ni, 'u', 0.0)
                ni_v = getattr(ni, 'v', 0.0)
                nj_u = getattr(nj, 'u', 0.0)
                nj_v = getattr(nj, 'v', 0.0)
                
                xi = ni.x + ni_u * scale * t
                yi = ni.y + ni_v * scale * t
                xj = nj.x + nj_u * scale * t
                yj = nj.y + nj_v * scale * t
                
                line.set_data([xi, xj], [yi, yj])
            return [l[0] for l in lines]

        # Canlı sallantı (sway) simülasyon döngüsü
        ani = animation.FuncAnimation(fig, update, frames=num_frames, interval=25, blit=True, repeat=True)
        
        # --- DİNAMİK ANIMASYONU .GIF OLARAK HEDEF DİZİNE KAYDET ---
        anim_save_path = os.path.join(os.getcwd(), "deformed_animation.gif")
        try:
            ani.save(anim_save_path, writer='pillow', fps=40)
            print(f" [✓] Dinamik deformasyon grafigi animasyonu basariyla kaydedildi: {anim_save_path}")
        except Exception as e:
            print(f" [!] Animasyon kaydetme hatasi: {e}")
            
        # Görseli en son karedeyken arka planda stabil resim (.png) olarak da basıyoruz
        update(num_frames - 1)
        save_path = os.path.join(os.getcwd(), "deformed_shape.png")
        try:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
            print(f" [✓] Dinamik deformasyon grafiginin son karesi kaydedildi: {save_path}")
        except Exception as e:
            print(f" [!] Grafik kaydetme hatası (Deformed Shape): {e}")

        plt.show()

    @staticmethod
    def plot_capacity_heatmap(nodes, elements, envelope_results):
        """AISC 360 D/C oranlarına göre elemanları renk kodlu kapasite haritası olarak çizer ve kaydeder."""
        plt.figure(figsize=(10, 8))
        node_dict = {n.id: n for n in nodes}
        
        for elem in elements:
            ni = node_dict[elem.node_i.id]
            nj = node_dict[elem.node_j.id]
            
            # Elemanın zarftaki (envelope) maksimum D/C oranını bul
            dc_i = envelope_results.get(elem.id, {}).get('i', {}).get('dc', 0.0)
            dc_j = envelope_results.get(elem.id, {}).get('j', {}).get('dc', 0.0)
            max_dc = max(dc_i, dc_j)
            
            # Renk Süzgeci: Güvenliyse Yeşil, Kritikse Sarı, Limit Aşmıssa Kıpkırmızı!
            if max_dc > 1.0:
                color = '#D62728' # Canlı Kırmızı
                linewidth = 3.0
            elif max_dc > 0.85:
                color = '#BCBD22' # Uyarı Sarısı
                linewidth = 2.5
            else:
                color = '#2CA02C' # Güvenli Yeşil
                linewidth = 2.0
                
            plt.plot([ni.x, nj.x], [ni.y, nj.y], color=color, linewidth=linewidth)
            
        # --- EKSENLERİ TEMİZLE VE BOYUTLARI GÖSTER ---
        plt.title("AISC 360-16 Kesit Mukavemet Kapasite Haritasi (D/C Heatmap)")
        
        plt.xlabel("")
        plt.ylabel("")
        plt.gca().set_xticks([])
        plt.gca().set_yticks([])
        
        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        plt.gca().spines['bottom'].set_visible(False)
        plt.gca().spines['left'].set_visible(False)

        if nodes:
            x_coords_raw = [node.x for node in nodes]
            y_coords_raw = [node.y for node in nodes]
            total_width = max(x_coords_raw) - min(x_coords_raw)
            total_height = max(y_coords_raw) - min(y_coords_raw)
        else:
            total_width, total_height = 0.0, 0.0

        width_text = f"Toplam Aciklik: {total_width:.1f} m"
        height_text = f"Toplam Yukseklik: {total_height:.1f} m"

        plt.figtext(0.5, 0.05, width_text, wrap=True, horizontalalignment='center', fontsize=12, fontweight='bold', color='#1f77b4')
        plt.figtext(0.92, 0.5, height_text, wrap=True, horizontalalignment='right', verticalalignment='center', rotation='vertical', fontsize=12, fontweight='bold', color='#ff7f0e')

        plt.grid(False)
        plt.axis('equal')
        
        # --- GÜNCELLEME: GÖRSELİ BELİRTİLEN PROJE DİZİNİNE KAYDET ---
        save_path = os.path.join(os.getcwd(), "capacity_heatmap.png")
        try:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
            print(f" [✓] Kapasite ısı haritası başarıyla kaydedildi: {save_path}")
        except Exception as e:
            print(f" [!] Grafik kaydetme hatası (Capacity Heatmap): {e}")

        plt.show()

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "data", "input.json")
    config_path = os.path.join(current_dir, "data", "grid_config.json")
    db_path = os.path.join(current_dir, "data", "sections_db.json")
    bu_path = os.path.join(current_dir, "data", "built_up_db.json")
    combo_db_path = os.path.join(current_dir, "data", "load_combos_db.json")
    
    try:
        # 1. Konfigürasyonları ve Üçlü Veritabanı Katmanlarını Yükle
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
        else: config = {"grid": {"has_bracing": False}}

        if os.path.exists(db_path):
            with open(db_path, 'r', encoding='utf-8') as f: section_db = json.load(f)
        else: section_db = {}

        if os.path.exists(bu_path):
            with open(bu_path, 'r', encoding='utf-8') as f: built_up_db = json.load(f)
        else: built_up_db = {}
            
        if os.path.exists(combo_db_path):
            with open(combo_db_path, 'r', encoding='utf-8') as f: combo_db = json.load(f)
        else: combo_db = {}

        # Aktif kombinasyon listesini grid_config'den çek
        active_combos = config.get("active_combinations", ["COMB_01"])
        
        # --- GERÇEK PARAMETRİK DİNAMİK BAĞLANTI KATMANI (JOKER KONTROLÜ VE FIX) ---
        if "ALL" in active_combos or "all" in active_combos:
            active_combos = list(combo_db.keys())
        
        # --- OOP KOMBİNASYON VE ZARF MOTORU ENJEKSİYONU ---
        envelope_manager = EnvelopeManager()
        envelope_results = envelope_manager.envelope_results
        combo_summaries = envelope_manager.combo_summaries
        
        u_pdelta = None
        b2_factor = 1.0

        # --- HARİCİ KÜTÜPHANEDEN GEOMETRİK ÖZELLİK ÖN OKUMASI (OOP FABRİKASINA BAĞLANDI) ---
        column_profile = config['grid'].get('column_section', 'IPE200')
        beam_profile = config['grid'].get('beam_section', 'HEA300')
        
        # Fabrika modülü üzerinden bağımsız kesit nesneleri üretilir
        col_sec = SectionFactory.create_section(column_profile, section_db, built_up_db)
        beam_sec = SectionFactory.create_section(beam_profile, section_db, built_up_db)

        # --- PARAMETRİK MASTER KOMBİNASYON DÖNGÜSÜ ---
        for c_name in active_combos:
            if c_name not in combo_db:
                print(f" [!] {c_name} yuk kombinasyon kütüphanesinde bulunamadi, atlaniyor.")
                continue
                
            factors = combo_db[c_name]
            print(f"[+] Kombinasyon Cozuluyor: {c_name} -> DEAD:{factors.get('DEAD',0)}, LIVE:{factors.get('LIVE',0)}, WIND:{factors.get('WIND',0)}, SEISMIC:{factors.get('SEISMIC',0)}")
            
            # 2. Analiz Verisini input.json üzerinden her kombinasyon için temiz yükle
            nodes, elements, bc, _, _ = IOHandler.load_input(json_path, ndof=3)
            with open(json_path, 'r', encoding='utf-8') as f:
                raw_input = json.load(f)
                raw_elems = {e['id']: e.get('load_patterns', {"DEAD": 0.0, "LIVE": 0.0, "SNOW": 0.0}) for e in raw_input.get('elements', [])}
                nodal_loads = raw_input.get('nodal_loads', [])

            # A. Eleman Rijitliklerini Besle ve Nesne Özniteliklerini Doğrudan Aktar
            for elem in elements:
                if abs(elem.node_i.x - elem.node_j.x) < 1e-3: # Kolon Sınıfı
                    elem.section_name = column_profile; elem.material.A = col_sec.A; elem.material.I = col_sec.I
                    elem.section_Z = col_sec.Z; elem.section_d = col_sec.d
                    elem.udl = 0.0
                else: # Kiriş Sınıfı
                    elem.section_name = beam_profile; elem.material.A = beam_sec.A; elem.material.I = beam_sec.I
                    elem.section_Z = beam_sec.Z; elem.section_d = beam_sec.d
                    pats = raw_elems.get(elem.id, {"DEAD": 0.0, "LIVE": 0.0, "SNOW": 0.0})
                    elem.udl = (pats.get("DEAD", 0.0) * factors.get("DEAD", 0.0)) + \
                               (pats.get("LIVE", 0.0) * factors.get("LIVE", 0.0)) + \
                               (pats.get("SNOW", 0.0) * factors.get("SNOW", 0.0))
            
            # B. Düğüm Noktası Yanal Yüklerini Katsayılarla Kombine Et
            scaled_nodal_loads = []
            for nl in nodal_loads:
                pats = nl.get("load_patterns", {"WIND": 0.0, "SEISMIC": 0.0})
                fx_combined = (pats.get("WIND", 0.0) * factors.get("WIND", 0.0)) + \
                              (pats.get("SEISMIC", 0.0) * factors.get("SEISMIC", 0.0))
                scaled_nodal_loads.append({"node_id": nl["node_id"], "fx": fx_combined, "fy": 0.0, "mz": 0.0})

            # 3. Analizi Gerçekleştir (YALIN ÇİFT ANALİZ KATMANI)
            solver = StructuralSolver(nodes, elements, bc, nodal_loads=scaled_nodal_loads, ndof=3, penalty=1e12)
            MemberLoadEffect().apply(solver)
            
            u_linear = solver.solve().copy()
            u_pdelta = solver.solve_pdelta() 
            
            # 4. B2 Amplifikasyon Katsayısı Hesaplama Adımı
            max_u_linear = np.max(np.abs(u_linear[0::3]))
            max_u_pdelta = np.max(np.abs(u_pdelta[0::3]))
            b2_factor = max_u_pdelta / max_u_linear if max_u_linear > 1e-9 else 1.0

            # --- 5. GÖRELİ KAT ÖTELENMELERİ (DRIFT) ALGORİTMASI ---
            y_coords = sorted(list(set([node.y for node in nodes])))
            current_drift_results = []
            drift_warning = False
            drift_limit = 0.008  
            max_theta_combo = 0.0
            
            for idx in range(1, len(y_coords)):
                y_curr = y_coords[idx]
                y_prev = y_coords[idx-1]
                h_story = y_curr - y_prev
                
                nodes_curr = [n for n in nodes if abs(n.y - y_curr) < 1e-3]
                nodes_prev = [n for n in nodes if abs(n.y - y_prev) < 1e-3]
                
                u_curr = np.max([abs(getattr(n, 'u', 0.0)) for n in nodes_curr])
                u_prev = np.max([abs(getattr(n, 'u', 0.0)) for n in nodes_prev])
                
                delta_story = abs(u_curr - u_prev)
                theta = delta_story / h_story
                
                if theta > max_theta_combo: max_theta_combo = theta
                
                if theta > drift_limit:
                    status = "LIMIT ASILDI"
                    drift_warning = True
                else:
                    status = "GUVENLI"
                    
                current_drift_results.append({
                    'story': idx, 'h': h_story, 'delta': delta_story, 'theta': theta, 'status': status
                })
            
            envelope_manager.initialize_combo_summary(c_name, np.max(np.abs(u_pdelta)), max_theta_combo, drift_warning, current_drift_results, factors)

            # --- 6. ELEMAN BAZLI ZARF (ENVELOPE) MUKAVEMET SÜZGECİ (YENİ OOP DESIGNCHECKER ENTEGRASYONU) ---
            designer = DesignChecker()  # GÜNCELLEME: Yeni Kapsüllenmiş Tasarım Sınıfı Çağrısı
            
            for elem in elements:
                f = getattr(elem, 'internal_forces', None)
                if not f: continue
                
                if abs(elem.node_i.x - elem.node_j.x) < 1e-3: 
                    type_str = f"Kolon ({column_profile})"
                else: 
                    type_str = f"Kiris ({beam_profile})"
                    
                # GÜNCELLEME: Elemanın iki ucu için LRFD D/C oranlarını yeni modülümüzden çekiyoruz
                dc_results = designer.compute_member_dc(elem)
                
                # İki ucu birden denetle (i ve j) - Tüm limit durum matematiği design.py içinde gizlidir
                for uc in ["i", "j"]:
                    dc = dc_results[uc]['dc']
                    envelope_manager.update_element_envelope(c_name, elem.id, type_str, uc, f['N'+uc], f['V'+uc], f['M'+uc], dc)

        # Kümülatif undeformed boyutları hesapla
        if nodes:
            x_coords_raw = [node.x for node in nodes]
            y_coords_raw = [node.y for node in nodes]
            total_width = max(x_coords_raw) - min(x_coords_raw)
            total_height = max(y_coords_raw) - min(y_coords_raw)
        else:
            total_width, total_height = 0.0, 0.0

        # --- 7. DIŞA AKTAR ---
        config_info = {
            'has_bracing': config['grid'].get('has_bracing', False),
            'sequence': config['grid'].get('bracing_sequence', "Standart"),
            'brace_mat_id': config['grid'].get('brace_material_id', 1),
            'max_u': np.max(np.abs(u_pdelta)) if u_pdelta is not None else 0.0,
            'b2_factor': b2_factor,
            'drift_results': envelope_manager.global_last_drift_results,  
            'drift_warning': envelope_manager.drift_warning_global,
            'column_section': column_profile,  
            'beam_section': beam_profile       
        }
        
        export_results(nodes, elements, envelope_results, combo_summaries, config_info)

        # --- 8. GRAFİKSEL SON İŞLEM GÖRSELLEŞTİRME ---
        print("\n[+] Analiz Sonuclari Grafiksel Olarak Basincli Isı Haritasina Dokuluyor...")
        StructuralVisualizer.plot_deformed_shape(nodes, elements, scale=30.0, total_width=total_width, total_height=total_height)
        StructuralVisualizer.plot_capacity_heatmap(nodes, elements, envelope_results)

    except Exception as e:
        print(f"\n [!] KRITIK HATA: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
