# Indian Railways PNR Status Auto-Tracker & Notifier

Automatically tracks your Indian Railways PNRs and sends real-time notifications to your phone or PC whenever:
- Waiting List improves (e.g. `WL 45` -> `WL 12`)
- Ticket shifts to RAC (e.g. `WL` -> `RAC 5`)
- Ticket gets Confirmed (`RAC` -> `CNF`, Coach & Berth assigned)
- Charting status is finalized (`Chart Prepared: Yes`)

---

## Quick Setup

### 1. Add your PNR Numbers
Open `config.json` in any text editor and replace the placeholder PNRs with your 10-digit numbers:
```json
{
  "pnr_list": [
    "2345678901",
    "8901234567"
  ],
  "check_interval_minutes": 30
}
```
*(Or add via command line: `python pnr_tracker.py --add-pnr 1234567890`)*

---

## Notification Options (Choose Any)

### Option 1: Instant Mobile App Push Notification (Recommended - 30 seconds setup, 100% Free)
1. Install the free **ntfy** app on your phone:
   - Android: [Google Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
   - iOS: [App Store](https://apps.apple.com/app/ntfy/id1625396347)
2. Open the app, tap `+` (Subscribe) and enter any unique topic name of your choice (e.g., `pnr_alert_rahul_99`).
3. In `config.json`, enable `ntfy` and set your topic:
   ```json
   "ntfy": {
     "enabled": true,
     "topic": "pnr_alert_rahul_99"
   }
   ```
4. Done! Every time your WL or RAC updates, your phone will ring/vibrate with the full ticket status.

---

### Option 2: WhatsApp (via CallMeBot - Free)
1. Add `+34 644 44 24 53` to your WhatsApp contacts as "CallMeBot".
2. Send this exact message to that number:
   `I allow callmebot to send me messages`
3. CallMeBot will reply with your personal API Key.
4. In `config.json`:
   ```json
   "whatsapp_callmebot": {
     "enabled": true,
     "phone_number": "+91XXXXXXXXXX",
     "api_key": "YOUR_API_KEY"
   }
   ```

---

### Option 3: Telegram Bot
1. Search for `@BotFather` on Telegram and send `/newbot` to create a bot. Copy your API Token.
2. Send any message to your new bot, then open:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   to find your `chat_id`.
3. In `config.json`:
   ```json
   "telegram": {
     "enabled": true,
     "bot_token": "YOUR_BOT_TOKEN",
     "chat_id": "YOUR_CHAT_ID"
   }
   ```

---

### Option 4: Email Notification
In `config.json`, provide your Gmail address and a [Google App Password](https://myaccount.google.com/apppasswords):
```json
"email": {
  "enabled": true,
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "sender_email": "your_email@gmail.com",
  "sender_password": "your_16_char_app_password",
  "recipient_email": "your_email@gmail.com"
}
```

---

### Option 5: Windows Desktop Notification
Enabled by default. A balloon toast notification will pop up on your Windows desktop whenever a status change occurs.

---

## Running the Tracker

- **Test Notifications**:
  ```cmd
  python pnr_tracker.py --test
  ```
- **Run Single Check**:
  ```cmd
  python pnr_tracker.py --once
  ```
- **Start Auto-Tracking Loop**:
  Double-click `run_tracker.bat` or run:
  ```cmd
  python pnr_tracker.py
  ```
