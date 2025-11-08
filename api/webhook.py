import os
import requests
import json
import sqlite3
from flask import Flask, request, jsonify
from datetime import datetime

# ---------------------------
# ⚙️ إعدادات البوت والتحقق السري
# ---------------------------
# قم بتعيين PAGE_ACCESS_TOKEN كمتغير بيئة في Vercel
PAGE_ACCESS_TOKEN = os.environ.get("EAAWWAEaEh1EBPy1nZCZAJmiQxFXcfqV0SkPAj6YPS3oci6EWC2ur3KMlEl4fGa2aYBL1Vexb1FYxQoZAZCAe2amLvRIM90zy36sBXMqZCZCKcXCWGNH6WrcQu0ffjfiggoVg0z9IAgZC68ByjE22kAGdHWRNGWqMf1gtIgsP5j5XhE6MAAUt1ZBQPHOHC5p1UIXrhUS6TgZDZD")
# الكود السري الخاص بك للتحقق من الويب هوك في فيسبوك
VERIFY_TOKEN = "boykta2026" 

app = Flask(__name__)

# ---------------------------
# 🛠️ الثوابت والـ APIs
# ---------------------------
SSH_API_URL = "https://painel.meowssh.shop:5000/test_ssh_public"
SSH_API_PAYLOAD = {"store_owner_id": 1}
# تم نقل الهيدرز بالكامل من الكود الأصلي
SSH_API_HEADERS = {
    'Host': "painel.meowssh.shop:5000",
    'User-Agent': "Mozilla/5.0 (Linux; Android 11; M2004J19C Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/140.0.7339.51 Mobile Safari/537.36",
    'Accept': "application/json",
    'Accept-Encoding': "gzip, deflate, br, zstd",
    'Content-Type': "application/json",
    'sec-ch-ua-platform': "\"Android\"",
    'sec-ch-ua': "\"Chromium\";v=\"140\", \"Not=A?Brand\";v=\"24\", \"Android WebView\";v=\"140\"",
    'sec-ch-ua-mobile': "?1",
    'Origin': "https://deft-rabanadas-c2cd8c.netlify.app",
    'X-Requested-With': "com.data.net",
    'Sec-Fetch-Site': "cross-site",
    'Sec-Fetch-Mode': "cors",
    'Sec-Fetch-Dest': "empty",
    'Referer': "https://deft-rabanadas-c2cd8c.netlify.app/",
    'Accept-Language': "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
}

# ملاحظة: Vercel هي بيئة بلا حالة (Stateless)، لذا سيتم حذف البيانات المخزنة
# بين طلب وآخر. تم وضع ملف DB في مجلد /tmp/ ليتوافق مع Vercel،
# لكن لن يتم حفظ الحسابات بشكل دائم.
DB_NAME = "/tmp/ssh_accounts.db" 

# ---------------------------
# 🗄️ وظائف قاعدة البيانات و SSH
# ---------------------------
def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS accounts
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT,
                      password TEXT,
                      ip TEXT,
                      expiration TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error on init: {e}")

def save_account(account_info):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT INTO accounts (username, password, ip, expiration)
                     VALUES (?, ?, ?, ?)''',
                  (account_info['username'], account_info['password'],
                   account_info['ip'], account_info['expiration']))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error on save: {e}")

def get_ssh_info():
    init_db() 
    try:
        response = requests.post(SSH_API_URL, data=json.dumps(SSH_API_PAYLOAD), headers=SSH_API_HEADERS, timeout=10)
        
        try:
            data = response.json()
            ssh_info = None
            
            if 'Usuario' in data and 'Senha' in data:
                ssh_info = {
                    'username': data['Usuario'],
                    'password': data['Senha'],
                    'expiration': data.get('Expiracao', 'غير معروف'),
                    'ip': data.get('IP', 'غير معروف'),
                    'limit': data.get('limite', 'غير معروف')
                }
            else:
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, dict) and 'Usuario' in value and 'Senha' in value:
                            ssh_info = {
                                'username': value['Usuario'],
                                'password': value['Senha'],
                                'expiration': value.get('Expiracao', 'غير معروف'),
                                'ip': value.get('IP', 'غير معروف'),
                                'limit': value.get('limite', 'غير معروف')
                            }
                            break
            
            if ssh_info:
                save_account(ssh_info)
                return ssh_info
            else:
                return {"error": "لم يتم العثور على معلومات الحساب"}
                
        except json.JSONDecodeError:
            return {"error": "خطأ في تحليل البيانات"}
    except Exception as e:
        return {"error": f"خطأ في الاتصال بالـ API: {str(e)}"}

# ---------------------------
# 💬 وظائف فيسبوك ماسنجر
# ---------------------------
def send_message(recipient_id, message_text, quick_replies=None):
    """إرسال رسالة نصية أو ردود سريعة إلى فيسبوك"""
    if not PAGE_ACCESS_TOKEN:
        print("❌ خطأ: لم يتم تعيين PAGE_ACCESS_TOKEN.")
        return

    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    
    # بناء حمولة الرسالة
    message_data = {"text": message_text}
    if quick_replies:
        message_data["quick_replies"] = quick_replies

    data = json.dumps({
        "recipient": {"id": recipient_id},
        "message": message_data
    })
    
    r = requests.post("https://graph.facebook.com/v19.0/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        print(f"❌ خطأ في إرسال رسالة فيسبوك: {r.text}")

def send_main_menu_facebook(recipient_id):
    """إرسال القائمة الرئيسية بالأزرار الجديدة والرسالة الافتراضية"""
    
    # النص الافتراضي المطلوب لأي رسالة من المستخدم
    welcome_text = "يرجى إستعمال الأزرار أدناه"

    # الأزرار المطلوبة فقط
    quick_replies = [
        {"content_type": "text", "title": "🔄 إنشاء حساب SSH", "payload": "CREATE_SSH_PAYLOAD"},
        {"content_type": "text", "title": "ℹ️ طريقة العمل", "payload": "HOW_IT_WORKS_PAYLOAD"}
    ]
    
    send_message(recipient_id, welcome_text, quick_replies=quick_replies)

def create_ssh_account_facebook(recipient_id):
    """منطق إنشاء الحساب وإرساله"""
    
    send_message(recipient_id, "⏳ جاري إنشاء حساب SSH... الرجاء الانتظار.")
    
    ssh_info = get_ssh_info()
    
    if 'error' in ssh_info:
        error_msg = f"❌ *خطأ:* {ssh_info['error']}\n\n🔁 حاول مرة أخرى لاحقاً."
        send_message(recipient_id, error_msg)
        return
        
    account_data = f"""
✅ *تم إنشاء الحساب بنجاح!*
📋 *معلومات الحساب:*
👤 المستخدم: {ssh_info['username']}
🔑 كلمة المرور: {ssh_info['password']}
🌐 IP: {ssh_info['ip']}
⏰ المدة: {ssh_info['expiration']}
📊 الحد: {ssh_info['limit']}
"""
    send_message(recipient_id, account_data)
    send_main_menu_facebook(recipient_id)


def handle_facebook_payload(recipient_id, payload):
    """معالجة الـ payloads (الردود السريعة أو Postbacks)"""
    
    if payload == "CREATE_SSH_PAYLOAD":
        create_ssh_account_facebook(recipient_id)
        
    # المنطق الجديد والمفصل لزر طريقة العمل
    elif payload == "HOW_IT_WORKS_PAYLOAD":
        how_it_works_text = """
**ℹ️ طريقة عمل البوت والحسابات المجانية**

هذا البوت مخصص لإنشاء حسابات SSH مجانية بمدة **3 ساعات** من واجهة برمجة تطبيقات خارجية.

### 🔑 خطوات إنشاء الحساب:
1.  **اضغط على زر "🔄 إنشاء حساب SSH"** لتوليد حساب جديد.
2.  **ستصلك رسالة تحتوي على:** اسم المستخدم، كلمة المرور، وعنوان السيرفر (IP).
3.  **قم بنسخ هذه البيانات** لاستخدامها في تطبيق VPN المخصص.

### 📱 التطبيق الضروري:
لاستخدام الحساب الذي تم إنشاؤه، يجب عليك تنزيل تطبيق **Ma'bar VPN**.
⬅️ **رابط تنزيل التطبيق:** [https://play.google.com/store/apps/details?id=com.mabarvpn.app] (ضع الرابط الصحيح لتطبيق Ma'bar VPN)

### ⚙️ شرح استخدام الحساب في التطبيق:
1.  **افتح تطبيق Ma'bar VPN.**
2.  ستجد خانة لإدخال **اسم المستخدم (Usuário)** وخانة لـ **كلمة المرور (Senha)**.
3.  **ألصق اسم المستخدم وكلمة المرور** التي حصلت عليها من البوت في الخانات المخصصة.
4.  **اختر السيرفر** (في العادة يكون السيرفر موجوداً تلقائياً أو يمكنك اختياره إذا طلب التطبيق).
5.  **اضغط على زر "INICIAR" (أو اتصال)** لبدء الاتصال.

**ملاحظة:** صلاحية الحساب هي 3 ساعات فقط، وبعد انتهاء المدة، يمكنك إنشاء حساب جديد.
"""
        send_message(recipient_id, how_it_works_text)
        send_main_menu_facebook(recipient_id)
        
    elif payload == "GET_STARTED_PAYLOAD": 
        # عند الضغط على زر "ابدأ" لأول مرة
        send_main_menu_facebook(recipient_id)
        
    else:
        # لأي payload غير معروف، إرسال القائمة الرئيسية
        send_main_menu_facebook(recipient_id)

# ---------------------------
# 🌐 Webhook (مسارات Flask)
# ---------------------------
# المسار الأساسي الذي سيتلقى الطلبات
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """التحقق من الـ Webhook"""
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args.get("hub.challenge"), 200
    return "Webhook server is running.", 200

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """معالجة رسائل فيسبوك"""
    data = request.get_json()
    
    if data["object"] == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                
                sender_id = messaging_event["sender"]["id"]

                # معالجة الرسالة النصية أو الرد السريع
                if messaging_event.get("message"):
                    if messaging_event["message"].get("quick_reply"):
                        payload = messaging_event["message"]["quick_reply"]["payload"]
                        handle_facebook_payload(sender_id, payload)
                        
                    elif messaging_event["message"].get("text"):
                        # الرد الافتراضي المطلوب لأي رسالة نصية
                        send_main_menu_facebook(sender_id) 

                # معالجة رسالة Postback (مثل زر "ابدأ")
                elif messaging_event.get("postback"):
                    payload = messaging_event["postback"]["payload"]
                    handle_facebook_payload(sender_id, payload)

    return jsonify({'status': 'ok'}), 200
