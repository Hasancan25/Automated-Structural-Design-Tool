def label_active_dof(self):
        # Mesnetlenmemiş (serbest) dereceleri numaralandır
        count = 0
        # GÜVENLİ SÖZLÜK OLUŞTURMA: Boş veya eksik satırları atla
        support_dict = {}
        for s in self.supports:
            if len(s) >= 4: # En az NodeID + 3 Reaksiyon olmalı
                try:
                    node_id = int(float(s[0]))
                    # Geri kalan değerleri (X, Y, Rot) tam sayıya çevir
                    restraints = [int(float(x)) for x in s[1:4]]
                    support_dict[node_id] = restraints
                except (ValueError, IndexError):
                    continue

        for i in range(1, self.num_node + 1):
            if i in support_dict:
                restraints = support_dict[i]
                for j in range(3):
                    # Güvenlik kontrolü: j indeksi restraints içinde var mı?
                    if j < len(restraints) and restraints[j] == 0: # Serbestse
                        count += 1
                        self.e_array[i-1][j] = count
            else:
                # Mesnet yoksa 3 derece de serbesttir
                for j in range(3):
                    count += 1
                    self.e_array[i-1][j] = count
        return count
