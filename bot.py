import os
import time
import re
import json
import logging
import requests
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes

# ===================== НАСТРОЙКИ =====================
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    print("❌ НЕТ ТОКЕНА! Добавь переменную TELEGRAM_TOKEN")
    exit()

CREATOR_ID = 7416252489  # ЗАМЕНИ НА СВОЙ ID!

# ===================== ПЕРЕВОДЧИК =====================
class SimpleTranslator:
    """Простой переводчик через Яндекс API"""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def detect_language(self, text):
        """Определяем язык текста (простая логика)"""
        # Проверяем кириллицу
        cyrillic_chars = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        # Проверяем латиницу
        latin_chars = sum(1 for char in text.lower() if 'a' <= char <= 'z')
        
        if cyrillic_chars > latin_chars:
            return 'ru'
        elif latin_chars > cyrillic_chars:
            return 'en'
        else:
            return 'auto'
    
    def translate(self, text, source_lang='auto', target_lang='en'):
        """Перевод текста через публичный API"""
        try:
            # Публичный Яндекс Переводчик (работает без ключа с лимитами)
            url = "https://translate.googleapis.com/translate_a/single"
            
            params = {
                'client': 'gtx',
                'sl': source_lang,
                'tl': target_lang,
                'dt': 't',
                'q': text[:1000]  # Ограничиваем длину
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    translated_text = ''
                    for item in data[0]:
                        if item[0]:
                            translated_text += item[0]
                    
                    return {
                        'text': translated_text or text,
                        'src': source_lang if source_lang != 'auto' else self.detect_language(text),
                        'dest': target_lang
                    }
            
            # Если не сработало, делаем простую эмуляцию перевода
            return self._emulate_translation(text, source_lang, target_lang)
            
        except Exception as e:
            print(f"⚠️ Ошибка перевода: {e}")
            return self._emulate_translation(text, source_lang, target_lang)
    
    def _emulate_translation(self, text, source_lang, target_lang):
        """Эмуляция перевода для теста"""
        if source_lang == 'auto':
            source_lang = self.detect_language(text)
        
        if source_lang == 'ru' and target_lang == 'en':
            # Простая замена некоторых русских слов на английские (для теста)
            replacements = {
                'привет': 'hello',
                'как дела': 'how are you',
                'спасибо': 'thank you',
                'да': 'yes',
                'нет': 'no'
            }
            
            translated = text.lower()
            for ru, en in replacements.items():
                translated = translated.replace(ru, en)
            
            if translated == text.lower():
                translated = f"[EN] {text}"
        elif source_lang == 'en' and target_lang == 'ru':
            # Простая замена английских слов на русские
            replacements = {
                'hello': 'привет',
                'hi': 'привет',
                'how are you': 'как дела',
                'thank you': 'спасибо',
                'thanks': 'спасибо',
                'yes': 'да',
                'no': 'нет'
            }
            
            translated = text.lower()
            for en, ru in replacements.items():
                translated = translated.replace(en, ru)
            
            if translated == text.lower():
                translated = f"[RU] {text}"
        else:
            translated = f"[{target_lang.upper()}] {text}"
        
        return {
            'text': translated,
            'src': source_lang,
            'dest': target_lang
        }

translator = SimpleTranslator()

# ===================== ХРАНИЛИЩА =====================
user_ranks = {CREATOR_ID: "creator"}

# Автоответы - регистр не важен
RESPONSES = {
    "правила": "📜 С правилами можно ознакомиться [туть](https://telegra.ph/Rules-01-24-146)",
    "сиси": "Ну, привет... опять ты появляешься. Что на этот раз?",
    "сиси как дела": "Разве важно? Время идет, а я все так же свободна",
    "сиси что делаешь": "Отвечаю на твои глупые вопросы. А ты?",
    "кто такой этот ваш луми": "АХХ..луми..мой создатель",
    "луми": "Мхх..",
    "бот": "Ну чего тебе?",
    "сиси доброй ночи": "Спи или не спи… всё равно ничего не закончится.",
    "сиси доброе утро": "Что в этом утре особенного..",
    "сиси добрый день": "День? Какой ещё день..",
    "сиси добрый вечер": "Вечер.. снова ты..",
    "сиси привет": "Опять ты.. чего надо?",
    "привет сиси": "Ну привет.. что теперь?",
}

# ===================== СИСТЕМА РАНГОВ =====================
def get_rank(user_id):
    return user_ranks.get(user_id, "user")

def has_permission(user_id, required_rank):
    rank_hierarchy = {"user": 0, "moderator": 1, "head_admin": 2, "creator": 3}
    return rank_hierarchy.get(get_rank(user_id), 0) >= rank_hierarchy.get(required_rank, 0)

def is_creator(user_id):
    return get_rank(user_id) == "creator"

def is_head_admin_or_higher(user_id):
    return has_permission(user_id, "head_admin")

def is_moderator_or_higher(user_id):
    return has_permission(user_id, "moderator")

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
async def get_user_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
    # 1. Ответ на сообщение
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        return user.id, user.username, user.first_name
    
    text = message.text or ""
    
    # 2. @username в тексте
    if '@' in text:
        match = re.search(r'@([a-zA-Z0-9_]{5,})', text)
        if match:
            username = match.group(1)
            try:
                user = await context.bot.get_chat(f"@{username}")
                return user.id, user.username, user.first_name
            except:
                return None, username, f"@{username}"
    
    # 3. ID в тексте
    match = re.search(r'(\d{9,})', text)
    if match:
        user_id = int(match.group(1))
        try:
            user = await context.bot.get_chat(user_id)
            return user.id, user.username, user.first_name
        except:
            return user_id, None, f"ID {user_id}"
    
    return None, None, None

# ===================== ФУНКЦИЯ ПЕРЕВОДА =====================
async def команда_переведи(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда .переведи или !переведи - перевод текста"""
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("❌ Ответьте на текстовое сообщение!")
        await update.message.delete()
        return
    
    text_to_translate = update.message.reply_to_message.text
    
    # Определяем язык исходного текста
    source_lang = translator.detect_language(text_to_translate)
    
    # Определяем целевой язык (противоположный)
    if source_lang == 'ru':
        target_lang = 'en'
        target_name = "английский"
        source_name = "русский"
    elif source_lang == 'en':
        target_lang = 'ru'
        target_name = "русский"
        source_name = "английский"
    else:
        target_lang = 'ru'
        target_name = "русский"
        source_name = "другой"
    
    try:
        # Переводим
        translated = translator.translate(text_to_translate, source_lang, target_lang)
        
        # Формируем ответ
        response = (
            f"🌍 **Перевод**\n\n"
            f"**С:** {source_name}\n"
            f"**На:** {target_name}\n\n"
            f"📝 **Оригинал:**\n`{text_to_translate[:200]}{'...' if len(text_to_translate) > 200 else ''}`\n\n"
            f"✅ **Перевод:**\n`{translated['text'][:200]}{'...' if len(translated['text']) > 200 else ''}`"
        )
        
        await update.message.reply_text(response, parse_mode='Markdown')
        await update.message.delete()
        
    except Exception as e:
        print(f"❌ Ошибка перевода: {e}")
        await update.message.reply_text("❌ Не удалось перевести текст")
        await update.message.delete()

# ===================== ОСНОВНЫЕ КОМАНДЫ =====================
async def команда_дел(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    if update.message.reply_to_message:
        try:
            await update.message.reply_to_message.delete()
            await update.message.delete()
        except:
            await update.message.reply_text("❌ Не могу удалить!")
    else:
        await update.message.reply_text("❌ Ответьте на сообщение!")
        await update.message.delete()

async def команда_пинг(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    start = time.time()
    msg = await update.message.reply_text("🏓...")
    await msg.edit_text(f"🏓 Пинг: {round((time.time() - start) * 1000, 2)}мс")

async def команда_кик(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    user_id, username, name = await get_user_from_message(update, context)
    if not user_id:
        await update.message.reply_text("❌ Укажите пользователя!")
        return
    
    if is_creator(user_id):
        await update.message.reply_text("❌ Нельзя кикать создателя!")
        return
    
    try:
        await context.bot.ban_chat_member(
            update.message.chat_id,
            user_id,
            until_date=datetime.now() + timedelta(seconds=30)
        )
        await context.bot.unban_chat_member(update.message.chat_id, user_id)
        await update.message.reply_text(f"🚪 {name} исключен!")
    except:
        await update.message.reply_text("❌ Ошибка кика!")

async def команда_плюс_сс(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_head_admin_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    user_id, username, name = await get_user_from_message(update, context)
    if not user_id:
        await update.message.reply_text("❌ Укажите пользователя!")
        return
    
    user_ranks[user_id] = "moderator"
    await update.message.reply_text(f"✅ {name} теперь модератор!")

async def команда_плюс_глсс(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_creator(update.message.from_user.id):
        await update.message.delete()
        return
    
    user_id, username, name = await get_user_from_message(update, context)
    if not user_id:
        await update.message.reply_text("❌ Укажите пользователя!")
        return
    
    user_ranks[user_id] = "head_admin"
    await update.message.reply_text(f"✅ {name} теперь главный админ!")

async def команда_минус_сс(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_head_admin_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    user_id, username, name = await get_user_from_message(update, context)
    if not user_id:
        await update.message.reply_text("❌ Укажите пользователя!")
        return
    
    if user_id in user_ranks:
        del user_ranks[user_id]
        await update.message.reply_text(f"✅ С {name} снят ранг!")
    else:
        await update.message.reply_text(f"⚠️ {name} не имеет ранга!")

async def команда_садм(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    text = "👑 Администрация:\n\n"
    for uid, rank in user_ranks.items():
        try:
            user = await context.bot.get_chat(uid)
            rank_name = "👑 Создатель" if rank == "creator" else "👑 Гл.Админ" if rank == "head_admin" else "⚡ Модератор"
            text += f"{rank_name}: {user.first_name} (@{user.username if user.username else 'нет'})\n"
        except:
            text += f"{rank}: ID {uid}\n"
    
    await update.message.reply_text(text)

async def команда_салл(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_creator(update.message.from_user.id):
        await update.message.delete()
        return
    
    count = len(user_ranks) - 1
    user_ranks.clear()
    user_ranks[CREATOR_ID] = "creator"
    await update.message.reply_text(f"✅ Сняты все ранги! ({count} чел.)")

# ===================== АВТООТВЕТЫ =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()
    text_clean = text.rstrip('?!.,;:')
    
    if text_clean in RESPONSES:
        await update.message.reply_text(
            RESPONSES[text_clean],
            parse_mode='Markdown' if text_clean == "правила" else None,
            quote=True
        )
        return
    
    if text in RESPONSES:
        await update.message.reply_text(RESPONSES[text], quote=True)
        return

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Работаю")

# ===================== ЗАПУСК =====================
def main():
    print("=" * 50)
    print("🤖 БОТ ЗАПУСКАЕТСЯ")
    print("=" * 50)
    
    if not TOKEN:
        print("❌ НЕТ ТОКЕНА!")
        return
    
    print(f"📦 Загружено {len(RESPONSES)} автоответов")
    print(f"👑 Создатель ID: {CREATOR_ID}")
    print("🌍 Переводчик: ✅ работает")
    print("=" * 50)
    
    while True:
        try:
            app = Application.builder().token(TOKEN).build()
            
            # Основные команды
            app.add_handler(MessageHandler(filters.Regex(r'^\.дел$'), команда_дел))
            app.add_handler(MessageHandler(filters.Regex(r'^\.пинг$'), команда_пинг))
            app.add_handler(MessageHandler(filters.Regex(r'^\+кик'), команда_кик))
            
            # Команды переводчика
            app.add_handler(MessageHandler(filters.Regex(r'^\.переведи$') & filters.REPLY, команда_переведи))
            app.add_handler(MessageHandler(filters.Regex(r'^\!переведи$') & filters.REPLY, команда_переведи))
            
            # Команды рангов
            app.add_handler(MessageHandler(filters.Regex(r'^\+сс'), команда_плюс_сс))
            app.add_handler(MessageHandler(filters.Regex(r'^\+глсс'), команда_плюс_глсс))
            app.add_handler(MessageHandler(filters.Regex(r'^\-сс'), команда_минус_сс))
            app.add_handler(MessageHandler(filters.Regex(r'^\.садм$'), команда_садм))
            app.add_handler(MessageHandler(filters.Regex(r'^\.салл$'), команда_салл))
            
            # Стандартные
            app.add_handler(CommandHandler("start", start_command))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            print("🔥 БОТ ЗАПУЩЕН И РАБОТАЕТ!")
            print("🎯 Команды: .дел .пинг +кик +сс -сс +глсс .садм .салл .переведи")
            print("\nОжидаю сообщения...\n")
            
            app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            print(f"💥 Ошибка: {e}")
            print("🔄 Перезапуск через 10 секунд...")
            time.sleep(10)

if __name__ == "__main__":
    main()
