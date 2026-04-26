import win32print
import win32con
import subprocess
import os
import requests
from datetime import timedelta, datetime, timezone
import json
import sys
import time
import shutil
from pypdf import PdfReader

def write_log(message):
    with open("printo_logs.txt", "a", encoding='utf-8') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")

def get_base_path():    
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()
SUMATRA_PATH = os.path.join(BASE_PATH, 'SumatraPDF-3.5.2-64.exe')
FOLDER_PATH = os.path.join(BASE_PATH, 'temp_folder')
BASE_URL = 'https://4l65k8g7-8000.inc1.devtunnels.ms'
ALL_PAGES_TYPES = {
        1: "Letter",
        5: "Legal",
        8: "A3",
        9: "A4",
        11: "A5",
        66: "A2",
        70: "A6"
    }

def get_printer_capabilities(printer_name):
    """
    Checks if a Windows printer supports Color and Duplex (Back-to-Back).
    Updates the global PRINTER_INVENTORY dict.
    """
    try:
        # 1. Open Printer to get the Port Name
        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            info = win32print.GetPrinter(hPrinter, 2)
            port_name = info['pPortName']
        finally:
            win32print.ClosePrinter(hPrinter)

        # 2. Check COLOR Support
        color_result = win32print.DeviceCapabilities(printer_name, port_name, win32con.DC_COLORDEVICE)
        supports_color = (color_result == 1)

        # 3. Check DUPLEX (Back-to-Back) Support
        duplex_result = win32print.DeviceCapabilities(printer_name, port_name, win32con.DC_DUPLEX)
        supports_duplex = (duplex_result == 1)

        # 4. Check SUPPORTED PAGE TYPES
        supported_ids = win32print.DeviceCapabilities(printer_name, port_name, win32con.DC_PAPERS)
        paper_names = get_page_type(supported_ids)
        

    except Exception as e:
        write_log(f"Error checking {printer_name}: {e}")
        # Default to safe values
        supports_color = False
        supports_duplex = False
        paper_names = []

    data = {
        "printer_info": {
            "name" : printer_name,
            "is_color":supports_color,
            "is_b2b":supports_duplex,
            "page_types":paper_names
        }
    }

    return json.dumps(data)


def get_page_type(supported_ids):
    filtered_list = []
    for supported_id in supported_ids:
        if supported_id in ALL_PAGES_TYPES:
            filtered_list.append(ALL_PAGES_TYPES[supported_id])

    return filtered_list


def get_status(printer_name):
    try:
        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            data = win32print.GetPrinter(hPrinter, 2)
        finally:
            win32print.ClosePrinter(hPrinter)
        
        raw_code = data['Status']
        jobs_count = data['cJobs']
        readable_status = decode_status_code(raw_code)

        status_entry = {
            "name": printer_name,
            "status": readable_status,
            "queue_size": jobs_count,
            "raw_code": raw_code,
            "error": False,
            "readable_status": readable_status
        }
        return status_entry

    except Exception as e:
        error_response = {
            "name": printer_name,
            "status": "Connection Failed",
            "error": True,
            "message": str(e)
        }
        return error_response

def decode_status_code(code):
    if code == 0: return "Ready"
    
    STATUS_MAP = {
        0x00000001: "Paused",
        0x00000002: "Error",
        0x00000008: "Paper Jam",
        0x00000010: "Out of Paper",
        0x00000020: "Manual Feed Required",
        0x00000080: "Offline",
        0x00000400: "Printing",
        0x00100000: "User Intervention Required",
        0x00002000: "Door Open",
        0x00004000: "Server Unknown"
    }
    
    active_errors = []
    for bit_mask, description in STATUS_MAP.items():
        if code & bit_mask:
            active_errors.append(description)
            
    if not active_errors:
        return "Ready"
        
    return ", ".join(active_errors)


def print_file(file_path, printer_name, page_type, copies=1):
    """
    Sends a file to the specified printer using SumatraPDF.
    Dynamically decides between 'shrink' and 'fit' using pypdf.
    """
    
    if not os.path.exists(file_path):
        write_log(f"[!] CRITICAL ERROR: File missing at: {file_path}")
        return False

    scaling_logic = "shrink"
    try:
        reader = PdfReader(file_path)
        page = reader.pages[0]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        # Logic for your 65cm "Posters" (1860+ points)
        if width > 600 or height > 850:
            scaling_logic = "shrink"
            write_log(f"Detected Large File ({width:.0f}pts). Applying 'shrink'.")
        
        # Logic for small scans (e.g., ID cards) to ensure they are readable
        elif width < 500 or height < 750:
            scaling_logic = "fit"
            write_log(f"Detected Small File ({width:.0f}pts). Applying 'fit'.")
        
        else:
            scaling_logic = "shrink"
            
    except Exception as e:
        write_log(f"PDF Meta Error: {e}. Falling back to default 'shrink'.")

    print_settings = f"{copies}x,paper={page_type},{scaling_logic}" 
    
    command = [
        SUMATRA_PATH,
        "-print-to", printer_name,
        "-print-settings", print_settings,
        "-exit-on-print",
        file_path
    ]

    write_log(f"Attempting print: {os.path.basename(file_path)} -> {printer_name} ({scaling_logic})")

    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=False, 
            timeout=30 
        )

        if result.returncode == 0:
            write_log(f"SUCCESS: {os.path.basename(file_path)} sent to spooler.")
            return True
        else:
            write_log(f"SUMATRA ERROR (Code {result.returncode}):")
            if result.stderr:
                write_log(f"   Stderr: {result.stderr.strip()}")
            
            write_log("Retrying without specific print-settings...")
            fallback_command = [SUMATRA_PATH, "-print-to", printer_name, "-exit-on-print", file_path]
            fallback_result = subprocess.run(fallback_command, capture_output=True, text=True)
            
            if fallback_result.returncode == 0:
                write_log("Fallback success.")
                return True
                
            return False

    except subprocess.TimeoutExpired:
        write_log(f"TIMEOUT: Printer {printer_name} took too long to respond.")
        return False
    
    except Exception as e:
        write_log(f"PYTHON EXCEPTION: {str(e)}")
        return False

def printer_info():
    new_inventory = []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    
    try:
        printers = [p[2] for p in win32print.EnumPrinters(flags)]
        
        for p_name in printers:
            try:
                json_str = get_printer_capabilities(p_name)
                p_data = json.loads(json_str)
                details = p_data["printer_info"]
                new_inventory.append(details)
            except Exception as e:
                write_log(f"Skipping {p_name} due to capability error: {e}")

    except Exception as e:
        write_log(f"Critical Printer Scan Error: {e}")

    try:
        existing_data = {}
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = {}

       
        existing_data["printer_info"] = new_inventory
        write_log(f"{existing_data}")
        with open(DATA_FILE, 'w') as f:
            json.dump(existing_data, f, indent=4)
            
        write_log("Printer Inventory Updated Successfully.")

    except Exception as e:
        write_log(f"Error saving printer info: {e}")


if __name__ == "__main__":

    Shop_token = ''
    shop_id = ''
    DATA_FILE = "shop_data.json"
    DEFAULT_CONFIG = {
        "shop_token":'', # Key names should match checks below
        "shop_id":'',
        "updated_timestamp":''
    }
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        write_log(f"OPEN {DATA_FILE} and fill required data manually.")
        sys.exit()

        
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        if data["shop_token"] == "" or data["shop_id"] == "":
            write_log(f"DATA_FILE is empty. OPEN FILE AND FILL REQUIRED CREDENTIALS ('Shop_token' and 'Shop_id').")
            sys.exit()
        
        Shop_token = data["shop_token"]
        shop_id = data["shop_id"]

    except Exception as e:
        write_log(f"DATA_FILE read error: {e}")
    
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
        write_log(f"timestamp update write error: {e}")
        
    while True:
        # connect with server and get the data
        try:
            url = f'{BASE_URL}/my_shop/shop_connect/'
            response = requests.post(url, headers={'Shop-Token': Shop_token, 'Shop-Id': shop_id})
            
            if response.status_code != 200:
                write_log(f" Error connecting server: {response.status_code}")
                time.sleep(5)
                continue
            
            data = response.json()
            print_carts = data.get('print_carts', [])
            clean_carts = data.get('clean_carts', [])
            write_log(f'Received {len(print_carts)} jobs.')

            # clean folders
            for cart_id in clean_carts:
                try:
                    cart_path = os.path.join(FOLDER_PATH, str(cart_id))
                    if os.path.exists(cart_path):
                        shutil.rmtree(cart_path)
                        requests.post(f'{BASE_URL}/my_shop/file_update/', 
                            headers={'Shop-Token': Shop_token, 'Shop-Id': shop_id, 'Cart-Id': str(cart_id), 'Update-Type': 'cleaned'})
                        write_log(f"Cleaned up cart: {cart_id}")
                except Exception as e:
                    write_log(f'Cleanup issue: {e}')

            # mark 2 carts as processing
            for i, cart in enumerate(print_carts):
                if i >= 2: break
                try:
                    requests.post(f'{BASE_URL}/my_shop/file_update/', 
                        headers={'Shop-Token': Shop_token, 'Shop-Id': shop_id, 'Cart-Id': str(cart["id"]), 'Update-Type': 'processing'})
                except Exception as e:
                    write_log(f'Processing update error: {e}')

            # --- PRINTING LOOP ---
            for i, cart in enumerate(print_carts):
                if i >= 2: 
                    break 
                
                cart_dir = os.path.join(FOLDER_PATH, str(cart['id']))
                os.makedirs(cart_dir, exist_ok=True)


                usable_printers = []
                try:
                    with open(DATA_FILE, 'r') as r:
                        printer_data = json.load(r)
                        for printer in printer_data["printer_info"]:
                            if printer["name"] not in ['OneNote (Desktop)', 'Microsoft Print to PDF']:
                                if 'A4' in printer["page_types"] and not printer["is_color"] :        
                                        if printer["is_b2b"] or not cart["is_b2b"]:
                                            usable_printers.append({
                                                'name':printer['name'],
                                                'queue':get_status(printer['name']).get('queue_size', 0)
                                            })
                except Exception as e:
                    write_log(f"Printer read error: {e}")

                if not usable_printers:
                    write_log(f"No printer for Cart {cart['id']}")
                    continue

                usable_printers.sort(key=lambda x: x.get('queue', 0))

                # --- ITEM DOWNLOAD & PRINT ---
                for item in cart['items']:
                    success = False
                    retries = 0
                    while not success and retries < 3:
                        for printer in usable_printers:
                            status = get_status(printer['name'])
                            if status['readable_status'] == 'Ready':
                                file_path = os.path.join(cart_dir, item['file_name'])
                                
                                try:
                                    # A. DOWNLOAD (Robust Chunked Method)
                                    if not os.path.exists(file_path):
                                        write_log(f"Downloading: {item['file_name']}...")
                                        resp = requests.get(item['file_url'], stream=True, timeout=20)
                                        
                                        if resp.status_code == 200:
                                            with open(file_path, "wb") as f:
                                                for chunk in resp.iter_content(chunk_size=8192):
                                                    if chunk:
                                                        f.write(chunk)
                                                f.flush() # Force write to buffer
                                                os.fsync(f.fileno()) # Force write to disk (prevents Windows lock issues)
                                            
                                            write_log("Download complete. Syncing...")
                                            time.sleep(2) # Final buffer for SSD latency
                                        else:
                                            write_log(f"Download rejected by server: {resp.status_code}")
                                            retries += 1
                                            break

                                    # B. PRINT
                                    success = print_file(file_path, printer['name'], item["page_type"], item["copies"])
                                    if success:
                                        write_log(f"SUCCESS: {item['file_name']} is at the spooler.")
                                        # Notify backend
                                        try:
                                            requests.post(f'{BASE_URL}/my_shop/file_update/', 
                                                headers={
                                                    'Shop-Token': Shop_token, 
                                                    'Shop-Id': shop_id, 
                                                    'Item-Id': str(item["id"]), 
                                                    'Update-Type': 'printed'
                                                })
                                            
                                        except Exception as e:
                                            write_log(f"Error while marking file {item['file_name']} as success: {e}")
                                        break
                                    else:
                                        retries += 1
                                        

                                except Exception as e:
                                    write_log(f"Item Processing Error: {e}")
                                    retries += 1
                                    break 
                            else:
                                write_log(f" {printer['name']} not Ready...")
                                if printer == usable_printers[-1]:
                                    write_log(f" All printers are busy waiting 3sec before retrying...")
                                    time.sleep(3) 
                                continue
                        if not success:
                            write_log(f'Tried retrying file {retries}/{3} times.')
                    if not success:
                        write_log(f"GIVING UP on {item['file_name']} after {retries} attempts. Moving to next item.")                
        except Exception as e:
            write_log(f"Main Loop Connection error: {e}")
        
        time.sleep(5)