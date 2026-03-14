import flet as ft
import sqlite3
import os
import warnings
from datetime import datetime

# --- KONFIGURASI SISTEM & DATABASE ---
warnings.simplefilter("ignore", DeprecationWarning)

# Menentukan lokasi database yang aman di Android
# os.getcwd() di Android akan mengarah ke folder internal data aplikasi
DB_NAME = "creator_pos_engine.db"
DB_PATH = os.path.join(os.getcwd(), DB_NAME)

class DatabaseManager:
    @staticmethod
    def get_connection():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def initialize():
        with DatabaseManager.get_connection() as conn:
            cursor = conn.cursor()
            # Tabel utama untuk menyimpan status shift
            cursor.execute('''CREATE TABLE IF NOT EXISTS shift_aktif (
                id INTEGER PRIMARY KEY, 
                is_active BOOLEAN DEFAULT 0, 
                modal_awal REAL DEFAULT 0, 
                variance REAL DEFAULT 0, 
                sales_tunai REAL DEFAULT 0, 
                tarik_tunai REAL DEFAULT 0, 
                setoran_sales REAL DEFAULT 0, 
                struk_tunai INTEGER DEFAULT 0, 
                struk_tarik INTEGER DEFAULT 0, 
                struk_nontunai INTEGER DEFAULT 0
            )''')
            # Tabel riwayat transaksi harian
            cursor.execute('''CREATE TABLE IF NOT EXISTS transaksi (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                jenis TEXT, 
                nominal_sales REAL, 
                nominal_tarik REAL, 
                waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            # Tabel log setoran brankas
            cursor.execute('''CREATE TABLE IF NOT EXISTS histori_setoran (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                nominal REAL, 
                waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            
            # Cek jika data awal belum ada
            cursor.execute("SELECT COUNT(*) FROM shift_aktif")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO shift_aktif (id) VALUES (1)")
            conn.commit()

# --- INITIALIZE DATABASE ---
DatabaseManager.initialize()

def main(page: ft.Page):
    # --- PAGE CONFIGURATION ---
    page.title = "CREATOR ENGINE PRO"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.bgcolor = "#F5F7FA"

    # --- UI STATE & REFRESH LOGIC ---
    current_view = ft.Column(expand=True)

    def show_toast(text, is_error=True):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(text, color="white", weight="bold"),
            bgcolor="red" if is_error else "green",
            action="OK"
        )
        page.snack_bar.open = True
        page.update()

    def get_current_shift_data():
        with DatabaseManager.get_connection() as conn:
            return dict(conn.execute("SELECT * FROM shift_aktif WHERE id=1").fetchone())

    # --- SHARED UI COMPONENTS ---
    def header_section(subtitle):
        return ft.Column([
            ft.Text("CREATOR ENGINE PRO", size=24, weight="bold", color="blue800"),
            ft.Text(subtitle, size=14, color="grey700", italic=True),
            ft.Divider(height=20, thickness=2),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # ==========================================
    # NAVIGATION LOGIC
    # ==========================================
    def navigate_to(view_name):
        current_view.controls.clear()
        shift = get_current_shift_data()
        
        # Logika proteksi: Jika shift belum buka, paksa ke halaman buka shift
        if not shift['is_active'] and view_name != "hasil_closing":
            render_buka_shift()
        elif view_name == "dashboard":
            render_dashboard(shift)
        elif view_name == "variance":
            render_variance(shift)
        elif view_name == "kas_aktual":
            render_kas_aktual(shift)
        elif view_name == "input_kasir":
            render_input_kasir()
        elif view_name == "setoran":
            render_setoran()
        elif view_name == "closing_menu":
            render_closing_menu()
        elif view_name == "blind_close":
            render_blind_close()
        elif view_name == "hasil_closing":
            render_hasil_closing()
            
        page.update()

    # ==========================================
    # RENDER VIEWS (MODULAR)
    # ==========================================

    def render_buka_shift():
        input_modal = ft.TextField(
            label="Modal Awal Laci", 
            prefix_text="Rp ", 
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
            focused_border_color="blue"
        )

        def handle_buka(e):
            try:
                val = float(input_modal.value)
                with DatabaseManager.get_connection() as conn:
                    conn.execute("UPDATE shift_aktif SET is_active=1, modal_awal=? WHERE id=1", (val,))
                navigate_to("dashboard")
            except: show_toast("Masukkan nominal modal yang valid!")

        current_view.controls.append(ft.Column([
            header_section("Point of Sale System"),
            ft.Container(height=40),
            ft.Icon(ft.icons.LOCK_OPEN_ROUNDED, size=50, color="green"),
            ft.Text("Selamat Bertugas!\nSilakan input modal awal untuk memulai.", text_align="center"),
            input_modal,
            ft.ElevatedButton(
                "BUKA SHIFT SEKARANG", 
                on_click=handle_buka, 
                style=ft.ButtonStyle(bgcolor="green", color="white", shape=ft.RoundedRectangleBorder(radius=10)),
                height=50, width=400
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER))

    def render_dashboard(shift):
        current_view.controls.append(ft.Column([
            header_section("Main Dashboard"),
            ft.Row([
                ft.Icon(ft.icons.CIRCLE, color="green", size=12),
                ft.Text("SHIFT AKTIF", weight="bold", color="green")
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=20),
            ft.Card(
                content=ft.Container(
                    padding=20,
                    content=ft.Column([
                        ft.Text("Pilih Menu Operasional:", size=16, weight="w500"),
                        ft.ElevatedButton("📊 Monitoring Variance", icon=ft.icons.DIFFERENCE, on_click=lambda _: navigate_to("variance"), width=float('inf')),
                        ft.ElevatedButton("💵 Monitor Kas & Input", icon=ft.icons.MONETIZATION_ON, on_click=lambda _: navigate_to("kas_aktual"), width=float('inf')),
                        ft.Divider(),
                        ft.ElevatedButton("🛑 CLOSING SHIFT", icon=ft.icons.STOP_SCREEN_SHARE, on_click=lambda _: navigate_to("closing_menu"), bgcolor="red700", color="white", width=float('inf')),
                    ])
                )
            )
        ]))

    def render_variance(shift):
        total_var = shift['variance']
        status = "⚖️ BALANCE" if total_var == 0 else ("✅ SURPLUS" if total_var > 0 else "⚠️ NOMOK")
        warna = "green" if total_var == 0 else ("blue" if total_var > 0 else "red")

        def update_var(val):
            with DatabaseManager.get_connection() as conn:
                conn.execute("UPDATE shift_aktif SET variance = variance + ? WHERE id=1", (val,))
            navigate_to("variance")

        current_view.controls.append(ft.Column([
            header_section("Modul Variance"),
            ft.Container(
                content=ft.Column([
                    ft.Text(status, size=20, weight="bold", color=warna),
                    ft.Text(f"Rp {total_var:,.0f}", size=30, weight="bold"),
                ], horizontal_alignment="center"),
                padding=20, bgcolor="white", border_radius=15, border=ft.border.all(1, warna)
            ),
            ft.Text("Quick Action (Receh Kembalian):", size=14),
            ft.Row([
                ft.ElevatedButton("-500", on_click=lambda _: update_var(-500), color="red", expand=True),
                ft.ElevatedButton("-200", on_click=lambda _: update_var(-200), color="red", expand=True),
                ft.ElevatedButton("-100", on_click=lambda _: update_var(-100), color="red", expand=True),
            ]),
            ft.Row([
                ft.ElevatedButton("+100", on_click=lambda _: update_var(100), color="green", expand=True),
                ft.ElevatedButton("+200", on_click=lambda _: update_var(200), color="green", expand=True),
                ft.ElevatedButton("+500", on_click=lambda _: update_var(500), color="green", expand=True),
            ]),
            ft.ElevatedButton("Kembali ke Dashboard", icon=ft.icons.ARROW_BACK, on_click=lambda _: navigate_to("dashboard"), width=float('inf'))
        ]))

    def render_kas_aktual(shift):
        laci_sistem = shift['modal_awal'] + shift['sales_tunai'] - shift['tarik_tunai'] - shift['setoran_sales']
        kas_tanpa_modal = shift['sales_tunai'] - shift['tarik_tunai'] - shift['setoran_sales']
        
        current_view.controls.append(ft.Column([
            header_section("Monitoring Kas"),
            ft.Card(
                color="blue50",
                content=ft.Container(
                    padding=15,
                    content=ft.Column([
                        ft.Text("💰 UANG FISIK DI LACI (ESTIMASI):", size=12, weight="bold"),
                        ft.Text(f"Rp {laci_sistem:,.0f}", size=24, weight="bold", color="blue900"),
                        ft.Text(f"🖥️ Input Komputer: Rp {kas_tanpa_modal:,.0f}", size=12, italic=True),
                    ])
                )
            ),
            ft.Container(height=10),
            ft.ElevatedButton("🛒 MULAI INPUT TRANSAKSI", icon=ft.icons.ADD_SHOPPING_CART, on_click=lambda _: navigate_to("input_kasir"), bgcolor="green", color="white", width=float('inf'), height=50),
            ft.ElevatedButton("📤 SETOR UANG KE BRANKAS", icon=ft.icons.UPLOAD, on_click=lambda _: navigate_to("setoran"), bgcolor="black", color="white", width=float('inf'), height=50),
            ft.TextButton("Kembali ke Dashboard", on_click=lambda _: navigate_to("dashboard"))
        ]))

    def render_input_kasir():
        in_sales = ft.TextField(label="Tunai Masuk (Sales)", prefix_text="Rp ", keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        in_tarik = ft.TextField(label="Tarik Tunai", prefix_text="Rp ", keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        list_trx = ft.Column()

        # Render 3 histori terakhir
        with DatabaseManager.get_connection() as conn:
            trx_rows = conn.execute("SELECT * FROM transaksi ORDER BY id DESC LIMIT 3").fetchall()
            for r in trx_rows:
                info = f"🛒 Rp{r['nominal_sales']:,.0f} | 🏧 Rp{r['nominal_tarik']:,.0f}" if r['jenis'] == "TUNAI" else "💳 Struk Non-Tunai"
                list_trx.controls.append(ft.Text(f"• {info}", size=12, color="grey700"))

        def handle_simpan(e):
            try:
                s = float(in_sales.value) if in_sales.value else 0
                t = float(in_tarik.value) if in_tarik.value else 0
                if s == 0 and t == 0: return
                if t > 0 and (t < 50000 or t % 50000 != 0):
                    show_toast("Tarik tunai harus kelipatan 50.000!")
                    return
                
                with DatabaseManager.get_connection() as conn:
                    conn.execute("UPDATE shift_aktif SET sales_tunai=sales_tunai+?, tarik_tunai=tarik_tunai+?, struk_tunai=struk_tunai+?, struk_tarik=struk_tarik+? WHERE id=1", (s, t, 1 if s>0 else 0, 1 if t>0 else 0))
                    conn.execute("INSERT INTO transaksi (jenis, nominal_sales, nominal_tarik) VALUES ('TUNAI', ?, ?)", (s, t))
                navigate_to("input_kasir")
            except: show_toast("Input tidak valid!")

        def handle_nontunai(e):
            with DatabaseManager.get_connection() as conn:
                conn.execute("UPDATE shift_aktif SET struk_nontunai=struk_nontunai+1 WHERE id=1")
                conn.execute("INSERT INTO transaksi (jenis, nominal_sales, nominal_tarik) VALUES ('NONTUNAI', 0, 0)")
            navigate_to("input_kasir")

        def handle_undo(e):
            with DatabaseManager.get_connection() as conn:
                last = conn.execute("SELECT * FROM transaksi ORDER BY id DESC LIMIT 1").fetchone()
                if last:
                    if last['jenis'] == "TUNAI":
                        conn.execute("UPDATE shift_aktif SET sales_tunai=sales_tunai-?, tarik_tunai=tarik_tunai-?, struk_tunai=struk_tunai-?, struk_tarik=struk_tarik-? WHERE id=1", (last['nominal_sales'], last['nominal_tarik'], 1 if last['nominal_sales']>0 else 0, 1 if last['nominal_tarik']>0 else 0))
                    else:
                        conn.execute("UPDATE shift_aktif SET struk_nontunai=struk_nontunai-1 WHERE id=1")
                    conn.execute("DELETE FROM transaksi WHERE id=?", (last['id'],))
            navigate_to("input_kasir")

        current_view.controls.append(ft.Column([
            header_section("Input Kasir"),
            ft.Row([in_sales, in_tarik]),
            ft.ElevatedButton("SIMPAN TRANSAKSI", icon=ft.icons.SAVE, on_click=handle_simpan, bgcolor="blue", color="white", width=float('inf')),
            ft.Row([
                ft.ElevatedButton("+1 Non-Tunai", icon=ft.icons.CREDIT_CARD, on_click=handle_nontunai, expand=True),
                ft.ElevatedButton("Undo Terakhir", icon=ft.icons.UNDO, on_click=handle_undo, color="orange", expand=True),
            ]),
            ft.Divider(),
            ft.Text("3 Riwayat Terakhir:", size=12, weight="bold"),
            list_trx,
            ft.Container(height=10),
            ft.ElevatedButton("Selesai & Cek Laci", icon=ft.icons.CHECK, on_click=lambda _: navigate_to("kas_aktual"), width=float('inf'))
        ]))

    def render_setoran():
        in_setor = ft.TextField(label="Nominal Setor Sales", prefix_text="Rp ", keyboard_type=ft.KeyboardType.NUMBER)
        
        def handle_setor(e):
            try:
                val = float(in_setor.value)
                if val < 1000000 or val % 1000000 != 0:
                    show_toast("Setoran minimal & kelipatan 1.000.000!")
                    return
                with DatabaseManager.get_connection() as conn:
                    conn.execute("UPDATE shift_aktif SET setoran_sales=setoran_sales+? WHERE id=1", (val,))
                    conn.execute("INSERT INTO histori_setoran (nominal) VALUES (?)", (val,))
                navigate_to("kas_aktual")
                show_toast(f"Setoran Rp {val:,.0f} sukses!", is_error=False)
            except: show_toast("Nominal salah!")

        current_view.controls.append(ft.Column([
            header_section("Setoran Brankas"),
            ft.Text("Minimal & Kelipatan Rp 1.000.000", color="red", size=12),
            in_setor,
            ft.ElevatedButton("EKSEKUSI SETORAN", icon=ft.icons.SEND, on_click=handle_setor, bgcolor="black", color="white", width=float('inf')),
            ft.TextButton("Batal", on_click=lambda _: navigate_to("kas_aktual"))
        ]))

    def render_closing_menu():
        current_view.controls.append(ft.Column([
            header_section("Opsi Closing"),
            ft.Text("Pilih mode penutupan shift:", text_align="center"),
            ft.ElevatedButton("📝 Hitung Fisik Laci (SOP)", icon=ft.icons.CALCULATE, on_click=lambda _: navigate_to("blind_close"), width=float('inf')),
            ft.ElevatedButton("🛑 Langsung Cetak Laporan", icon=ft.icons.PRINT, on_click=lambda _: execute_final_closing(None), bgcolor="red", color="white", width=float('inf')),
            ft.TextButton("Kembali", on_click=lambda _: navigate_to("dashboard"))
        ], horizontal_alignment="center"))

    def render_blind_close():
        in_fisik = ft.TextField(label="Input Total Fisik di Laci", prefix_text="Rp ", keyboard_type=ft.KeyboardType.NUMBER)
        
        def handle_blind(e):
            try:
                execute_final_closing(float(in_fisik.value))
            except: show_toast("Input fisik tidak valid!")

        current_view.controls.append(ft.Column([
            header_section("Blind Closing"),
            ft.Text("Hitung seluruh uang tunai di laci (termasuk modal) lalu masukkan nominalnya:", size=13),
            in_fisik,
            ft.ElevatedButton("PROSES PENGECEKAN", icon=ft.icons.CHECK_CIRCLE, on_click=handle_blind, bgcolor="blue", color="white", width=float('inf')),
            ft.TextButton("Batal", on_click=lambda _: navigate_to("closing_menu"))
        ]))

    # --- LOGIKA PENUTUPAN FINAL ---
    laporan_global = ""

    def execute_final_closing(fisik_input):
        nonlocal laporan_global
        shift = get_current_shift_data()
        laci_sistem = shift['modal_awal'] + shift['sales_tunai'] - shift['tarik_tunai'] - shift['setoran_sales']
        kas_tanpa_modal = shift['sales_tunai'] - shift['tarik_tunai'] - shift['setoran_sales']
        
        with DatabaseManager.get_connection() as conn:
            setoran_rows = conn.execute("SELECT * FROM histori_setoran").fetchall()
        
        setoran_text = "\n".join([f"- Jam {r['waktu'].split(' ')[1]}: Rp {r['nominal']:,.0f}" for r in setoran_rows]) or "Tidak ada setoran."

        header = f"🛑 LAPORAN CLOSING SHIFT 🛑\n{datetime.now().strftime('%d %B %Y | %H:%M')}\n" + "═"*25 + "\n"
        rekap = f"Modal Awal    : Rp {shift['modal_awal']:,.0f}\nSales Tunai   : Rp {shift['sales_tunai']:,.0f}\nTarik Tunai   : (Rp {shift['tarik_tunai']:,.0f})\nSetoran       : (Rp {shift['setoran_sales']:,.0f})\n"
        sistem = f"SISTEM WAJIB  : Rp {laci_sistem:,.0f}\n"
        
        selisih_text = ""
        if fisik_input is not None:
            diff = fisik_input - laci_sistem
            status = "PAS" if diff == 0 else (f"SURPLUS +{diff:,.0f}" if diff > 0 else f"MINUS {diff:,.0f}")
            selisih_text = f"FISIK LACI    : Rp {fisik_input:,.0f}\nSTATUS        : {status}\n"

        footer = "═"*25 + f"\nINPUT KOMPUTER: Rp {kas_tanpa_modal:,.0f}\nVariance      : Rp {shift['variance']:,.0f}\n"
        laporan_global = header + rekap + sistem + selisih_text + footer + "\nLog Setoran:\n" + setoran_text

        # Reset Database
        with DatabaseManager.get_connection() as conn:
            conn.execute("UPDATE shift_aktif SET is_active=0, modal_awal=0, variance=0, sales_tunai=0, tarik_tunai=0, setoran_sales=0, struk_tunai=0, struk_tarik=0, struk_nontunai=0 WHERE id=1")
            conn.execute("DELETE FROM transaksi")
            conn.execute("DELETE FROM histori_setoran")
        
        navigate_to("hasil_closing")

    def render_hasil_closing():
        current_view.controls.append(ft.Column([
            header_section("Laporan Akhir"),
            ft.Container(
                content=ft.Text(laporan_global, font_family="monospace", size=12),
                padding=15, bgcolor="white", border_radius=10, border=ft.border.all(1, "grey300")
            ),
            ft.ElevatedButton("Copy Laporan", icon=ft.icons.COPY, on_click=lambda _: page.set_clipboard(laporan_global)),
            ft.ElevatedButton("Selesai & Buka Shift Baru", icon=ft.icons.REFRESH, on_click=lambda _: navigate_to("buka_shift"), bgcolor="green", color="white", width=float('inf'))
        ]))

    # --- START APP ---
    page.add(current_view)
    navigate_to("dashboard")

# --- EXECUTION ---
if __name__ == "__main__":
    ft.app(target=main)