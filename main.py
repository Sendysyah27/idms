import flet as ft
import sqlite3
from datetime import datetime
import warnings
# --- AUTO CREATE DATABASE UNTUK APK ---
def init_db_otomatis():
    conn = sqlite3.connect('data_kasir.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS shift_aktif (
        id INTEGER PRIMARY KEY, is_active BOOLEAN, modal_awal REAL, variance REAL, 
        sales_tunai REAL, tarik_tunai REAL, setoran_sales REAL, 
        struk_tunai INTEGER, struk_tarik INTEGER, struk_nontunai INTEGER
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transaksi (
        id INTEGER PRIMARY KEY AUTOINCREMENT, jenis TEXT, nominal_sales REAL, 
        nominal_tarik REAL, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS histori_setoran (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nominal REAL, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    cursor.execute("SELECT COUNT(*) FROM shift_aktif")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''INSERT INTO shift_aktif (id, is_active, modal_awal, variance, sales_tunai, tarik_tunai, setoran_sales, struk_tunai, struk_tarik, struk_nontunai) VALUES (1, 0, 0, 0, 0, 0, 0, 0, 0, 0)''')
    conn.commit()
    conn.close()

init_db_otomatis() # Panggil fungsi ini pas aplikasi baru nyala
# --------------------------------------
warnings.simplefilter("ignore", DeprecationWarning)

# --- FUNGSI DATABASE ---
def get_db():
    conn = sqlite3.connect('data_kasir.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_shift():
    with get_db() as conn:
        return dict(conn.execute("SELECT * FROM shift_aktif WHERE id=1").fetchone())

def hitung_laci(shift):
    return shift['modal_awal'] + shift['sales_tunai'] - shift['tarik_tunai'] - shift['setoran_sales']

def get_kas_tanpa_modal(shift):
    return shift['sales_tunai'] - shift['tarik_tunai'] - shift['setoran_sales']

# --- APLIKASI UTAMA ---
def main(page: ft.Page):
    page.title = "Creator Engine Pro - POS"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "adaptive"
    page.padding = 15

    def tunjukkan_pesan(pesan, warna="red"):
        page.snack_bar = ft.SnackBar(ft.Text(pesan, weight="bold"), bgcolor=warna)
        page.snack_bar.open = True
        page.update()

    # --- STATE MANAGEMENT ---
    current_view = "buka_shift" 

    def change_view(view_name):
        nonlocal current_view
        current_view = view_name
        refresh_app()

    # ==========================================
    # 1. LAYAR BUKA SHIFT
    # ==========================================
    input_modal = ft.TextField(label="Input Modal Awal Laci (Rp)", keyboard_type="number", text_size=20)
    
    def mulai_shift(e):
        try:
            modal = float(input_modal.value)
            with get_db() as conn:
                conn.execute("UPDATE shift_aktif SET is_active=1, modal_awal=? WHERE id=1", (modal,))
            tunjukkan_pesan(f"Shift Dimulai! Modal: Rp {modal:,.0f}", "green")
            change_view("dashboard")
        except:
            tunjukkan_pesan("Masukkan angka modal yang benar!")

    view_buka_shift = ft.Column([
        ft.Text("🏢 CREATOR ENGINE PRO - POS SYSTEM 🏢", size=18, weight="bold", text_align="center"),
        ft.Divider(),
        ft.Text("Shift belum dibuka. Masukkan MODAL AWAL laci hari ini:", weight="bold"),
        input_modal,
        ft.ElevatedButton("MULAI SHIFT SEKARANG", on_click=mulai_shift, bgcolor="green", color="white", height=50, width=float('inf'))
    ], visible=False)

    # ==========================================
    # 2. DASHBOARD UTAMA
    # ==========================================
    view_dashboard = ft.Column([
        ft.Text("🏢 CREATOR ENGINE PRO - POS SYSTEM 🏢", size=18, weight="bold", text_align="center"),
        ft.Divider(),
        ft.Text("Status: 🟢 SHIFT OPEN", size=16, weight="bold", color="green"),
        ft.Text("Silakan pilih modul operasional Anda:"),
        ft.Container(height=10),
        ft.ElevatedButton("📊 Buka Modul Variance", on_click=lambda _: change_view("variance"), width=float('inf'), height=50),
        ft.Container(height=5),
        ft.ElevatedButton("💵 Buka Modul Kas Aktual", on_click=lambda _: change_view("kas_aktual"), width=float('inf'), height=50),
        ft.Container(height=5),
        ft.ElevatedButton("🛑 CLOSING SHIFT (Opsi Cetak)", on_click=lambda _: change_view("closing_menu"), width=float('inf'), height=50, bgcolor="red", color="white")
    ], visible=False)

    # ==========================================
    # 3. MODUL VARIANCE
    # ==========================================
    teks_variance = ft.Text("", size=18, weight="bold")
    
    def tambah_var(val):
        with get_db() as conn: conn.execute("UPDATE shift_aktif SET variance = variance + ? WHERE id=1", (val,))
        refresh_app()

    view_variance = ft.Column([
        ft.Text("📊 MODUL MONITORING VARIANCE", size=18, weight="bold"),
        ft.Divider(),
        teks_variance,
        ft.Text("Catat setiap kembalian receh/selisih selama shift:"),
        ft.Row([
            ft.ElevatedButton("-500", on_click=lambda _: tambah_var(-500), bgcolor="red", color="white", expand=True),
            ft.ElevatedButton("-200", on_click=lambda _: tambah_var(-200), bgcolor="red", color="white", expand=True),
            ft.ElevatedButton("-100", on_click=lambda _: tambah_var(-100), bgcolor="red", color="white", expand=True),
        ]),
        ft.Row([
            ft.ElevatedButton("+100", on_click=lambda _: tambah_var(100), bgcolor="green", color="white", expand=True),
            ft.ElevatedButton("+200", on_click=lambda _: tambah_var(200), bgcolor="green", color="white", expand=True),
            ft.ElevatedButton("+500", on_click=lambda _: tambah_var(500), bgcolor="green", color="white", expand=True),
        ]),
        ft.Container(height=20),
        ft.ElevatedButton("🔙 Kembali ke Dashboard", on_click=lambda _: change_view("dashboard"), width=float('inf'), height=50)
    ], visible=False)

    # ==========================================
    # 4. MODUL KAS AKTUAL (Rincian Summary)
    # ==========================================
    teks_rincian_kas = ft.Text("")
    
    view_kas_aktual = ft.Column([
        ft.Text("💵 MODUL MONITORING KAS AKTUAL", size=18, weight="bold"),
        ft.Divider(),
        ft.Container(content=teks_rincian_kas, bgcolor="#E3F2FD", padding=10, border_radius=5),
        ft.Container(height=10),
        ft.ElevatedButton("⌨️ 🟢 MULAI INPUT KASIR (Tunai & Non-Tunai)", on_click=lambda _: change_view("input_kasir"), bgcolor="green", color="white", width=float('inf'), height=50),
        ft.Container(height=5),
        ft.ElevatedButton("📤 SETOR UANG KAS (Sales)", on_click=lambda _: change_view("input_setoran"), bgcolor="black", color="white", width=float('inf'), height=50),
        ft.Container(height=5),
        ft.ElevatedButton("🔙 Kembali ke Dashboard", on_click=lambda _: change_view("dashboard"), width=float('inf'), height=50)
    ], visible=False)

    # ==========================================
    # 5. INPUT KASIR (Continuous Mode)
    # ==========================================
    input_sales = ft.TextField(label="Belanja Tunai (Rp)", keyboard_type="number", expand=True)
    input_tarik = ft.TextField(label="Tarik Tunai (Rp)", keyboard_type="number", expand=True)
    list_riwayat = ft.Column(spacing=5)

    def proses_transaksi(e):
        try:
            sales = float(input_sales.value) if input_sales.value else 0
            tarik = float(input_tarik.value) if input_tarik.value else 0
            if sales == 0 and tarik == 0: return tunjukkan_pesan("Isi minimal satu kolom!")
            if tarik > 0 and (tarik < 50000 or tarik % 50000 != 0): return tunjukkan_pesan("Tarik tunai WAJIB kelipatan Rp 50.000!")

            with get_db() as conn:
                conn.execute('''UPDATE shift_aktif SET 
                    sales_tunai = sales_tunai + ?, tarik_tunai = tarik_tunai + ?,
                    struk_tunai = struk_tunai + ?, struk_tarik = struk_tarik + ? WHERE id=1''',
                    (sales, tarik, 1 if sales > 0 else 0, 1 if tarik > 0 else 0))
                conn.execute("INSERT INTO transaksi (jenis, nominal_sales, nominal_tarik) VALUES ('TUNAI', ?, ?)", (sales, tarik))
            
            input_sales.value = ""
            input_tarik.value = ""
            refresh_app()
            tunjukkan_pesan("✅ TRANSAKSI SUKSES Tercatat!", "green")
        except:
            tunjukkan_pesan("Gagal: Masukkan angka yang valid.")

    def proses_nontunai(e):
        with get_db() as conn:
            conn.execute("UPDATE shift_aktif SET struk_nontunai = struk_nontunai + 1 WHERE id=1")
            conn.execute("INSERT INTO transaksi (jenis, nominal_sales, nominal_tarik) VALUES ('NONTUNAI', 0, 0)")
        refresh_app()
        tunjukkan_pesan("✅ +1 Struk Non-Tunai (EDC/QRIS) Tercatat!", "green")

    def undo_terakhir(e):
        with get_db() as conn:
            trx = conn.execute("SELECT * FROM transaksi ORDER BY id DESC LIMIT 1").fetchone()
            if not trx: return tunjukkan_pesan("Belum ada transaksi!", "orange")
            if trx['jenis'] == 'TUNAI':
                conn.execute('''UPDATE shift_aktif SET 
                    sales_tunai = sales_tunai - ?, tarik_tunai = tarik_tunai - ?,
                    struk_tunai = struk_tunai - ?, struk_tarik = struk_tarik - ? WHERE id=1''',
                    (trx['nominal_sales'], trx['nominal_tarik'], 1 if trx['nominal_sales'] > 0 else 0, 1 if trx['nominal_tarik'] > 0 else 0))
            else:
                conn.execute("UPDATE shift_aktif SET struk_nontunai = struk_nontunai - 1 WHERE id=1")
            conn.execute("DELETE FROM transaksi WHERE id=?", (trx['id'],))
        refresh_app()
        tunjukkan_pesan("⚠️ KOREKSI BERHASIL (Transaksi Terakhir di-VOID)!", "orange")

    view_input_kasir = ft.Column([
        ft.Text("🟢 SYSTEM READY: MODE KASIR AKTIF", size=16, weight="bold", color="green"),
        ft.Divider(),
        ft.Row([input_sales, input_tarik]),
        ft.ElevatedButton("🛒 SIMPAN TRANSAKSI (ENTER)", on_click=proses_transaksi, bgcolor="blue", color="white", width=float('inf'), height=50),
        ft.Container(height=5),
        ft.ElevatedButton("💳 +1 Struk Non-Tunai (EDC/QRIS)", on_click=proses_nontunai, bgcolor="purple", color="white", width=float('inf'), height=45),
        ft.ElevatedButton("↩️ Koreksi (Batalkan Transaksi Terakhir)", on_click=undo_terakhir, bgcolor="orange", color="white", width=float('inf'), height=45),
        ft.Divider(),
        ft.Text("🕒 3 Transaksi Terakhir:", weight="bold"),
        list_riwayat,
        ft.Divider(),
        ft.ElevatedButton("🔙 Selesai & Cek Laci", on_click=lambda _: change_view("kas_aktual"), width=float('inf'), height=50)
    ], visible=False)

    # ==========================================
    # 6. INPUT SETORAN
    # ==========================================
    input_setor = ft.TextField(label="Nominal Setor (Rp)", keyboard_type="number", expand=True)
    
    def proses_setoran(e):
        try:
            nominal = float(input_setor.value)
            if nominal < 1000000 or nominal % 1000000 != 0: return tunjukkan_pesan("Setoran minimal & kelipatan Rp 1.000.000!")
            shift = get_shift()
            if nominal > hitung_laci(shift): return tunjukkan_pesan("Gagal: Uang di laci kurang!")

            with get_db() as conn:
                conn.execute("UPDATE shift_aktif SET setoran_sales = setoran_sales + ? WHERE id=1", (nominal,))
                conn.execute("INSERT INTO histori_setoran (nominal) VALUES (?)", (nominal,))
            
            input_setor.value = ""
            tunjukkan_pesan(f"✅ Setoran Rp {nominal:,.0f} Berhasil!", "green")
            change_view("kas_aktual")
        except:
            tunjukkan_pesan("Masukkan angka setoran valid.")

    view_setoran = ft.Column([
        ft.Text("📤 MODUL SETORAN KE BRANKAS", size=18, weight="bold"),
        ft.Divider(),
        ft.Text("⚠️ SOP SETORAN:\n• Minimal Setor : Rp 1.000.000\n• Wajib Kelipatan : Rp 1.000.000", color="red"),
        ft.Container(height=10),
        input_setor,
        ft.ElevatedButton("PROSES SETORAN", on_click=proses_setoran, bgcolor="black", color="white", width=float('inf'), height=50),
        ft.ElevatedButton("❌ Batal", on_click=lambda _: change_view("kas_aktual"), width=float('inf'), height=50)
    ], visible=False)

    # ==========================================
    # 7. CLOSING MENU & BLIND CLOSE
    # ==========================================
    input_fisik = ft.TextField(label="Hitung Fisik Laci (Rp)", keyboard_type="number")
    laporan_teks = ft.Text("", selectable=True)
    
    view_closing_menu = ft.Column([
        ft.Text("🛑 OPSI CLOSING SHIFT", size=18, weight="bold", color="red"),
        ft.Divider(),
        ft.Text("Mau dibantu sistem buat cek selisih fisik uang laci, atau mau langsung cetak laporan akhir?"),
        ft.Container(height=10),
        ft.ElevatedButton("📝 Hitung Fisik Laci (Cek Selisih)", on_click=lambda _: change_view("blind_close"), width=float('inf'), height=50),
        ft.ElevatedButton("🛑 Langsung Cetak Laporan", on_click=lambda _: eksekusi_closing(None), bgcolor="red", color="white", width=float('inf'), height=50),
        ft.ElevatedButton("🔙 Batal (Kembali)", on_click=lambda _: change_view("dashboard"), width=float('inf'), height=50)
    ], visible=False)

    def eksekusi_closing(fisik_input):
        try:
            shift = get_shift()
            laci_sistem = hitung_laci(shift)
            kas_tanpa_modal = get_kas_tanpa_modal(shift)
            total_struk = shift['struk_tunai'] + shift['struk_tarik'] + shift['struk_nontunai']
            
            with get_db() as conn:
                histori = conn.execute("SELECT * FROM histori_setoran").fetchall()
            history_cetak = "Tidak ada setoran."
            if histori:
                history_cetak = "\n".join([f" - Jam {h['waktu'].split(' ')[1]} : Rp {h['nominal']:,.0f}" for h in histori])

            lap = f"""🛑 LAPORAN CLOSING SHIFT 🛑
Tanggal: {datetime.now().strftime('%d %B %Y')}
═══════════════════════════
[1] REKAPITULASI KAS & STRUK
 Modal Awal       : Rp {shift['modal_awal']:,.0f}
 Total Sales      : Rp {shift['sales_tunai']:,.0f}
 Tarik Tunai      : (Rp {shift['tarik_tunai']:,.0f})
 Total Setoran    : (Rp {shift['setoran_sales']:,.0f})
───────────────────────────
✅ SISTEM (WAJIB ADA) : Rp {laci_sistem:,.0f}\n"""

            if fisik_input is not None:
                selisih = fisik_input - laci_sistem
                status_selisih = "⚖️ BALANCE (Pas)"
                if selisih > 0: status_selisih = f"✅ SURPLUS (+Rp {selisih:,.0f})"
                elif selisih < 0: status_selisih = f"⚠️ MINUS (-Rp {abs(selisih):,.0f})"
                lap += f"🕵️ FISIK LACI (INPUT) : Rp {fisik_input:,.0f}\n📈 STATUS SELISIH     : {status_selisih}\n"

            lap += f"""───────────────────────────
🖥️ INPUT KE KOMPUTER  : Rp {kas_tanpa_modal:,.0f} (Tanpa Modal)
───────────────────────────
 Total Semua Struk : {total_struk} Lembar
 ├─ Tunai       : {shift['struk_tunai']} lbr
 ├─ Non-Tunai   : {shift['struk_nontunai']} lbr
 └─ Tarik Tunai : {shift['struk_tarik']} lbr

[2] LOG SETORAN BRANKAS
{history_cetak}

[3] MONITORING VARIANCE (Modul Dinamis)
 Total Akumulasi Variance : Rp {shift['variance']:,.0f}
═══════════════════════════
✅ Shift selesai. Data telah di-reset."""
            
            laporan_teks.value = lap
            with get_db() as conn:
                conn.execute('''UPDATE shift_aktif SET 
                    is_active=0, modal_awal=0, variance=0, sales_tunai=0, tarik_tunai=0, 
                    setoran_sales=0, struk_tunai=0, struk_tarik=0, struk_nontunai=0 WHERE id=1''')
                conn.execute("DELETE FROM transaksi")
                conn.execute("DELETE FROM histori_setoran")
            
            input_fisik.value = ""
            change_view("hasil_closing")
            tunjukkan_pesan("Closing Berhasil! Silakan copy laporan.", "green")
        except:
            tunjukkan_pesan("Terjadi kesalahan sistem saat closing!")

    def proses_blind_close(e):
        try:
            fisik = float(input_fisik.value)
            eksekusi_closing(fisik)
        except:
            tunjukkan_pesan("Masukkan angka fisik uang yang benar!")

    view_blind_close = ft.Column([
        ft.Text("📝 PENGECEKAN FISIK LACI", size=18, weight="bold"),
        ft.Divider(),
        ft.Text("Hitung seluruh uang fisik di laci sekarang dan masukkan nominalnya:"),
        input_fisik,
        ft.ElevatedButton("Proses Hitung Selisih", on_click=proses_blind_close, bgcolor="blue", color="white", width=float('inf'), height=50),
        ft.ElevatedButton("❌ Batal", on_click=lambda _: change_view("closing_menu"), width=float('inf'), height=50)
    ], visible=False)

    view_hasil_closing = ft.Column([
        ft.Text("✅ SHIFT BERHASIL DITUTUP", size=18, weight="bold", color="green"),
        ft.Container(content=laporan_teks, bgcolor="#f0f0f0", padding=10, border_radius=5),
        ft.ElevatedButton("Mulai Shift Baru", on_click=lambda _: change_view("buka_shift"), width=float('inf'), height=50, bgcolor="green", color="white")
    ], visible=False)


    # ==========================================
    # LOGIKA REFRESH DATA & PINDAH LAYAR
    # ==========================================
    def refresh_app():
        shift = get_shift()
        
        if shift['is_active']:
            # 1. Update Teks Variance
            status_var = "⚖️ BALANCE (Pas!)"
            var_warna = "green"
            if shift['variance'] > 0: status_var = "✅ SURPLUS (Lebih)"; var_warna = "blue"
            elif shift['variance'] < 0: status_var = "⚠️ NOMOK (Kurang)"; var_warna = "red"
            teks_variance.value = f"Status Saat Ini : {status_var}\nTotal Variance : Rp {shift['variance']:,.0f}"
            teks_variance.color = var_warna

            # 2. Update Teks Summary Kas Aktual
            with get_db() as conn:
                histori = conn.execute("SELECT * FROM histori_setoran").fetchall()
            history_text = "Belum ada setoran."
            if histori:
                history_text = "\n".join([f"  └ Jam {h['waktu'].split(' ')[1]} -> Rp {h['nominal']:,.0f}" for h in histori])

            laci = hitung_laci(shift)
            total_struk = shift['struk_tunai'] + shift['struk_tarik'] + shift['struk_nontunai']
            teks_rincian_kas.value = (
                f"💰 UANG FISIK DI LACI : Rp {laci:,.0f}\n"
                f"🖥️ KAS INPUT KOMPUTER : Rp {get_kas_tanpa_modal(shift):,.0f} (Tanpa Modal)\n"
                f"═══════════════════════════\n"
                f"🧾 Total Semua Struk  : {total_struk} Lembar\n\n"
                f"Rincian Sistem:\n"
                f"• Modal Awal   : Rp {shift['modal_awal']:,.0f}\n"
                f"• Sales Tunai  : +Rp {shift['sales_tunai']:,.0f} ({shift['struk_tunai']} Struk)\n"
                f"• Tarik Tunai  : -Rp {shift['tarik_tunai']:,.0f} ({shift['struk_tarik']} Struk)\n"
                f"• Non-Tunai    : Rp 0 (EDC) ({shift['struk_nontunai']} Struk)\n"
                f"• Disetor      : -Rp {shift['setoran_sales']:,.0f}\n\n"
                f"Histori Setoran Hari Ini:\n{history_text}"
            )

            # 3. Update Riwayat (Undo) di Menu Input Kasir
            list_riwayat.controls.clear()
            with get_db() as conn:
                riwayat = conn.execute("SELECT * FROM transaksi ORDER BY id DESC LIMIT 3").fetchall()
                if len(riwayat) == 0:
                    list_riwayat.controls.append(ft.Text("Belum ada transaksi.", color="grey"))
                else:
                    for r in riwayat:
                        info = f"🛒 Rp{r['nominal_sales']:,.0f} | 🏧 Rp{r['nominal_tarik']:,.0f}" if r['jenis'] == 'TUNAI' else "💳 1 Struk Non-Tunai"
                        warna = "blue" if r['jenis'] == 'TUNAI' else "purple"
                        list_riwayat.controls.append(
                            ft.Container(content=ft.Text(f"ID #{r['id']} - {info}", color=warna, weight="bold"), bgcolor="#f0f0f0", padding=5, border_radius=5)
                        )

        # 4. Pengendali Visibilitas Layar
        nonlocal current_view
        if shift['is_active'] == 0 and current_view != "hasil_closing":
            current_view = "buka_shift"
            
        view_buka_shift.visible = (current_view == "buka_shift")
        view_dashboard.visible = (current_view == "dashboard")
        view_variance.visible = (current_view == "variance")
        view_kas_aktual.visible = (current_view == "kas_aktual")
        view_input_kasir.visible = (current_view == "input_kasir")
        view_setoran.visible = (current_view == "input_setoran")
        view_closing_menu.visible = (current_view == "closing_menu")
        view_blind_close.visible = (current_view == "blind_close")
        view_hasil_closing.visible = (current_view == "hasil_closing")
        
        page.update()

    page.add(
        view_buka_shift, view_dashboard, view_variance, view_kas_aktual, 
        view_input_kasir, view_setoran, view_closing_menu, view_blind_close, view_hasil_closing
    )
    refresh_app()

ft.run(main, view=ft.AppView.WEB_BROWSER, port=8000)
