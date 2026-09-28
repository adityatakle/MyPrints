import win32print # type: ignore
import win32con # type: ignore
import subprocess
import os
import requests
from datetime import timedelta, datetime, timezone
import json
import sys
import time
import shutil
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from io import BytesIO
from pypdf import PdfReader, PdfWriter

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
BASE_URL = 'https://myprints.in'
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

    return data


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


PAPER_SIZES_PT = {
    "A4":     (595.28, 841.89),
    "A3":     (841.89, 1190.55),
    "A5":     (419.53, 595.28),
    "LETTER": (612, 792),
    "LEGAL":  (612, 1008),
}


def print_file(file_path, printer_name, page_type, copies, is_duplex, is_color, is_portrait, is_long_edge):
    """
    Sends a file to the specified printer using SumatraPDF.
    """
    color = 'monochrome,'
    side = 'simplex,'
    orientation = 'portrait,'
    scaling_logic = "shrink"
    if not is_portrait:
        orientation = 'landscape,'
    if is_duplex and is_long_edge:
        side = 'duplexlong,'
    elif is_duplex and not is_long_edge:
        side = 'duplexshort,'
    if is_color:
        color = 'color,'
    if not os.path.exists(file_path):
        write_log(f"[!] CRITICAL ERROR: File missing at: {file_path}")
        return False


    print_settings = f"{color}{orientation}{side}{copies}x,paper={page_type},{scaling_logic},disable-auto-rotation" 
    write_log(f"Print settings: {print_settings}")
    command = [
        SUMATRA_PATH,
        "-print-to", printer_name,
        "-print-settings", print_settings,
        "-exit-when-done",
        file_path
    ]
    
    write_log(f"Attempting print: {os.path.basename(file_path)} -> {printer_name} ({scaling_logic})")
    write_log(f"command sent to print: {command}")
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
                details = p_data["printer_info"]['name']
                new_inventory.append(details)
            except Exception as e:
                write_log(f"Skipping {p_name} due to capability error: {e}")

    except Exception as e:
        write_log(f"Critical Printer Scan Error: {e}")
    write_log(new_inventory)
    return new_inventory

def test_local_pdf_stamping(pickup_code="0000", prepend_blank=False):
    static_base   = os.path.join(BASE_PATH)
    template_path = os.path.join(static_base, 'FP_template.pdf')

    if not os.path.exists(template_path):
        return None

    PW, PH = 1860.0, 2631.12
    otp_str = str(pickup_code).zfill(4)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))

    # Box 1 — top-left small reference box
    c.setFont("Helvetica-Bold", 52)
    c.setFillColor(HexColor("#000000"))
    tw = c.stringWidth(otp_str, "Helvetica-Bold", 52)
    c.drawString(178 - tw/2, 2426 - 26, otp_str)

    # Box 2 — main center inner box (large OTP number)
    c.setFont("Helvetica-Bold", 260)
    c.setFillColor(HexColor("#000000"))
    tw = c.stringWidth(otp_str, "Helvetica-Bold", 260)
    c.drawString(1090 - tw/2, 1371 - 260*0.35, otp_str)

    # Box 3 — bottom-right small reference box
    c.setFont("Helvetica-Bold", 52)
    c.setFillColor(HexColor("#000000"))
    tw = c.stringWidth(otp_str, "Helvetica-Bold", 52)
    c.drawString(1674 - tw/2, 153 - 26, otp_str)

    c.save()
    buf.seek(0)

    template_reader = PdfReader(template_path)
    overlay_reader  = PdfReader(buf)
    main_page = template_reader.pages[0]
    main_page.merge_page(overlay_reader.pages[0])

    writer = PdfWriter()
    if prepend_blank:
        writer.add_blank_page(width=PW, height=PH)
    writer.add_page(main_page)

    final_pdf_buffer = BytesIO()
    writer.write(final_pdf_buffer)
    final_pdf_buffer.seek(0)
    return final_pdf_buffer

if __name__ == "__main__":

    shop_token = 'ax89sdMr37p1itJwDzwknOKgrw-Sgtg4HF72bViGSc0'
    shop_id = '3'
    printer_name = ''
    DATA_FILE = "shop_data.json"
    DEFAULT_CONFIG = {
        "printer_name":''
    }

    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        if data["printer_name"] == "":
            write_log(f"Printer no set correctly. SET MANUALLY.")
            sys.exit()
        
        printer_name = data['printer_name']

    except Exception as e:
        write_log(f"DATA_FILE read error: {e}")
        sys.exit()

    try:
        resp = requests.post(f'{BASE_URL}/api/shop_handshake', 
                             headers ={'Shop-Id':shop_id,'Shop-Token':shop_token})
        if resp.status_code == 200:
            resp_data = resp.json()
            page_types = resp_data['page_types'] or []
            is_color = resp_data['is_color'] or False
            is_b2b = resp_data['is_b2b'] or False
            printer_names = printer_info()
            if printer_name in printer_names:
                capabilities = get_printer_capabilities(printer_name)
                result = capabilities['printer_info']
                check_page_type = bool(set(page_types) & set(result['page_types']))
                check_color = not is_color or result['is_color']
                check_b2b = not is_b2b or result['is_b2b']
                if not (check_page_type and check_b2b and check_color):
                    write_log('Set Printer doesnt have set configs.')
                    sys.exit()
        else:
            write_log(f'Error connecting server: {resp.status_code}')
    except Exception as e:
        write_log(f'SHOP HANDSHAKE ERROR: {e}')
        sys.exit()
        

    while True:
        # connect with server and get the data
        try:
            url = f'{BASE_URL}/my_shop/shop_connect/'
            response = requests.post(url, headers={'Shop-Token': shop_token, 'Shop-Id': shop_id})
            
            if response.status_code != 200:
                write_log(f" Error connecting server: {response.status_code}")
                time.sleep(5)
                continue
            
            data = response.json()
            print_carts = data.get('print_carts', [])
            clean_carts = data.get('clean_carts', [])
            write_log(f'Received {len(print_carts)} jobs.')
            write_log(print_carts)
            write_log(clean_carts)
            # clean folders
            for cart_id in clean_carts:
                try:
                    cart_path = os.path.join(FOLDER_PATH, str(cart_id))
                    if os.path.exists(cart_path):
                        shutil.rmtree(cart_path)
                        clean_resp = requests.post(f'{BASE_URL}/my_shop/file_update/', 
                            headers={'Shop-Token': shop_token, 'Shop-Id': shop_id, 'Cart-Id': str(cart_id), 'Update-Type': 'cleaned'})
                        if clean_resp.status_code == 200:
                            write_log(f"Cleaned up cart and updated database: {cart_id}")
                except Exception as e:
                    write_log(f'Cleanup issue: {e}')
            i = 0
            # mark 2 carts as processing and edit file_link
            for cart in print_carts:
                if i >= 2:
                    break
                if not cart['is_processing']:
                    try:
                        resp = requests.post(f'{BASE_URL}/my_shop/file_update/', 
                            headers={'Shop-Token': shop_token, 'Shop-Id': shop_id, 'Cart-Id': str(cart["id"]), 'Update-Type': 'processing'})
                        if resp.status_code == 200:
                            res_data = resp.json()
                            if res_data['status'] == 'success':
                                
                                # 💡 FIX: Pull from res_data (the file_update endpoint response payload)
                                new_links = {link['id']: link['file_url'] for link in res_data.get('cart_data', [])}
                                
                                # 2. Update local items in one pass
                                for item in cart['items']:
                                    if item['id'] in new_links:
                                        item['file_url'] = new_links[item['id']]
                                
                                # Mark locally as processing
                                cart['is_processing'] = True
                                i += 1
                    except Exception as e:
                        write_log(f'Processing update error: {e}')

            # --- PRINTING LOOP ---
            for cart in print_carts: 
                if cart['is_processing'] and any(item.get('file_url') for item in cart['items']):
                    cart_dir = os.path.join(FOLDER_PATH, str(cart['id']))
                    os.makedirs(cart_dir, exist_ok=True)

                    printer_queue = get_status(printer_name).get('queue_size', 0)
                    if printer_queue > 10:
                        time.sleep(10)

                    otp = cart['pickup_code']
                    fp = test_local_pdf_stamping(otp)
                    file_path = os.path.join(cart_dir, 'front_page.pdf')
                    with open(file_path, 'wb') as f:
                        f.write(fp.getvalue() if hasattr(fp, 'getvalue') else fp)
                    print_file(file_path, printer_name, 'A4', 1, False, False, True, False)


                    # --- ITEM DOWNLOAD & PRINT ---
                    for item in cart['items']:
                        success = False
                        retries = 0

                        while not success:
                            status = get_status(printer_name)
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
                                            time.sleep(1.5) # Final buffer for SSD latency
                                        else:
                                            write_log(f"Download rejected by server: {resp.status_code}")
                                            time.sleep(15)
                                            continue

                                    # B. PRINT
                                    success = print_file(file_path, printer_name, item["page_type"], item["copies"], item["is_b2b"], item['is_color'], item['is_portrait'], item['is_long_edge'])
                                    if success:
                                        write_log(f"SUCCESS: {item['file_name']} is at the spooler.")
                                        # Notify backend
                                        try:
                                            requests.post(f'{BASE_URL}/my_shop/file_update/', 
                                                headers={
                                                    'Shop-Token': shop_token, 
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
                                    time.sleep(5)

                            else:
                                write_log(f" {printer_name} not Ready...")
                                time.sleep(5)
                        if not success:
                            write_log(f'Tried retrying file {retries}/{3} times.')
                    if not success:
                        write_log(f"GIVING UP on {item['file_name']} after {retries} attempts. Moving to next item.")
                    otp = cart['pickup_code']
                    lp = test_local_pdf_stamping(otp,True)
                    file_path = os.path.join(cart_dir, 'last_page.pdf')
                    with open(file_path, 'wb') as f:
                        f.write(lp.getvalue() if hasattr(lp, 'getvalue') else lp)
                    print_file(file_path, printer_name, 'A4', 1, True, False, True, True)           
        except Exception as e:
            write_log(f"Main Loop Connection error: {e}")
        
        time.sleep(5)