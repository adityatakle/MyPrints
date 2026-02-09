import win32print
import win32con
import subprocess
import os
import requests
from datetime import timedelta, datetime, timezone
import json
import sys
import time

SUMATRA_PATH = r"C:\Users\adity\Downloads\printo\SumatraPDF-3.5.2-64.exe"
FOLDER_PATH = r"C:\Users\adity\Downloads\printo\temp_folder"
BASE_URL = 'https://5cqwb04t-8000.inc1.devtunnels.ms/'
# Page types supported
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
        print(f"Error checking {printer_name}: {e}")
        # Default to safe values
        supports_color = False
        supports_duplex = False
        paper_names = []

    # FIX: Keys must match what the main loop expects ("name" instead of "printer_name")
    data = {
        "printer_info": {
            "name" : printer_name, # Changed from "printer_name" to "name"
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
        return json.dumps(status_entry) # Returns JSON string, note that logic below might need dict

    except Exception as e:
        error_response = {
            "name": printer_name,
            "status": "Connection Failed",
            "error": True,
            "message": str(e)
        }

        return error_response 

# Corrected get_status to return DICT not JSON STRING for internal use
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


def print_file(file_path, printer_name, page_type):
    # 1. DEBUG: Check if file actually exists where we think it is
    if not os.path.exists(file_path):
        print(f"[!] CRITICAL ERROR: File missing at: {file_path}")
        return False

    print_settings = f'paper={page_type},fit'

    try:
        command = [
            SUMATRA_PATH,
            "-print-to", printer_name,
            "-print-settings", print_settings,
            "-exit-on-print", 
            file_path
        ]
    except Exception as e:
        print(f"Print issue: {e}")
    
    print(f"Printing {file_path} by {printer_name}") # Debug command

    try:
        # 2. Run SumatraPDF
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[✓] SumatraPDF sent file to spooler.")
            return True
        else:
            print(f"[X] SumatraPDF Failed. Exit Code: {result.returncode}")
            print(f"    Error Output: {result.stderr}")
            print(f"    Standard Output: {result.stdout}")
            return False

    except Exception as e:
        print(f"[!] Python Exception trying to run subprocess : {e}")
        return False

def printer_info():
    printers = [p[2] for p in win32print.EnumPrinters(2)]
    
    # FIX: Changed to a LIST to match main loop expectation
    new_inventory = []

    for p_name in printers:
        json_str = get_printer_capabilities(p_name)
        p_data = json.loads(json_str)
        details = p_data["printer_info"]
        
        # Add to list
        new_inventory.append(details)

    try:
        existing_data = {}
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = {}

        # FIX: Save as "printer_info" because that is what your loop reads
        existing_data["printer_info"] = new_inventory
        print(f"{existing_data}")
        with open(DATA_FILE, 'w') as f:
            json.dump(existing_data, f, indent=4)
            
        print("Printer Inventory Updated Successfully.")

    except Exception as e:
        print(f"Error saving printer info: {e}")


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
    

    while True:
        # URL uses shop_id which is now correctly loaded
        try:
            url = f'{BASE_URL}my_shop/shop_connect/'
            
            response = requests.post(url, headers={'Shop-token':Shop_token, 'Shop-id':shop_id})
            
            if response.status_code != 200:
                print(f"❌ Error: {response.status_code}")
                
            if response.status_code == 200:
                items = response.json()
                items = items.get('items')
                print(f"Received {len(items)} jobs.")
                if not os.path.isdir(FOLDER_PATH):
                    try:
                        os.makedirs(FOLDER_PATH)
                    except Exception as e:
                        print(f"Unable to make dir : {e}")
                for item in items:
                    usable_printers = []
                    try:
                        with open(DATA_FILE, 'r') as r:
                            data = json.load(r)
                            for printer in data["printer_info"]:
                                if printer["name"] not in ['OneNote (Desktop)', 'Microsoft Print to PDF']:
                                    if item["page_type"] in printer["page_types"] and item["is_color"] == printer["is_color"] :        
                                        if printer["is_b2b"] or not item["is_b2b"]:
                                            usable_printers.append(printer["name"])
     
                    except Exception as e:
                        print(f"Exception while reading printers data : {e}")
                    if len(usable_printers) == 0:
                        print(f"No printer satisfies item's configurations.")
                        print("Moving to next item")
                        continue
                    if len(usable_printers) != 0:
                        success = False
                        while True:
                            for printer in usable_printers:
                                status = get_status(printer) 
                                if status["error"]:
                                    print(status)
                                    if usable_printers[-1] == printer:
                                        time.sleep(20)
                                    continue
                                
                                if status["readable_status"] == "Ready" and status["queue_size"] == 0:
                                    url = item["file_url"]
                                    file_name = item["file_name"]
                                    
                                    try:
                                        response = requests.get(url, stream=True)

                                        if response.status_code != 200:
                                            print("Server connection rejected.")

                                        if response.status_code == 200:
                                            if not os.path.exists(fr"{FOLDER_PATH}\{item['file_name']}"):
                                                with open(fr"{FOLDER_PATH}\{item['file_name']}", "wb") as f:
                                                    for chunk in response.iter_content(chunk_size=8192): 
                                                        f.write(chunk)
                                                    
                                                    # 1. Force Python to write everything to disk NOW
                                                    f.flush()
                                                    os.fsync(f.fileno()) 
                                            
                                                # 2. WAIT for Windows to unlock the file (Crucial Step)
                                                print("Download done. Waiting for file unlock...")
                                                time.sleep(3)
                                            try:
                                                file_path = fr"{FOLDER_PATH}\{item['file_name']}"
                                                try:
                                                    success = print_file(file_path, printer, item["page_type"])
                                                    time.sleep(1)
                                                    check = get_status(printer)
                                                    if check != "Running":
                                                        print(f"Error printing due to printer. {check}")
                                                except Exception as e:
                                                    print(f"print error: {e}")
                                                if success:
                                                    print("Added to queue for print.")
                                                
                                                try:
                                                    url = f'{BASE_URL}my_shop/file_update/'
                                                    response = requests.post(url, headers={'Shop-token':Shop_token, 'Shop-id':shop_id, 'item-id':str(item["id"])})
                                                except Exception as e:
                                                    print(f"Error Updating status after printing: {e}")                                          
                                                break
                                            except Exception as e:
                                                print(f"Error printing file. {e}")
                                    except Exception as e:
                                        print(f"Error while downloading file from server: {e}")
                                    
                                    # If we broke out of the download/print block successfully
                                    if success:
                                        break 
                                
                                if usable_printers[-1] == printer:
                                    time.sleep(20)
                                    continue
                                
                                if (status["readable_status"] == "Ready" and status["queue_size"] != 0) or (status["readable_status"] == "Printing"):
                                    continue
                                else:
                                    print(status["readable_status"])
                                    continue
                            
                            if success:
                                break
        except Exception as e:
            print(f"Connection error: {e}")
        print("Waiting for file....")
        time.sleep(5)