#!/usr/bin/env python3
import os
import re
import json
import socket
import requests
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YAHAN_NAYA_TOKEN_DAAL")
PHONE_API = os.environ.get("PHONE_API", "https://ethicaltabbo.in/api/lookup")
PHONE_KEY = os.environ.get("PHONE_KEY", "Sahil")

# 🔥 APNA CHANNEL YAHAN DAALO (username with @)
CHANNEL_ID = "@death_taker"
BRANDING = "@death_taker"

# ================= FORCE SUBSCRIPTION =================
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception:
        pass

    # Not subscribed
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton("✅ Verify", callback_data="verify_sub")]
    ]
    text = (
        f"⚠️ *Access Denied!*\n\n"
        f"Bot use karne ke liye pehle channel join karo:\n"
        f"👉 {CHANNEL_ID}\n\n"
        f"Join karne ke baad *Verify* button dabao.\n\n"
        f"Powered by {BRANDING}"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(
            text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return False

async def verify_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            await q.message.edit_text(
                f"✅ *Verified!* Ab tum bot use kar sakte ho.\n\nPowered by {BRANDING}",
                parse_mode="Markdown"
            )
            return
    except Exception:
        pass
    await q.answer("❌ Pehle channel join karo!", show_alert=True)

# ================= PHONE =================
def phone_lookup(number):
    try:
        r = requests.get(f"{PHONE_API}?key={PHONE_KEY}&mobile={number}", timeout=15)
        if r.status_code == 200 and r.json().get("status"):
            return r.json()
    except Exception as e:
        return {"error": str(e)}
    return None

# ================= EMAIL =================
def email_check(email):
    result = {}
    try:
        import dns.resolver
        domain = email.split("@")[1]
        mx = dns.resolver.resolve(domain, "MX")
        result["mx_records"] = [str(x.exchange) for x in mx]
        result["domain_valid"] = True
    except:
        result["domain_valid"] = False
    try:
        r = requests.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
            headers={"User-Agent": "OSINT-Bot"}, timeout=10
        )
        if r.status_code == 200:
            result["breaches"] = [b["Name"] for b in r.json()]
        elif r.status_code == 404:
            result["breaches"] = "CLEAN"
    except:
        result["breaches"] = "check failed"
    return result

# ================= IP =================
def ip_lookup(ip):
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=66846719", timeout=10)
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == "success":
                return d
    except Exception as e:
        return {"error": str(e)}
    return None

# ================= DOMAIN =================
def domain_lookup(domain):
    result = {}
    try:
        import whois
        w = whois.whois(domain)
        result["whois"] = {
            "registrar": w.registrar,
            "creation_date": str(w.creation_date),
            "expiration_date": str(w.expiration_date),
            "name_servers": w.name_servers,
            "emails": w.emails,
            "country": w.country,
            "org": w.org,
        }
    except Exception as e:
        result["whois"] = {"error": str(e)}
    try:
        result["resolved_ip"] = socket.gethostbyname(domain)
    except:
        result["resolved_ip"] = None
    return result

# ================= USERNAME =================
SITES = {
    "GitHub": "https://github.com/{}",
    "Instagram": "https://instagram.com/{}",
    "Twitter/X": "https://twitter.com/{}",
    "Reddit": "https://reddit.com/user/{}",
    "Telegram": "https://t.me/{}",
    "YouTube": "https://youtube.com/@{}",
    "Facebook": "https://facebook.com/{}",
    "TikTok": "https://tiktok.com/@{}",
    "Pinterest": "https://pinterest.com/{}",
    "LinkedIn": "https://linkedin.com/in/{}",
    "Medium": "https://medium.com/@{}",
    "Twitch": "https://twitch.tv/{}",
    "Steam": "https://steamcommunity.com/id/{}",
    "Spotify": "https://open.spotify.com/user/{}",
}

def _check_site(name, url):
    try:
        r = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        return name, r.status_code == 200, url
    except:
        return name, False, url

def username_search(username):
    found = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(_check_site, n, u.format(username)) for n, u in SITES.items()]
        for f in futures:
            name, ok, url = f.result()
            if ok:
                found[name] = url
    return {"username": username, "found": found, "total_found": len(found)}

# ================= IMAGE EXIF =================
def image_exif(image_bytes):
    result = {"exif": {}}
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        img = Image.open(BytesIO(image_bytes))
        exif = img._getexif() or {}
        for tag_id, val in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            result["exif"][str(tag)] = str(val)[:200]
    except Exception as e:
        result["exif"]["error"] = str(e)
    result["reverse_search"] = [
        "https://lens.google.com/upload",
        "https://yandex.com/images",
        "https://tineye.com"
    ]
    return result

# ================= GST =================
def gst_lookup(gstin):
    return {
        "gstin": gstin,
        "valid_format": len(gstin) == 15 and gstin[:2].isdigit(),
        "check_links": [
            "https://www.gst.gov.in/",
            "https://razorpay.com/gst-number-search/",
            "https://www.mastersindia.co/gst-number-search-and-gstin-verification/"
        ]
    }

# ================= UPI =================
def upi_lookup(vpa):
    pattern = r"^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}$"
    if not re.match(pattern, vpa):
        return {"valid_format": False, "error": "Invalid VPA"}
    handle = vpa.split("@")[1]
    banks = {
        "ybl": "PhonePe", "paytm": "Paytm", "okbizaxis": "Axis Bank",
        "okaxis": "Axis Bank", "oksbi": "SBI", "okhdfcbank": "HDFC Bank",
        "okicici": "ICICI Bank", "ibl": "ICICI Bank", "axl": "Axis Bank",
        "upi": "BHIM", "apl": "Amazon Pay", "yapl": "PhonePe",
        "gpay": "Google Pay", "airtel": "Airtel Payments Bank",
        "fbl": "Federal Bank", "jupiteraxis": "Jupiter", "naviaxis": "Navi",
    }
    return {
        "valid_format": True, "vpa": vpa, "handle": handle,
        "likely_bank": banks.get(handle, "Unknown")
    }

# ================= VEHICLE =================
def vehicle_info(rc_number):
    rc = rc_number.upper().replace(" ", "").replace("-", "")
    if len(rc) < 10:
        return {"error": "Invalid RC (e.g. MH12AB1234)"}
    states = {
        "MH": "Maharashtra", "DL": "Delhi", "KA": "Karnataka",
        "TN": "Tamil Nadu", "UP": "Uttar Pradesh", "GJ": "Gujarat",
        "RJ": "Rajasthan", "WB": "West Bengal", "AP": "Andhra Pradesh",
        "TS": "Telangana", "KL": "Kerala", "MP": "Madhya Pradesh",
        "HR": "Haryana", "PB": "Punjab", "BR": "Bihar",
        "OR": "Odisha", "JH": "Jharkhand", "AS": "Assam",
        "CH": "Chandigarh", "GA": "Goa",
    }
    return {
        "rc_number": rc,
        "state_code": rc[:2],
        "state_name": states.get(rc[:2], "Unknown"),
        "rto_code": rc[2:4],
        "series": rc[4:6],
        "vehicle_number": rc[6:],
        "public_check_url": "https://vahan.parivahan.gov.in/nrservices/faces/user/searchstatus.xhtml"
    }

# ================= COMPANY =================
def company_info(query):
    return {
        "query": query,
        "zaubacorp": f"https://www.zaubacorp.com/company-search/{query}",
        "tofler": f"https://www.tofler.in/search?q={query}",
        "mca": "https://www.mca.gov.in/mcafoportal/viewCompanyMasterData.do"
    }

# ================= DETECT =================
def detect(text):
    t = text.strip()
    if t.isdigit() and len(t) == 10:
        return "phone"
    if "@" in t and not t.split("@")[0].isdigit():
        if "." not in t.split("@")[1]:
            return "upi"
        return "email"
    if t.count(".") == 3 and all(p.isdigit() for p in t.split(".")):
        return "ip"
    if len(t) == 15 and t[:2].isdigit() and t[2:].isalnum():
        return "gst"
    if len(t) >= 10 and t[:2].isalpha() and t[2:4].isdigit():
        return "vehicle"
    if "." in t and " " not in t:
        return "domain"
    return "username"

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 🔒 FORCE SUB CHECK
    if not await check_subscription(update, context):
        return

    kb = [
        [InlineKeyboardButton("📱 Phone", "h1"), InlineKeyboardButton("📧 Email", "h2")],
        [InlineKeyboardButton("🌐 IP", "h3"), InlineKeyboardButton("🌍 Domain", "h4")],
        [InlineKeyboardButton("🔍 Username", "h5"), InlineKeyboardButton("🖼️ Image", "h6")],
        [InlineKeyboardButton("🧾 GST", "h7"), InlineKeyboardButton("💳 UPI", "h8")],
        [InlineKeyboardButton("🚗 Vehicle", "h9"), InlineKeyboardButton("🏢 Company", "h10")],
    ]
    await update.message.reply_text(
        f"🛡️ *ALL-IN-ONE OSINT BOT*\n\n"
        f"📱 Phone | 📧 Email | 🌐 IP | 🌍 Domain\n"
        f"🔍 Username | 🖼️ Image | 🧾 GST | 💳 UPI\n"
        f"🚗 Vehicle | 🏢 Company\n\n"
        f"Bas type karke bhej — auto detect!\n\n"
        f"🔰 Powered by {BRANDING}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def help_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    msgs = {
        "h1": "📱 10-digit number bhej",
        "h2": "📧 email@domain.com bhej",
        "h3": "🌐 8.8.8.8 bhej",
        "h4": "🌍 google.com bhej",
        "h5": "🔍 username bhej",
        "h6": "🖼️ Image bhej",
        "h7": "🧾 GSTIN bhej",
        "h8": "💳 user@bank bhej",
        "h9": "🚗 MH12AB1234 bhej",
        "h10": "🏢 company name bhej",
    }
    await q.message.reply_text(msgs.get(q.data, "?"))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 🔒 FORCE SUB CHECK
    if not await check_subscription(update, context):
        return

    text = update.message.text.strip()
    kind = detect(text)
    msg = await update.message.reply_text(f"⏳ `{kind.upper()}`...", parse_mode="Markdown")

    result = None
    try:
        if kind == "phone":     result = phone_lookup(text)
        elif kind == "email":   result = email_check(text)
        elif kind == "ip":      result = ip_lookup(text)
        elif kind == "domain":  result = domain_lookup(text)
        elif kind == "username":result = username_search(text)
        elif kind == "gst":     result = gst_lookup(text)
        elif kind == "upi":     result = upi_lookup(text)
        elif kind == "vehicle": result = vehicle_info(text)
        elif kind == "company": result = company_info(text)
    except Exception as e:
        result = {"error": str(e)}

    if not result:
        await msg.edit_text(f"❌ Koi data nahi mila.\n\n🔰 {BRANDING}")
        return

    out = json.dumps(result, indent=2, ensure_ascii=False, default=str)
    if len(out) > 4000:
        out = out[:4000] + "\n... (truncated)"
    await msg.edit_text(
        f"```json\n{out}\n```\n\n🔰 Powered by {BRANDING}",
        parse_mode="Markdown"
    )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 🔒 FORCE SUB CHECK
    if not await check_subscription(update, context):
        return

    photo = update.message.photo[-1]
    file = await photo.get_file()
    b = await file.download_as_bytearray()
    res = image_exif(bytes(b))
    out = json.dumps(res, indent=2, ensure_ascii=False, default=str)
    if len(out) > 4000:
        out = out[:4000] + "\n...(truncated)"
    await update.message.reply_text(
        f"```json\n{out}\n```\n\n🔰 Powered by {BRANDING}",
        parse_mode="Markdown"
    )

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(verify_sub, pattern="^verify_sub$"))
    app.add_handler(CallbackQueryHandler(help_cb))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print(f"🛡️ OSINT Bot running... Branding: {BRANDING}")
    app.run_polling()

if __name__ == "__main__":
    main()
