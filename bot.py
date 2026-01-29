import os
import time
import re
import html
import logging
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes

try:
    from googletrans import Translator, LANGUAGES
    translator_available = True
except ImportError:
    print("⚠️ Библиотека 'googletrans' не установлена. Перевод недоступен.")
    print("ℹ️ Добавь в requirements.txt: googletrans==4.0.0-rc1")
    translator_available = False

# ===================== НАСТРОЙКИ =====================
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ НЕТ ТОКЕНА! Добавь переменную TOKEN")
    exit()

CREATOR_ID = 7416252489  # ЗАМЕНИ НА СВОЙ ID!

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
    """Получает ранг пользователя"""
    return user_ranks.get(user_id, "user")

def has_permission(user_id, required_rank):
    """Проверяет, имеет ли пользователь достаточный ранг"""
    rank_hierarchy = {
        "user": 0,
        "moderator": 1,
        "head_admin": 2,
        "creator": 3
    }
    user_rank = get_rank(user_id)
    return rank_hierarchy.get(user_rank, 0) >= rank_hierarchy.get(required_rank, 0)

def is_creator(user_id):
    """Проверяет, является ли пользователь создателем"""
    return get_rank(user_id) == "creator"

def is_head_admin_or_higher(user_id):
    """Проверяет, является ли пользователь главным админом или выше"""
    return has_permission(user_id, "head_admin")

def is_moderator_or_higher(user_id):
    """Проверяет, является ли пользователь модератором или выше"""
    return has_permission(user_id, "moderator")

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
async def get_user_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Получает пользователя из:
    1. Ответа на сообщение
    2. @username в тексте
    3. ID в тексте
    Возвращает (user_id, username, display_name)
    """
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
                # Пробуем получить информацию о пользователе
                user = await context.bot.get_chat(f"@{username}")
                return user.id, user.username, user.first_name
            except:
                # Если не получается, возвращаем что есть
                return None, username, f"@{username}"
    
    # 3. ID в тексте (цифры от 9 символов)
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
        await update.message.reply_text("❌ Ответьте на текстовое сообщение для перевода!")
        await update.message.delete()
        return
    
    # Получаем текст для перевода
    text_to_translate = update.message.reply_to_message.text
    
    if not translator_available:
        await update.message.reply_text("❌ Переводчик недоступен!")
        await update.message.delete()
        return
    
    try:
        # Создаем переводчик
        translator = Translator()
        
        # Определяем язык исходного текста
        detected = translator.detect(text_to_translate)
        source_lang = detected.lang
        source_lang_name = LANGUAGES.get(source_lang, source_lang).capitalize()
        
        # Определяем целевой язык
        if source_lang in ['ru', 'uk', 'be']:  # Русский, Украинский, Белорусский → Английский
            target_lang = 'en'
            target_lang_name = "английский"
        elif source_lang == 'en':  # Английский → Русский
            target_lang = 'ru'
            target_lang_name = "русский"
        else:  # Любой другой язык → Русский
            target_lang = 'ru'
            target_lang_name = "русский"
        
        # Переводим текст
        translated = translator.translate(
            text_to_translate, 
            src=source_lang, 
            dest=target_lang
        )
        
        # Формируем ответ
        if len(text_to_translate) > 100:
            original_preview = text_to_translate[:100] + "..."
        else:
            original_preview = text_to_translate
        
        response = (
            f"🌍 **Перевод**\n\n"
            f"**С:** {source_lang_name}\n"
            f"**На:** {target_lang_name}\n\n"
            f"📝 **Оригинал:**\n`{original_preview}`\n\n"
            f"✅ **Перевод:**\n`{translated.text}`"
        )
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
        # Удаляем команду .переведи
        await update.message.delete()
        
    except Exception as e:
        print(f"❌ Ошибка перевода: {e}")
        await update.message.reply_text("❌ Не удалось перевести текст")
        await update.message.delete()

# ===================== КОМАНДЫ МОДЕРАЦИИ =====================
async def команда_дел(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда .дел - удалить сообщение (только по ответу)"""
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    if update.message.reply_to_message:
        try:
            await update.message.reply_to_message.delete()
            await update.message.delete()
            print(f"🗑️ Удалил сообщение от {update.message.reply_to_message.from_user.first_name}")
        except Exception as e:
            print(f"❌ Ошибка удаления: {e}")
            try:
                await update.message.reply_text("❌ Не могу удалить сообщение!")
            except:
                pass
    else:
        await update.message.reply_text("❌ Ответьте на сообщение для удаления!")
        await update.message.delete()

async def команда_пинг(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда .пинг - проверка пинга"""
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    start_time = time.time()
    sent_message = await update.message.reply_text("🏓 Измеряю пинг...")
    end_time = time.time()
    ping_ms = round((end_time - start_time) * 1000, 2)
    await sent_message.edit_text(f"🏓 Пинг бота: {ping_ms}мс")

async def команда_кик(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда +кик - исключить пользователя"""
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    user_id, username, display_name = await get_user_from_message(update, context)
    
    if not user_id:
        await update.message.reply_text("❌ Укажите пользователя: ответьте на сообщение, @username или ID")
        await update.message.delete()
        return
    
    # Проверки безопасности
    if is_creator(user_id):
        await update.message.reply_text("❌ Нельзя кикать создателя!")
        await update.message.delete()
        return
    
    if has_permission(user_id, get_rank(update.message.from_user.id)):
        await update.message.reply_text("❌ Нельзя кикать пользователя с равным или высшим ранком!")
        await update.message.delete()
        return
    
    # Выполнение кика
    try:
        await context.bot.ban_chat_member(
            chat_id=update.message.chat_id,
            user_id=user_id,
            until_date=datetime.now() + timedelta(seconds=30)
        )
        await context.bot.unban_chat_member(update.message.chat_id, user_id)
        
        await update.message.reply_text(f"🚪 {display_name} был исключен из группы!")
        print(f"🚪 Кикнул пользователя: {display_name} (ID: {user_id})")
        
    except Exception as e:
        error_msg = str(e).lower()
        if "not enough rights" in error_msg or "administrator" in error_msg:
            await update.message.reply_text("❌ У бота нет прав на исключение!")
        else:
            await update.message.reply_text(f"❌ Ошибка: {str(e)[:100]}")

async def команда_плюс_сс(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда +сс - назначить модератором"""
    if not is_head_admin_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    user_id, username, display_name = await get_user_from_message(update, context)
    
    if not user_id:
        await update.message.reply_text("❌ Укажите пользователя: ответьте на сообщение, @username или ID")
        await update.message.delete()
        return
    
    # Проверки
    if is_creator(user_id):
        await update.message.reply_text("❌ Нельзя изменять ранг создателя!")
        await update.message.delete()
        return
    
    if has_permission(user_id, get_rank(update.message.from_user.id)):
        await update.message.reply_text("❌ Нельзя назначать ранг пользователю с равным или высшим ранком!")
        await update.message.delete()
        return
    
    # Назначение модератором
    user_ranks[user_id] = "moderator"
    await update.message.reply_text(f"✅ {display_name} назначен Модератором!")
    print(f"👤 Назначен модератор: {display_name} (ID: {user_id})")

async def команда_плюс_глсс(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда +глсс - назначить главным админом"""
    if not is_creator(update.message.from_user.id):
        await update.message.delete()
        return
    
    user_id, username, display_name = await get_user_from_message(update, context)
    
    if not user_id:
        await update.message.reply_text("❌ Укажите пользователя: ответьте на сообщение, @username или ID")
        await update.message.delete()
        return
    
    # Проверки
    if is_creator(user_id):
        await update.message.reply_text("❌ Это создатель!")
        await update.message.delete()
        return
    
    # Назначение главным админом
    user_ranks[user_id] = "head_admin"
    await update.message.reply_text(f"✅ {display_name} назначен Главным Администратором!")
    print(f"👑 Назначен главный админ: {display_name} (ID: {user_id})")

async def команда_минус_сс(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда -сс - снять ранг"""
    if not is_head_admin_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    user_id, username, display_name = await get_user_from_message(update, context)
    
    if not user_id:
        await update.message.reply_text("❌ Укажите пользователя: ответьте на сообщение, @username или ID")
        await update.message.delete()
        return
    
    # Проверки
    if is_creator(user_id):
        await update.message.reply_text("❌ Нельзя изменять ранг создателя!")
        await update.message.delete()
        return
    
    if has_permission(user_id, get_rank(update.message.from_user.id)):
        await update.message.reply_text("❌ Нельзя снимать ранг пользователю с равным или высшим ранком!")
        await update.message.delete()
        return
    
    # Снятие ранга
    if user_id in user_ranks:
        old_rank = user_ranks[user_id]
        del user_ranks[user_id]
        await update.message.reply_text(f"✅ С {display_name} снят ранг ({old_rank})!")
        print(f"🗑️ Снят ранг у: {display_name} (ID: {user_id}), был: {old_rank}")
    else:
        await update.message.reply_text(f"⚠️ {display_name} не имеет ранга!")
        await update.message.delete()

async def команда_садм(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда .садм - список всех рангов"""
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    if len(user_ranks) <= 1:  # Только создатель
        await update.message.reply_text("👑 Есть только Создатель!")
        return
    
    # Сортируем по рангам
    rank_order = {"creator": 0, "head_admin": 1, "moderator": 2}
    sorted_users = sorted(
        [(uid, rank) for uid, rank in user_ranks.items() if uid != CREATOR_ID],
        key=lambda x: rank_order.get(x[1], 99)
    )
    
    text = "👑 Список рангов:\n\n"
    
    # Создатель
    try:
        creator_user = await context.bot.get_chat(CREATOR_ID)
        username = f"@{creator_user.username}" if creator_user.username else "нет @"
        text += f"👑 Создатель: {creator_user.first_name} {username}\n\n"
    except:
        text += f"👑 Создатель: ID {CREATOR_ID}\n\n"
    
    # Остальные ранги
    for user_id, rank in sorted_users:
        try:
            user = await context.bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else "нет @"
            
            if rank == "head_admin":
                rank_name = "👑 Администратор"
            elif rank == "moderator":
                rank_name = "⚡ Модератор"
            else:
                rank_name = rank
            
            text += f"{rank_name}: {user.first_name} {username}\n"
        except:
            text += f"{rank}: ID {user_id}\n"
    
    await update.message.reply_text(text)

async def команда_салл(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда .салл - снять ВСЕ ранги (кроме создателя)"""
    if not is_creator(update.message.from_user.id):
        await update.message.delete()
        return
    
    # Сохраняем создателя
    saved_creator = {CREATOR_ID: "creator"}
    
    # Считаем сколько было админов/модераторов
    removed_count = len(user_ranks) - 1  # Минус создатель
    
    # Оставляем только создателя
    user_ranks.clear()
    user_ranks.update(saved_creator)
    
    await update.message.reply_text(f"✅ Сняты все ранги! Удалено: {removed_count} пользователей")
    print(f"🔥 Сняты все ранги, остался только создатель")

# ===================== УЛУЧШЕННЫЕ АВТООТВЕТЫ =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка сообщений:
    - Регистр не важен (Сиси = сиси = СИСИ)
    - Игнорирует знаки препинания в конце
    - Реагирует на точное совпадение
    """
    original_text = update.message.text.strip()
    
    # Приводим к нижнему регистру для сравнения
    text_lower = original_text.lower()
    
    # Убираем знаки препинания в конце
    text_clean = text_lower.rstrip('?!.,;:')
    
    # Вариант 1: Точное совпадение с очищенным текстом
    if text_clean in RESPONSES:
        await update.message.reply_text(
            RESPONSES[text_clean],
            parse_mode='Markdown' if text_clean == "правила" else None
        )
        return
    
    # Вариант 2: Точное совпадение с оригинальным (нижний регистр)
    if text_lower in RESPONSES:
        await update.message.reply_text(
            RESPONSES[text_lower],
            parse_mode='Markdown' if text_lower == "правила" else None
        )
        return
    
    # Вариант 3: Проверяем если сообщение начинается с ключевых слов
    # (например: "Сиси, привет" → найдет "сиси")
    first_word = text_clean.split()[0] if text_clean else ""
    if first_word in ["сиси", "бот", "луми"] and first_word in RESPONSES:
        await update.message.reply_text(RESPONSES[first_word])
        return
    
    # Вариант 4: Проверяем фразы типа "доброе утро сиси"
    words = text_clean.split()
    if len(words) >= 2:
        # Ищем "сиси" в любом месте и проверяем время суток
        if "сиси" in words:
            if "утро" in words or "утра" in words:
                await update.message.reply_text("Что в этом утре особенного..")
                return
            elif "день" in words or "дня" in words:
                await update.message.reply_text("День? Какой ещё день..")
                return
            elif "вечер" in words or "вечера" in words:
                await update.message.reply_text("Вечер.. снова ты..")
                return
            elif "ночь" in words or "ночи" in words or "ночи" in text_clean:
                await update.message.reply_text("Спи или не спи… всё равно ничего не закончится.")
                return
            elif "привет" in words:
                await update.message.reply_text("Опять ты.. чего надо?")
                return

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text("🤖 Работаю")

# ===================== ЗАПУСК БОТА =====================
def main():
    """Запуск бота с переподключением"""
    print("=" * 50)
    print("🤖 БОТ ЗАПУСКАЕТСЯ")
    print("=" * 50)
    
    if not TOKEN:
        print("❌ НЕТ ТОКЕНА! Добавь переменную TOKEN в Railway → Variables")
        return
    
    print(f"📦 Загружено {len(RESPONSES)} автоответов")
    print(f"👑 Создатель ID: {CREATOR_ID}")
    
    if translator_available:
        print("🌍 Переводчик: ✅ доступен")
    else:
        print("🌍 Переводчик: ❌ недоступен (установи googletrans)")
    
    print("ℹ️ Команды: .дел .пинг +кик +сс -сс +глсс .садм .салл .переведи")
    print("=" * 50)
    
    # Бесконечный цикл с переподключением
    while True:
        try:
            app = Application.builder().token(TOKEN).build()
            
            # КОМАНДЫ МОДЕРАЦИИ
            app.add_handler(MessageHandler(filters.Regex(r'^\.дел$'), команда_дел))
            app.add_handler(MessageHandler(filters.Regex(r'^\.пинг$'), команда_пинг))
            app.add_handler(MessageHandler(filters.Regex(r'^\+кик'), команда_кик))
            app.add_handler(MessageHandler(filters.Regex(r'^\.переведи$') & filters.REPLY, команда_переведи))
            app.add_handler(MessageHandler(filters.Regex(r'^\!переведи$') & filters.REPLY, команда_переведи))
            
            # КОМАНДЫ УПРАВЛЕНИЯ РАНГАМИ
            app.add_handler(MessageHandler(filters.Regex(r'^\+сс'), команда_плюс_сс))
            app.add_handler(MessageHandler(filters.Regex(r'^\+глсс'), команда_плюс_глсс))
            app.add_handler(MessageHandler(filters.Regex(r'^\-сс'), команда_минус_сс))
            app.add_handler(MessageHandler(filters.Regex(r'^\.садм$'), команда_садм))
            app.add_handler(MessageHandler(filters.Regex(r'^\.салл$'), команда_салл))
            
            # СТАНДАРТНЫЕ КОМАНДЫ
            app.add_handler(CommandHandler("start", start_command))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            print("🔥 БОТ ЗАПУЩЕН И РАБОТАЕТ!")
            print("📌 Команды работают с: ответами, @username, ID")
            print("🌍 Переводчик работает с: .переведи или !переведи (ответьте на сообщение)")
            print("\nОжидаю сообщения...\n")
            
            app.run_polling(drop_pending_updates=True, close_loop=False)
            
        except Exception as e:
            print(f"💥 Критическая ошибка: {e}")
            print("🔄 Перезапуск через 10 секунд...")
            time.sleep(10)

if __name__ == "__main__":
    main()
