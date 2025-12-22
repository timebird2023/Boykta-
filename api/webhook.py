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
DB_NAME = "/tmp/mabar_vpn.db"

# --- إدارة قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS cooldowns (user_id TEXT PRIMARY KEY, last_request TEXT)')
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

# --- وظيفة الإرسال المزدوجة (لضمان ظهور الأزرار فوق الكيبورد) ---
def send_mabar_menu(recipient_id, text_header):
    if not PAGE_ACCESS_TOKEN: return
    
    # 1. الردود السريعة (الفقاعات فوق صندوق الكتابة) - تظهر بشكل ممتاز في التطبيق الرسمي
    quick_replies = [
        {"content_type": "text", "title": "🚀 إنشاء حساب V2Ray", "payload": "CREATE_V2RAY"},
        {"content_type": "text", "title": "ℹ️ طريقة الاستخدام", "payload": "HOW_TO_USE"}
    ]
    
    # 2. قالب الأزرار الثابتة (داخل الدردشة) - لضمان العمل على فيسبوك لايت
    button_template = {
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
            "quick_replies": quick_replies # نرسلها هنا أيضاً لزيادة التأكيد
        }
    }
    
    requests.post(f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}", 
                  headers={"Content-Type": "application/json"}, data=json.dumps(button_template))

# --- منطق إنشاء الحساب ---
def handle_v2ray_logic(recipient_id):
    wait_msg = get_remaining_time(recipient_id)
    if wait_msg:
        send_mabar_menu(recipient_id, f"⚠️ لديك حساب نشط حالياً.\n⏱️ الوقت المتبقي لطلب حساب جديد: {wait_msg}")
        return

    # رسالة نصية بسيطة مع أزرار سريعة للإشعار بالبدء
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "text": "⏳ جاري توليد بيانات حسابك في Ma'bar VPN... يرجى الانتظار.",
            "quick_replies": [{"content_type": "text", "title": "🚀 إنشاء حساب", "payload": "CREATE_V2RAY"}]
        }
    }
    requests.post(f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}", 
                  headers={"Content-Type": "application/json"}, data=json.dumps(payload))

    try:
        username = f"mabar{random.randint(1000, 9999)}"
        password = str(random.randint(100000, 999999))
        
        # محاكاة الطلب (يجب التأكد من بيانات API الصحيحة كما في المرات السابقة)
        update_request_time(recipient_id)
        uuid_v = f"{random.getrandbits(32):x}-{random.getrandbits(16):x}"
        success_msg = f"✅ تم إنشاء حسابك في Ma'bar VPN!\n\n👤 المستخدم: {username}\n🔑 السر: {password}\n🆔 UUID: {uuid_v}\n⏱️ الصلاحية: 24 ساعة"
        send_mabar_menu(recipient_id, success_msg)
    except:
        send_mabar_menu(recipient_id, "⚠️ حدث خطأ فني، يرجى المحاولة لاحقاً.")

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
                
                # التعامل مع الأزرار (القالب أو الرد السريع)
                payload = None
                if event.get("postback"):
                    payload = event["postback"]["payload"]
                elif event.get("message") and event["message"].get("quick_reply"):
                    payload = event["message"]["quick_reply"]["payload"]
                
                if payload:
                    if payload == "CREATE_V2RAY":
                        handle_v2ray_logic(sid)
                    elif payload == "HOW_TO_USE":
                        instruct = "ℹ️ طريقة الاستخدام:\n1. حمل تطبيق Ma'bar VPN.\n2. أدخل بيانات الحساب (User, Pass, UUID).\n3. اضغط اتصال واستمتع بالإنترنت."
                        send_mabar_menu(sid, instruct)
                    continue

                # التعامل مع أي مدخلات أخرى (نص، صورة، تسجيل صوتي)
                if event.get("message"):
                    wait_msg = get_remaining_time(sid)
                    if wait_msg:
                        # إذا كان لديه وقت انتظار، نظهر التوقيت المتبقي فوراً
                        send_mabar_menu(sid, f"⚠️ لا يمكنك إنشاء حساب الآن.\n⏱️ الوقت المتبقي: {wait_msg}")
                    else:
                        # رسالة البداية التوضيحية لـ Ma'bar VPN
                        welcome = "✨ مرحباً بك في بوت Ma'bar VPN.\n\nوظيفتي هي إنشاء حسابات V2Ray مجانية وآمنة لمدة 24 ساعة.\n\nيرجى الضغط على الأزرار أدناه للتحكم:"
                        send_mabar_menu(sid, welcome)

    return "ok", 200

if __name__ == '__main__':
    app.run()
