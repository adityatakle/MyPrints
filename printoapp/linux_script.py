import os
import re
import shutil
import cups
import requests
import json
from datetime import timedelta, datetime, timezone
import sys
import time

FOLDER_PATH = r"/home/aditya-takle/Downloads/Telegram Desktop/printo/temp_folder_linux"
BASE_URL = 'https://5cqwb04t-8000.inc1.devtunnels.ms/'

# CHANGED: Now stores a dict -> {'Canon': {'color': False, 'duplex': True}}
PRINTER_INVENTORY = {} 

def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name)

def initialize_inventory():
    """
    1) Delete the cache folder if it already exists and make a new one.
    2) Fetch the printer names and detect capabilities (Color & Duplex).
    """
    PRINTER_INVENTORY.clear()

    # --- 1. CLEAR CACHE FOLDER ---
    if os.path.exists(FOLDER_PATH):
        try:
            shutil.rmtree(FOLDER_PATH)
        except Exception as e:
            print(f"Warning: Could not clear cache folder '{FOLDER_PATH}': {e}")

    # --- 2. CREATE FRESH FOLDER ---
    try:
        os.makedirs(FOLDER_PATH, exist_ok=True)
    except Exception as e:
        print(f"Error: Could not create cache folder '{FOLDER_PATH}': {e}")
        return

    # --- 3. CONNECT TO CUPS ---
    try:
        conn = cups.Connection()
        printers = conn.getPrinters()
    except Exception as e:
        print(f"Error: Could not connect to CUPS: {e}")
        return

    # --- 4. PROCESS EACH PRINTER ---
    for name in printers:
        # Now returns a dictionary: {'color': True/False, 'duplex': True/False}
        caps = check_printer_capabilities(conn, name)
        PRINTER_INVENTORY[name] = caps
        print(f"Initialized {name}: Color={caps['color']}, B2B={caps['duplex']}")

def check_printer_capabilities(conn: cups.Connection, printer_name: str) -> dict:
    """
    Analyzes the PPD to find:
    1. Color Support (True/False)
    2. Duplex/B2B Support (True/False)
    """
    # Default result
    result = {'color': False, 'duplex': False}
    
    safe_name = _sanitize_filename(printer_name)
    final_path = os.path.join(FOLDER_PATH, f"{safe_name}.ppd")

    try:
        # Fetch & Cache PPD
        temp_path = conn.getPPD(printer_name)
        shutil.move(temp_path, final_path)
        ppd = cups.PPD(final_path)

        # ==============================
        # 1. DETECT COLOR (Your Waterfall Logic)
        # ==============================
        
        found_color = False
        
        # Check A: ColorModel
        option = ppd.findOption("ColorModel")
        if option and option.choices:
            for choice in option.choices:
                text_val = (choice.get("text") or "").lower()
                choice_name = (choice.get("choice") or "").lower()
                if any(kw in text_val or kw in choice_name for kw in ("color", "rgb", "cmyk")):
                    found_color = True
                    break
        
        # Check B: PrintMode (Fallback)
        if not found_color:
            option = ppd.findOption("PrintMode")
            if option and option.choices:
                for choice in option.choices:
                    text_val = (choice.get("text") or "").lower()
                    if any(kw in text_val for kw in ("color", "rgb", "cmyk")):
                        found_color = True
                        break
        
        # Check C: ColorDevice Attribute
        if not found_color:
            attr = ppd.findAttr("ColorDevice")
            if attr and attr.value and attr.value.lower() == "true":
                found_color = True

        result['color'] = found_color

        # ==============================
        # 2. DETECT DUPLEX (B2B)
        # ==============================
        
        # The standard PPD option is named "Duplex"
        opt_duplex = ppd.findOption("Duplex")
        
        if opt_duplex and opt_duplex.choices:
            for choice in opt_duplex.choices:
                # "DuplexNoTumble" = Standard Book Style (Long Edge)
                # "DuplexTumble"   = Calendar Style (Short Edge)
                # If either exists, the hardware supports 2-sided printing.
                c_name = choice['choice']
                if c_name in ["DuplexNoTumble", "DuplexTumble"]:
                    result['duplex'] = True
                    break
                    
    except Exception as e:
        print(f"Error checking capabilities for '{printer_name}': {e}")
        # Return whatever we found so far (defaults are False)

    return result


status_details = {} # Global Dictionary

def get_printer_details(printer_name):
    try:
        conn = cups.Connection()
        
        # OPTIMIZATION: Don't fetch ALL printers. 
        # Just ask CUPS for the specific one you want. It's much faster.
        # attributes=['printer-state'] ensures we fetch minimal data.
        attributes = conn.getPrinterAttributes(printer_name, requested_attributes=['printer-state'])
        
        # A. Extract Status
        state_code = attributes.get('printer-state')
        
        if state_code == 3:
            status_text = "Idle"
        elif state_code == 4:
            status_text = "Processing"
        elif state_code == 5:
            status_text = "Stopped"
        else:
            status_text = f"Unknown ({state_code})"
        
        # B. UPDATE THE DICTIONARY
        # This one line handles both "Adding New" and "Updating Existing"
        status_details[printer_name] = status_text
        
        return 0
        
    except Exception as e:
        print(f"Cups connection error: {e}")
        # Optional: Mark as offline in the dict if connection fails
        status_details[printer_name] = "Offline/Error"


def print_document(printer_name, file_path, page_type, is_color, is_b2b, copies, job_title="My Print Job"):
    """
    Sends a file to the specified CUPS printer.
    Returns: Job ID (int) on success, or None on error.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None

    try:
        conn = cups.Connection()
        
        # --- 1. SET OPTIONS ---
        # These are standard CUPS options. 
        options = {
            "fit-to-page": "True",       # Resizes large images to fit paper
            "print-quality": "4",       # Normal photo quality
        }

        options["media"] = page_type.capitalize()
        if not is_color:
            options["ColorModel"] = "Gray"

        if is_b2b:
            options["sides"] = "two-sided-long-edge"
        else:
            options["sides"] = "one-sided"
        options["copies"] = str(copies)

        # --- 2. SEND TO PRINTER ---
        # Arguments: (Printer Name, File Path, Job Title, Options Dict)
        job_id = conn.printFile(printer_name, file_path, job_title, options)
        
        print(f"Success! Job {job_id} sent to {printer_name}.")
        return job_id

    except cups.IPPError as e:
        print(f"CUPS Printing Error: {e}")
        return None



if __name__ == "__main__":

    SHOP_ID = ''
    SHOP_TOKEN = ''
    DATA_FILE = 'shop_data.json'
    DEFAULT_CONFIG = {
        "shop_token":'', # Key names should match checks below
        "shop_id":'',
        "updated_timestamp":''
    }
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        print(f"OPEN {DATA_FILE} and fill required data manually.")
        sys.exit()

        
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        if data["shop_token"] == "" or data["shop_id"] == "":
            print(f"DATA_FILE is empty. OPEN FILE AND FILL REQUIRED CREDENTIALS ('Shop_token' and 'Shop_id').")
            sys.exit()
        
        # FIX: Assign variables so they aren't empty in the URL request
        Shop_token = data["shop_token"]
        shop_id = data["shop_id"]

    except Exception as e:
        print(f"DATA_FILE read error: {e}")
    
    ist_offset = timezone(timedelta(hours=5, minutes=30))
            
    printer_info()
    now_ist = datetime.now(ist_offset).strftime("%Y-%m-%d %H:%M:%S")
            
    # Refresh data after printer_info update
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    data["updated_timestamp"] = now_ist 
            
    try:
        with open(DATA_FILE, 'w') as r:
            json.dump(data, r, indent=4)
    except Exception as e:
        print(f"timestamp update write error: {e}")
    