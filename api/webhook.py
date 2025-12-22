import os
import requests
import json
import sqlite3
import random
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# --- الإعدادات ---
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = "boykta2026" 
API_URL = "https://painel.meowssh.shop/pages/criar_teste.php?id=Pul&byid=1&mainid=0"
DB_NAME = "/tmp/meow_ultimate.db"

# --- إدارة قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS cooldowns (user_id TEXT PRIMARY KEY, last_request TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER)')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('last_id', 80303342)")
    conn.commit()
    conn.close()

def get_remaining_time(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT last_request FROM cooldowns WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        last_time = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
        next_allowed = last_time + timedelta(hours=23)
        if datetime.now() < next_allowed:
            diff = next_allowed - datetime.now()
            h, rem = divmod(int(diff.total_seconds()), 3600)
            m, s = divmod(rem, 60)
            return f"{h} ساعة و {m} دقيقة و {s} ثانية"
    return None

def update_request_time(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT OR REPLACE INTO cooldowns (user_id, last_request) VALUES (?, ?)", (user_id, now))
    conn.commit()
    conn.close()

# --- وظيفة الإرسال الموحدة (أزرار ثابتة + ردود سريعة) ---
def send_universal_menu(recipient_id, text_header):
    if not PAGE_ACCESS_TOKEN: return
    
    # الردود السريعة (تظهر فوق الكيبورد)
    quick_replies = [
        {"content_type": "text", "title": "🚀 إنشاء حساب", "payload": "CREATE_V2RAY"},
        {"content_type": "text", "title": "ℹ️ الطريقة", "payload": "HOW_TO_USE"}
    ]
    
    # قالب الأزرار الثابتة (لا يختفي أبداً - يدعم لايت)
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text_header,
                    "buttons": [
                        {"type": "postback", "title": "🚀 إنشاء حساب V2Ray", "payload": "CREATE_V2RAY"},
                        {"type": "postback", "title": "ℹ️ طريقة الاستخدام", "payload": "HOW_TO_USE"}
                    ]
                }
            },
            "quick_replies": quick_replies
        }
    }
    
    requests.post(f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}", 
                  headers={"Content-Type": "application/json"}, data=json.dumps(payload))

# --- معالجة منطق الحساب ---
def handle_creation_logic(recipient_id):
    wait_msg = get_remaining_time(recipient_id)
    if wait_msg:
        send_universal_menu(recipient_id, f"⚠️ لديك حساب نشط حالياً.\n⏱️ الوقت المتبقي لطلب حساب جديد: {wait_msg}")
        return

    # رسالة انتظار بسيطة قبل المعالجة
    payload = {"recipient": {"id": recipient_id}, "message": {"text": "⏳ جاري توليد بيانات الحساب... "}}
    requests.post(f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}", 
                  headers={"Content-Type": "application/json"}, data=json.dumps(payload))

    # منطق الـ API
    try:
        current_id = random.randint(80303342, 90303342) # تبسيط لليوزر
        username = f"utest{current_id}"
        password = str(random.randint(100000, 999999))
        
        with requests.Session() as s:
            s.get(API_URL)
            res = s.post(API_URL, data={'categoria': 'ServerBR', 'nome': username, 'usuario': username, 'senha': password, 'tipo': 'v2ray', 'whatsapp': '556199999999'}, timeout=20)
            if res.status_code == 200:
                update_request_time(recipient_id)
                uuid_v = f"{random.getrandbits(32):x}-{random.getrandbits(16):x}"
                success_msg = f"✅ تم الإنشاء!\n👤 المستخدم: {username}\n🔑 السر: {password}\n🆔 UUID: {uuid_v}\n⏱️ الصلاحية: 24 ساعة"
                send_universal_menu(recipient_id, success_msg)
            else:
                send_universal_menu(recipient_id, "❌ خطأ في السيرفر حالياً.")
    except:
        send_universal_menu(recipient_id, "⚠️ فشل الاتصال بالموقع.")

# --- Webhook ---
@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Error", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    init_db()
    if data.get("object") == "page":
        for entry in data["entry"]:
            for event in entry.get("messaging", []):
                sid = event["sender"]["id"]
                
                # 1. التعامل مع ضغط الأزرار (Postbacks/Quick Replies)
                payload = None
                if event.get("postback"):
                    payload = event["postback"]["payload"]
                elif event.get("message") and event["message"].get("quick_reply"):
                    payload = event["message"]["quick_reply"]["payload"]
                
                if payload:
                    if payload == "CREATE_V2RAY":
                        handle_creation_logic(sid)
                    elif payload == "HOW_TO_USE":
                        instruct = "ℹ️ طريقة الاستخدام:\n1. حمل تطبيق Meow VPN.\n2. أدخل بيانات الحساب المستخرجة.\n3. اضغط اتصال."
                        send_universal_menu(sid, instruct)
                    continue

                # 2. التعامل مع أي مدخلات أخرى (نص، صورة، صوت)
                if event.get("message"):
                    wait_msg = get_remaining_time(sid)
                    if wait_msg:
                        # إذا أرسل المستخدم أي شيء ولديه حساب نشط، يظهر له الوقت
                        send_universal_menu(sid, f"⏱️ لا يمكنك إنشاء حساب جديد الآن.\nالوقت المتبقي: {wait_msg}")
                    else:
                        # إذا أرسل أي شيء وليس لديه وقت انتظار، تظهر رسالة البداية التوضيحية
                        welcome = "✨ مرحباً بك في بوت Meow SSH.\nوظيفتي هي إنشاء حسابات V2Ray مجانية لمدة 24 ساعة.\n\nيرجى استخدام الأزرار أدناه للتحكم:"
                        send_universal_menu(sid, welcome)

    return "ok", 200

if __name__ == '__main__':
    app.run()
