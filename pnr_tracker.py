#!/usr/bin/env python3
"""
Indian Railways PNR Status Auto-Tracker & Notifier
Author: Antigravity
Configured for:
  PNRs: 2844588144, 2525809503
  Recipients: 7678668484, 9810713715, 9871845476
  Channels: Android Push Notifications (ntfy), WhatsApp (CallMeBot), Desktop
"""

import os
import sys
import json
import time
import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import urllib.parse
import subprocess
import requests

# Ensure console supports UTF-8 on Windows
if sys.platform == "win32":
    try:
        if sys.stdout.encoding != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr.encoding != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pnr_state.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"[!] Error: Configuration file '{CONFIG_FILE}' not found.")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Warning reading state file: {e}. Starting fresh.")
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[!] Error saving state file: {e}")

# ----------------- PNR API Fetcher -----------------

def fetch_pnr_status(pnr_number):
    """
    Fetches real-time PNR status from Indian Railways / ConfirmTkt API endpoint.
    """
    clean_pnr = str(pnr_number).strip().replace(" ", "")
    if len(clean_pnr) != 10 or not clean_pnr.isdigit():
        print(f"[!] Invalid PNR format: '{pnr_number}'. PNR must be 10 digits.")
        return None

    url = f"https://cttrainsapi.confirmtkt.com/api/v2/ctpro/mweb/{clean_pnr}?querysource=ct-web&locale=en&getHighChanceText=true&livePnr=false"
    headers = {
        "Accept": "*/*",
        "ApiKey": "ct-web!2$",
        "ClientId": "ct-web",
        "Content-Type": "application/json",
        "Origin": "https://www.confirmtkt.com",
        "Referer": "https://www.confirmtkt.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    payload = json.dumps({"proPlanName": "CP7", "emailId": "", "tempToken": ""})

    for attempt in range(1, 4):
        try:
            resp = requests.post(url, headers=headers, data=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                pnr_resp = data.get("data", {}).get("pnrResponse", {})
                
                err = pnr_resp.get("error")
                if err:
                    print(f"[-] PNR {clean_pnr} notice: {err}")
                    return {"error": err, "pnr": clean_pnr}

                # Parse passenger status
                passengers = []
                for p in pnr_resp.get("passengerStatus", []):
                    coach = (p.get("currentCoachId") or p.get("coach") or "").strip()
                    berth = (str(p.get("currentBerthNo") or p.get("berth") or "")).strip()
                    berth_code = (p.get("currentBerthCode") or "").strip()
                    curr_st = (p.get("currentStatus") or "").strip()

                    passengers.append({
                        "number": p.get("number"),
                        "booking_status": (p.get("bookingStatus") or "").strip(),
                        "current_status": curr_st,
                        "coach": coach,
                        "berth": berth if "CNF" in curr_st or coach else "",
                        "berth_code": berth_code if "CNF" in curr_st or coach else "",
                        "prediction": (p.get("prediction") or "").strip()
                    })

                return {
                    "pnr": clean_pnr,
                    "train_no": pnr_resp.get("trainNo", "N/A"),
                    "train_name": pnr_resp.get("trainName", "N/A"),
                    "doj": pnr_resp.get("doj", "N/A"),
                    "source": pnr_resp.get("sourceName", pnr_resp.get("from", "N/A")),
                    "destination": pnr_resp.get("destinationName", pnr_resp.get("to", "N/A")),
                    "from_code": pnr_resp.get("from", ""),
                    "to_code": pnr_resp.get("to", ""),
                    "class": pnr_resp.get("class", "N/A"),
                    "chart_prepared": bool(pnr_resp.get("chartPrepared", False)),
                    "passengers": passengers,
                    "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                print(f"[!] HTTP error {resp.status_code} while checking PNR {clean_pnr} (attempt {attempt}/3)")
        except requests.exceptions.RequestException as e:
            print(f"[!] Network error on attempt {attempt}/3: {e}")
        time.sleep(2)

    return None

# ----------------- Message Formatter -----------------

def format_status_message(pnr_data, changes=None, title_prefix="PNR Update"):
    """
    Constructs a rich, readable status message detailing train, route, date, and seat/status.
    """
    train_line = f"Train: {pnr_data.get('train_no')} - {pnr_data.get('train_name')}"
    from_st = pnr_data.get('from_code') or pnr_data.get('source') or ''
    to_st = pnr_data.get('to_code') or pnr_data.get('destination') or ''
    route_line = f"Route: {from_st} -> {to_st}"
    date_line = f"Journey Date: {pnr_data.get('doj')} | Class: {pnr_data.get('class')}"
    chart_line = f"Chart Status: {'Chart Prepared (Final Seats Allocated)' if pnr_data.get('chart_prepared') else 'Chart Not Prepared Yet'}"

    # Passenger details
    passenger_lines = []
    for p in pnr_data.get("passengers", []):
        p_num = p.get("number")
        curr = p.get("current_status")
        book = p.get("booking_status")
        coach = p.get("coach")
        berth = p.get("berth")
        b_code = p.get("berth_code")
        pred = p.get("prediction")

        # Format seat details if confirmed
        seat_detail = ""
        if "CNF" in curr or "CONFIRM" in curr.upper():
            if coach or berth:
                b_str = f"Berth {berth}" if berth else ""
                c_str = f"Coach {coach}" if coach else ""
                code_str = f"({b_code})" if b_code else ""
                seat_detail = f" -> SEAT: {c_str} {b_str} {code_str}".strip()
            else:
                seat_detail = " -> CONFIRMED (Seat allotted on Charting)"
        elif "RAC" in curr:
            seat_detail = f" -> {curr} (Confirmed seat on board)"
        elif "WL" in curr:
            pred_str = f" [{pred}]" if pred else ""
            seat_detail = f" -> {curr}{pred_str}"
        else:
            seat_detail = f" -> {curr}"

        passenger_lines.append(f"  Passenger {p_num}: {book}{seat_detail}")

    passengers_block = "\n".join(passenger_lines)

    change_block = ""
    if changes:
        c_lines = "\n".join([f"  * {c}" for c in changes])
        change_block = f"\nChanges Detected:\n{c_lines}\n"

    msg = (
        f"{title_prefix}\n\n"
        f"PNR: {pnr_data['pnr']}\n"
        f"{train_line}\n"
        f"{route_line}\n"
        f"{date_line}\n"
        f"{chart_line}\n"
        f"{change_block}\n"
        f"Passenger Status / Seats:\n{passengers_block}\n\n"
        f"Last Checked: {pnr_data['last_checked']}"
    )
    return msg

# ----------------- Status Comparator -----------------

def check_for_updates(old_pnr_data, new_pnr_data):
    if not old_pnr_data:
        return False, "Initial status recorded", ""

    if new_pnr_data.get("error"):
        return False, "", ""

    changes = []
    old_passengers = {p.get("number"): p for p in old_pnr_data.get("passengers", [])}
    new_passengers = {p.get("number"): p for p in new_pnr_data.get("passengers", [])}

    for p_num, new_p in new_passengers.items():
        old_p = old_passengers.get(p_num)
        if not old_p:
            continue
        old_status = old_p.get("current_status", "").strip()
        new_status = new_p.get("current_status", "").strip()

        old_coach = old_p.get("coach", "").strip()
        new_coach = new_p.get("coach", "").strip()
        new_berth = new_p.get("berth", "").strip()

        if old_status != new_status:
            changes.append(f"Passenger {p_num}: {old_status} -> {new_status}")
        elif not old_coach and new_coach:
            changes.append(f"Passenger {p_num} Seat Allocated: Coach {new_coach}, Berth {new_berth}")

    # Check chart preparation status
    old_chart = old_pnr_data.get("chart_prepared", False)
    new_chart = new_pnr_data.get("chart_prepared", False)
    if not old_chart and new_chart:
        changes.append("CHART PREPARED! Final coach and seats allocated.")

    if not changes:
        return False, "No change", ""

    msg = format_status_message(new_pnr_data, changes, title_prefix="ALERT: PNR Ticket Status Updated!")
    return True, "; ".join(changes), msg

# ----------------- Notification Dispatchers -----------------

def notify_ntfy(topic, title, message):
    """
    Sends native mobile push notification via ntfy.sh.
    Instant broadcast to all Android/iOS phones subscribed to the topic.
    """
    if not topic:
        return False
    try:
        url = f"https://ntfy.sh/{topic}"
        headers = {
            "Title": title.encode("utf-8"),
            "Priority": "high",
            "Tags": "bullettrain_side,ticket"
        }
        res = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=10)
        if res.status_code == 200:
            print(f"  [OK] Push notification broadcast via ntfy (topic: {topic})")
            return True
        else:
            print(f"  [!] ntfy notification returned HTTP {res.status_code}")
    except Exception as e:
        print(f"  [!] Error sending ntfy push notification: {e}")
    return False

def notify_whatsapp_callmebot(recipients, message):
    """
    Sends WhatsApp message via CallMeBot gateway to all configured phone numbers.
    """
    if not recipients:
        return False
    success_count = 0
    for r in recipients:
        phone = r.get("phone", "").strip()
        api_key = r.get("api_key", "").strip()
        name = r.get("name", phone)
        if not phone or not api_key:
            print(f"  [i] WhatsApp not configured for {name} ({phone}) - missing API key. Skipping.")
            continue
        try:
            encoded_text = urllib.parse.quote(message)
            url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_text}&apikey={api_key}"
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                print(f"  [OK] Sent WhatsApp message to {name} ({phone})")
                success_count += 1
            else:
                print(f"  [!] CallMeBot returned HTTP {res.status_code} for {phone}: {res.text}")
        except Exception as e:
            print(f"  [!] Error sending WhatsApp message to {phone}: {e}")
    return success_count > 0

def notify_windows_desktop(title, message):
    if sys.platform != "win32":
        return False
    try:
        clean_title = title.replace("'", "").replace('"', '')
        first_line = message.split("\n")[0] if message else "Status update"
        clean_msg = first_line.replace("'", "").replace('"', '')
        ps_script = (
            "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
            "$n = New-Object Windows.Forms.NotifyIcon;"
            "$n.Icon = [System.Drawing.SystemIcons]::Information;"
            "$n.Visible = $True;"
            f"$n.ShowBalloonTip(4000, '{clean_title}', '{clean_msg}', [Windows.Forms.ToolTipIcon]::Info);"
        )
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                       capture_output=True, timeout=5)
        print("  [OK] Displayed Windows Desktop notification!")
        return True
    except Exception as e:
        print(f"  [!] Windows notification error: {e}")
    return False

def dispatch_notifications(config, title, message):
    cfg_notif = config.get("notifications", {})

    # 1. ntfy (Phone Push Notification for Android)
    if cfg_notif.get("ntfy", {}).get("enabled"):
        topic = cfg_notif["ntfy"].get("topic")
        notify_ntfy(topic, title, message)

    # 2. WhatsApp
    if cfg_notif.get("whatsapp_callmebot", {}).get("enabled"):
        wa_recipients = cfg_notif["whatsapp_callmebot"].get("recipients", [])
        notify_whatsapp_callmebot(wa_recipients, message)

    # 3. Windows Desktop
    if cfg_notif.get("windows_desktop", {}).get("enabled", True):
        notify_windows_desktop(title, message)

# ----------------- Main Tracking Logic -----------------

def run_check(force_notify=False):
    config = load_config()
    pnr_list = config.get("pnr_list", [])
    if not pnr_list:
        print("[!] No PNR numbers configured in config.json.")
        return

    state = load_state()
    print(f"\n=======================================================")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking {len(pnr_list)} PNR(s)...")
    print(f"=======================================================")

    for pnr in pnr_list:
        pnr_str = str(pnr).strip()
        print(f"\n[*] Querying PNR: {pnr_str}")
        res = fetch_pnr_status(pnr_str)
        if not res:
            print(f"[-] Could not retrieve data for PNR {pnr_str}")
            continue

        if res.get("error"):
            print(f"[-] Status: {res.get('error')}")
            continue

        print(f"    Train: {res['train_no']} - {res['train_name']}")
        print(f"    Route: {res['from_code']} -> {res['to_code']} | DOJ: {res['doj']} | Class: {res['class']}")
        print(f"    Chart Prepared: {'Yes' if res['chart_prepared'] else 'No'}")
        for p in res.get("passengers", []):
            coach_berth = f" [Coach: {p['coach']} Berth: {p['berth']}]" if p.get('coach') else ""
            print(f"    Passenger {p['number']}: Booking: {p['booking_status']} | Current: {p['current_status']}{coach_berth}")

        old_data = state.get(pnr_str)
        has_changed, change_summary, detailed_msg = check_for_updates(old_data, res)

        if not old_data:
            print(f"[+] Initial status recorded for PNR {pnr_str}.")
            state[pnr_str] = res
            save_state(state)
            if force_notify:
                title = f"Tracking Active: PNR {pnr_str} ({res['train_no']})"
                init_msg = format_status_message(res, title_prefix="PNR Tracking Activated")
                dispatch_notifications(config, title, init_msg)
        elif has_changed or force_notify:
            print(f"[UPDATE] Status changed: {change_summary}")
            state[pnr_str] = res
            save_state(state)
            title = f"PNR Update: {pnr_str} ({res['train_no']})"
            dispatch_notifications(config, title, detailed_msg)
        else:
            print(f"    [No updates since last check]")

    save_state(state)
    print(f"\n[OK] Check cycle completed.")

def broadcast_live_status():
    """
    Fetches the live status of all PNRs and immediately broadcasts to Android phones.
    """
    config = load_config()
    pnr_list = config.get("pnr_list", [])
    print("[*] Fetching live status and broadcasting to phones...")
    for pnr in pnr_list:
        res = fetch_pnr_status(str(pnr).strip())
        if res and not res.get("error"):
            title = f"Current Status: PNR {res['pnr']} ({res['train_no']})"
            msg = format_status_message(res, title_prefix="Indian Railways Live Status")
            dispatch_notifications(config, title, msg)
            time.sleep(1)

def test_notifications():
    print("[*] Testing enabled notification channels...")
    config = load_config()
    test_title = "IRCTC PNR Tracker - Test Alert"
    test_message = (
        "Test Alert from your Indian Railways PNR Tracker!\n\n"
        "Configured for phones: 7678668484, 9810713715, 9871845476\n"
        "Tracking PNRs: 2844588144 & 2525809503 (Shiv Ganga Exp)\n\n"
        "You will receive an instant push notification whenever your Waiting List or RAC seat status updates!"
    )
    dispatch_notifications(config, test_title, test_message)
    print("[OK] Test notifications dispatched.")

def main():
    parser = argparse.ArgumentParser(description="Indian Railways PNR Auto Tracker")
    parser.add_argument("--once", action="store_true", help="Run a single check and exit")
    parser.add_argument("--test", action="store_true", help="Send a test notification to verify your channels")
    parser.add_argument("--notify-now", action="store_true", help="Fetch and broadcast current status to phones right now")
    parser.add_argument("--status", action="store_true", help="Show currently saved status of tracked PNRs")
    args = parser.parse_args()

    if args.test:
        test_notifications()
        return

    if args.notify_now:
        broadcast_live_status()
        return

    if args.status:
        state = load_state()
        if not state:
            print("[i] No saved PNR statuses yet.")
        for pnr, d in state.items():
            print(f"\nPNR: {pnr} | Train: {d.get('train_no')} {d.get('train_name')} | DOJ: {d.get('doj')}")
            for p in d.get("passengers", []):
                print(f"  Passenger {p.get('number')}: {p.get('current_status')}")
        return

    if args.once:
        run_check()
        return

    # Default: Loop mode
    config = load_config()
    interval_minutes = config.get("check_interval_minutes", 30)
    print(f"[*] Starting Indian Railways PNR Auto-Tracker (checking every {interval_minutes} minutes)...")
    print(f"[*] Press Ctrl+C to stop.\n")

    while True:
        try:
            run_check()
            print(f"[*] Sleeping for {interval_minutes} minutes before next check...")
            time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n[*] Tracker stopped by user.")
            break
        except Exception as e:
            print(f"[!] Unexpected error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
