import customtkinter as ctk
import ctypes, sys, os, threading, time
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
from plyer import notification

# --- 管理者権限のチェック ---
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# 管理者権限がない場合は、昇格を求めて再起動
if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 基本設定
        self.version = "v1.0.0"
        self.title(f"Focus {self.version}")
        
        # 完璧な白銀比サイズ (400x428)
        self.geometry("400x428")
        self.resizable(False, False) 
        
        # パス・フラグ設定
        self.hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        self.config_file = "config.txt"
        self.redirect = "127.0.0.1"
        self.is_timer_running = False

        # 設定の読み込み（保存された解除時間とブラックリスト）
        self.last_minutes, self.blacklist = self.load_config()

        # UI構築
        self.tabview = ctk.CTkTabview(self, width=380, height=408)
        self.tabview.pack(padx=10, pady=(5, 5))
        
        self.tab_main = self.tabview.add("タイマー")
        self.tab_config = self.tabview.add("設定")

        self.setup_main_tab()
        self.setup_config_tab()
        
        # ウィンドウ終了時の挙動（トレイに隠す）
        self.protocol('WM_DELETE_WINDOW', self.hide_window)

        # 初期状態：ブロック開始
        self.block()
        
        # トレイアイコン作成
        self.create_tray_icon()
        
        # 起動時はウィンドウを隠してトレイに常駐
        self.withdraw()

    def setup_main_tab(self):
        """タイマー画面のセットアップ"""
        self.status_label = ctk.CTkLabel(self.tab_main, text="現在：制限中 🔥", font=("Yu Gothic", 20, "bold"), text_color="#E74C3C")
        self.status_label.pack(pady=(16, 4))

        self.timer_label = ctk.CTkLabel(self.tab_main, text="00:00", font=("Consolas", 52))
        self.timer_label.pack(pady=4)

        self.instruction_label = ctk.CTkLabel(
            self.tab_main, 
            text="解除する時間（分）:", 
            font=("Yu Gothic", 16, "bold")
        )
        self.instruction_label.pack(pady=(10, 0))
        
        self.time_entry = ctk.CTkEntry(self.tab_main, width=110, height=32, font=("Yu Gothic", 16), justify="center")
        self.time_entry.insert(0, self.last_minutes)
        self.time_entry.pack(pady=6)
        
        self.btn_unblock_timer = ctk.CTkButton(
            self.tab_main, 
            text="一時解除スタート", 
            command=self.start_unblock_timer, 
            fg_color="#34495E",
            hover_color="#2C3E50",
            height=80,             
            font=("Yu Gothic", 20, "bold") 
        )
        self.btn_unblock_timer.pack(pady=(16, 12), padx=30, fill="x")

    def setup_config_tab(self):
        """設定画面のセットアップ"""
        self.entry = ctk.CTkEntry(self.tab_config, placeholder_text="example.com", height=32)
        self.entry.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkButton(self.tab_config, text="追加", command=self.add_site, height=30).pack(pady=5)
        
        self.textbox = ctk.CTkTextbox(self.tab_config, height=188) 
        self.textbox.pack(pady=10, padx=20, fill="both")
        
        # バージョン表示
        self.version_label = ctk.CTkLabel(
            self.tab_config, 
            text=f"Version {self.version}", 
            font=("Yu Gothic", 10), 
            text_color="gray"
        )
        self.version_label.pack(side="bottom", anchor="se", padx=10, pady=5)
        
        self.update_list_display()

    # --- 構成・保存機能 ---
    def load_config(self):
        default_time = "15"
        default_list = ["youtube.com", "www.youtube.com", "instagram.com", "www.instagram.com"]
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    if lines:
                        return lines[0], (lines[1:] if len(lines) > 1 else default_list)
            except: pass
        return default_time, default_list

    def save_config(self):
        current_time = self.time_entry.get().strip() or "15"
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                f.write(current_time + "\n")
                for site in self.blacklist:
                    f.write(site + "\n")
        except: pass

    def add_site(self):
        site = self.entry.get().strip()
        if site and site not in self.blacklist:
            self.blacklist.append(site)
            self.save_config()
            self.update_list_display()
            self.block() # リスト更新時に即座に反映
            self.entry.delete(0, 'end')

    def update_list_display(self):
        self.textbox.delete("0.0", "end")
        self.textbox.insert("0.0", "\n".join(self.blacklist))

    # --- トレイ・ウィンドウ制御 ---
    def create_tray_icon(self):
        width, height = 64, 64
        image = Image.new('RGB', (width, height), (30, 30, 30))
        dc = ImageDraw.Draw(image)
        dc.ellipse((10, 10, 54, 54), fill=(30, 144, 255))
        menu = (item('表示', self.show_window, default=True), item('終了', self.quit_app))
        self.tray_icon = pystray.Icon("focus_timer", image, f"Focus {self.version}", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_window(self):
        self.save_config()
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self):
        self.save_config()
        self.block() # 終了時は必ずブロック状態に戻す
        self.tray_icon.stop()
        self.quit()

    # --- ブロックロジック ---
    def block(self):
        try:
            with open(self.hosts_path, "r", encoding="utf-8") as f: content = f.read()
            with open(self.hosts_path, "a", encoding="utf-8") as f:
                for site in self.blacklist:
                    if site not in content: f.write(f"\n{self.redirect} {site}")
            self.status_label.configure(text="現在：制限中 🔥", text_color="#E74C3C")
        except: pass

    def unblock(self):
        try:
            with open(self.hosts_path, "r", encoding="utf-8") as f: lines = f.readlines()
            with open(self.hosts_path, "w", encoding="utf-8") as f:
                for line in lines:
                    if not any(site in line for site in self.blacklist): f.write(line)
            self.status_label.configure(text="一時解除中 🔓", text_color="#2ECC71")
        except: pass

    def start_unblock_timer(self):
        if self.is_timer_running: return
        try:
            val = self.time_entry.get().strip()
            if not val or not val.isdigit(): return
            
            self.save_config()
            self.btn_unblock_timer.configure(state="disabled", text="一時解除中...")
            self.is_timer_running = True
            self.unblock()
            threading.Thread(target=self.countdown, args=(int(val) * 60,), daemon=True).start()
        except: pass

    def countdown(self, count):
        while count > 0:
            mins, secs = divmod(count, 60)
            self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
            time.sleep(1)
            count -= 1
        
        self.is_timer_running = False
        self.timer_label.configure(text="00:00")
        self.btn_unblock_timer.configure(state="normal", text="一時解除スタート")
        self.block()

        # タイマー終了通知
        try:
            notification.notify(
                title="Focus",
                message="制限時間が終了しました。集中モードを再開します！",
                app_name="Focus",
                timeout=10
            )
        except: pass

if __name__ == "__main__":
    app = App()
    app.mainloop()