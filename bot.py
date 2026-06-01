import logging
import threading
import re
import os
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- SOZLAMALAR ---
TOKEN = "8744818266:AAHyEeNJLGWae5L5k5TVFIB9X-15l5jP4Ec"
ADMIN_ID = 6123752979

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- SERVER (RENDER MONITORING UCHUN) ---
app_server = Flask(__name__)

@app_server.route('/')
def home():
    # UptimeRobot va Render yashil bo'lishi uchun 200 kodi qaytariladi
    return "Bot is running...", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    # Werkzeug server bloklanib qolmasligi uchun threaded va use_reloader beramiz
    app_server.run(host='0.0.0.0', port=port, threaded=True, use_reloader=False)

# --- BOT FUNKSIYALARI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['chat_active'] = False
    context.user_data['contact_asked'] = False
    keyboard = [[KeyboardButton("📝 Boshlash")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        """Assalomu alaykum, bu SURXONDARYO 24 ning murojaat va xabarlar boti.
Xabarlar va murojaatingizni qisqa va aniq qilib yozing. Hujjatlar, foto, audio va videolar bo‘lsa ilova qilib yo‘llang. Aloqa uchun telegram manzilingiz yoki telefon raqamingizni yozib yuboring.""",
        reply_markup=reply_markup
    )

async def admin_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    target_id = None
    reply_msg = update.message.reply_to_message

    # Reply qilingan xabar matn bo'lsa yoki rasm tagidagi yozuv bo'lsa ID ni qidiradi
    msg_text = reply_msg.text or reply_msg.caption

    if msg_text:
        match = re.search(r"ID:\s*(\d+)", msg_text)
        if match:
            target_id = int(match.group(1))

    if target_id:
        try:
            # Admin faqat matn yozib javob qaytarganda ishlaydi
            if update.message.text:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"👨‍💻 Admin javobi:\n\n{update.message.text}"
                )
                await update.message.reply_text("✅ Javob yuborildi.")
        except Exception as e:
            await update.message.reply_text(f"❌ Yuborishda xato: {e}")

async def user_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    # "Boshlash" tugmasi bosilganda
    if text == "📝 Boshlash":
        context.user_data['chat_active'] = True
        context.user_data['contact_asked'] = False
        contact_btn = [[KeyboardButton("📱 Kontaktni ulashish", request_contact=True)]]
        markup = ReplyKeyboardMarkup(contact_btn, resize_keyboard=True)
        await update.message.reply_text(
            "Xabarlar va murojaatingizni yuborishingiz mumkin. "
            "Aloqa uchun telegram manzilingiz yoki telefon raqamingizni qoldirishni unutmang!!!", 
            reply_markup=markup
        )
        return

    # Foydalanuvchi xabar yoki media yuborganda
    if context.user_data.get('chat_active'):
        # Adminga xabarni (Rasm, video, tekst, fayl) xavfsiz forward qilish
        await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user.id, message_id=update.message.message_id)
        
        # Admin uchun ma'lumot paneli
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📩 Yangi xabar!\n👤 {user.full_name}\n🆔 ID: {user.id}\n\n👆 Javob berish uchun yuqoridagi xabarga 'Reply' qiling."
        )
        
        # Aloqa ma'lumotlarini so'rash eslatmasini faqat 1-marta chiqarish
        if not context.user_data.get('contact_asked'):
            await update.message.reply_text("Murojaatingiz qabul qilindi va adminga yuborildi.")
            context.user_data['contact_asked'] = True
        else:
            await update.message.reply_text("Xabaringiz qabul qilindi.")

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📞 KONTAKT KELDI:\nIsm: {contact.first_name}\nTel: +{contact.phone_number}\nID: {contact.user_id}"
    )
    await update.message.reply_text("Rahmat! Kontaktingiz qabul qilindi.")

# --- ASOSIY ISHGA TUSHIRISH ---
if __name__ == '__main__':
    # 1. Flask serverni xavfsiz sozlamalar bilan fonda ochish
    threading.Thread(target=run_web, daemon=True).start()
    
    # 2. Bot ilovasini qurish
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.REPLY & filters.User(user_id=ADMIN_ID), admin_reply_handler))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    
    # filters.ALL yordamida rasm va videolarda bot o'chib qolmaydigan qilindi
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND & ~filters.User(user_id=ADMIN_ID), user_message_handler))
    
    print("SURXONDARYO 24 boti barqaror ishga tushdi...")
    
    # 3. Pollingni asinxron muammolarsiz yurgizish
    app.run_polling(close_loop=False)
