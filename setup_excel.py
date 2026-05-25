import pandas as pd
import json
import os

def json_to_excel():
    # --- YOL AYARLARI ---
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'data', 'input.json')
    excel_path = os.path.join(current_dir, 'data', 'input_data.xlsx')

    # 1. JSON Dosyasını Oku (Dinamik Kısım Burası)
    if not os.path.exists(json_path):
        print(f"[!] HATA: {json_path} bulunamadı. Önce generator'ı çalıştır.")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        print(f"[+] {json_path} başarıyla okundu.")
    except Exception as e:
        print(f"[!] JSON okunurken hata oluştu: {e}")
        return

    # 2. Excel'e Yazma İşlemi
    # JSON anahtarlarını Excel sayfa isimleriyle eşleştiriyoruz
    sheet_mapping = {
        'materials': 'Materials',
        'nodes': 'Nodes',
        'elements': 'Elements',
        'boundary_conditions': 'BC',
        'nodal_loads': 'Loads'
    }

    try:
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            for json_key, sheet_name in sheet_mapping.items():
                if json_key in input_data and input_data[json_key]:
                    # Veriyi DataFrame'e çevir ve sayfaya yaz
                    df = pd.DataFrame(input_data[json_key])
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    print(f" -> {sheet_name} sayfası oluşturuldu.")
        
        print("-" * 50)
        print(f"[✓] İŞLEM BAŞARILI: Excel güncellendi.\nYol: {excel_path}")
        print("-" * 50)

    except Exception as e:
        print(f"[!] Excel'e yazarken hata oluştu: {e}")

if __name__ == "__main__":
    json_to_excel()
