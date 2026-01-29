import os
import time
import re
import logging
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes

# ===================== НАСТРОЙКИ =====================
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ НЕТ ТОКЕНА! Добавь переменную TOKEN в Railway → Variables")
    exit()

CREATOR_ID = 7416252489  # Замени на свой ID

# ===================== ХРАНИЛИЩА =====================
user_ranks = {
    CREATOR_ID: "creator"
}

RESPONSES = {
    "правила": "📜 С правилами можно ознакомиться [туть](https://telegra.ph/Rules-01-24-146)",
    "сиси": "Ну, привет... опять ты появляешься. Что на этот раз?",
    "сиси как дела": "Разве важно? Время идет, а я все так же свободна",
    "сиси что делаешь": "Отвечаю на твои глупые вопросы. А ты?",
    "кто такой этот ваш луми": "АХХ..луми..мой создатель",
    "луми": "Мхх..",
    "бот": "Ну чего тебе?",
}

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
def extract_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Извлекает целевого пользователя из:
    1. Ответа на сообщение
    2. Упоминания @username в тексте
    3. Указания ID в тексте
    Возвращает (user_id, username) или (None, None)
    """
    message = update.message
    text = message.text if message.text else ""
    
    # 1. Проверяем ответ на сообщение
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        return target.id, target.username
    
    # 2. Ищем упоминания @username в тексте
    username_match = re.search(r'@([a-zA-Z0-9_]{5,})', text)
    if username_match:
        username = username_match.group(1)
        # Здесь username, но нужно получить user_id
        # Будем возвращать username, а user_id получим позже
        return None, username
    
    # 3. Ищем ID в тексте (только цифры после команды)
    id_match = re.search(r'(?<!\d)(\d{8,})(?!\d)', text)
    if id_match:
        user_id = int(id_match.group(1))
        return user_id, None
    
    return None, None

async def resolve_user_id(context: ContextTypes.DEFAULT_TYPE, user_id: int = None, username: str = None):
    """Получает полную информацию о пользователе по ID или username"""
    if user_id:
        try:
            user = await context.bot.get_chat(user_id)
            return user.id, user.username, user.first_name
        except:
            return user_id, None, f"User {user_id}"
    
    if username:
        # Пытаемся получить информацию через поиск
        try:
            # Если username есть в чате
            members = await context.bot.get_chat_administrators(update.effective_chat.id)
            for member in members:
                if member.user.username and member.user.username.lower() == username.lower():
                    return member.user.id, member.user.username, member.user.first_name
        except:
            pass
        
        # Если не нашли, возвращаем как есть
        return None, username, f"@{username}"
    
    return None, None, None

def get_rank(user_id):
    return user_ranks.get(user_id, "user")

def has_permission(user_id, required_rank):
    rank_hierarchy = {
        "user": 0,
        "moderator": 1,
        "head_admin": 2,
        "creator": 3
    }
    user_rank = get_rank(user_id)
    return rank_hierarchy.get(user_rank, 0) >= rank_hierarchy.get(required_rank, 0)

def is_creator(user_id):
    return get_rank(user_id) == "creator"

def is_head_admin_or_higher(user_id):
    return has_permission(user_id, "head_admin")

def is_moderator_or_higher(user_id):
    return has_permission(user_id, "moderator")

# ===================== ОБНОВЛЕННЫЕ КОМАНДЫ =====================
async def команда_дел(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда .дел - удалить сообщение"""
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    if update.message.reply_to_message:
        try:
            await update.message.reply_to_message.delete()
            await update.message.delete()
            print(f"🗑️ Удалил сообщение от {update.message.reply_to_message.from_user.first_name}")
        except:
            await update.message.reply_text("❌ Не могу удалить сообщение!")
    else:
        await update.message.reply_text("❌ Ответьте на сообщение для удаления!")
        await update.message.delete()

async def команда_пинг(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда .пинг - проверка пинга"""
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Измеряю пинг...")
    end_time = time.time()
    await msg.edit_text(f"🏓 Пинг: {round((end_time - start_time) * 1000, 2)}мс")

async def команда_кик(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда +кик - исключить пользователя"""
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    # Получаем целевого пользователя
    user_id, username = extract_target_user(update, context)
    if not user_id and not username:
        await update.message.reply_text("❌ Укажите пользователя: ответьте на сообщение, @username или ID")
        await update.message.delete()
        return
    
    # Разрешаем user_id
    target_id, target_username, target_name = await resolve_user_id(context, user_id, username)
    if not target_id:
        await update.message.reply_text(f"❌ Не могу найти пользователя {username}")
        await update.message.delete()
        return
    
    # Проверка прав
    if is_creator(target_id):
        await update.message.reply_text("❌ Нельзя кикать создателя!")
        await update.message.delete()
        return
    
    if has_permission(target_id, get_rank(update.message.from_user.id)):
        await update.message.reply_text("❌ Нельзя кикать пользователя с равным или высшим рангом!")
        await update.message.delete()
        return
    
    # Выполняем кик
    try:
        await context.bot.ban_chat_member(
            chat_id=update.message.chat_id,
            user_id=target_id,
            until_date=datetime.now() + timedelta(seconds=30)
        )
        await context.bot.unban_chat_member(update.message.chat_id, target_id)
        await update.message.reply_text(f"🚪 {target_name} был исключен из группы!")
        print(f"🚪 Кикнул: {target_name} (ID: {target_id})")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:100]}")

async def команда_плюс_сс(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда +сс - назначить модератором"""
    if not is_head_admin_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    # Получаем целевого пользователя
    user_id, username = extract_target_user(update, context)
    if not user_id and not username:
        await update.message.reply_text("❌ Укажите пользователя: ответьте на сообщение, @username или ID")
        await update.message.delete()
        return
    
    # Разрешаем user_id
    target_id, target_username, target_name = await resolve_user_id(context, user_id, username)
    if not target_id:
        await update.message.reply_text(f"❌ Не могу найти пользователя {username}")
        await update.message.delete()
        return
    
    # Проверки
    if is_creator(target_id):
        await update.message.reply_text("❌ Нельзя изменять ранг создателя!")
        await update.message.delete()
        return
    
    if has_permission(target_id, get_rank(update.message.from_user.id)):
        await update.message.reply_text("❌ Нельзя назначать ранг пользователю с равным или высшим рангом!")
        await update.message.delete()
        return
    
    # Назначаем модератором
    user_ranks[target_id] = "moderator"
    await update.message.reply_text(f"✅ {target_name} назначен Модератором!")
    print(f"👤 Назначен модератор: {target_name} (ID: {target_id})")

async def команда_плюс_глсс(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда +глсс - назначить главным админом"""
    if not is_creator(update.message.from_user.id):
        await update.message.delete()
        return
    
    # Получаем целевого пользователя
    user_id, username = extract_target_user(update, context)
    if not user_id and not username:
        await update.message.reply_text("❌ Укажите пользователя: ответьте на сообщение, @username или ID")
        await update.message.delete()
        return
    
    # Разрешаем user_id
    target_id, target_username, target_name = await resolve_user_id(context, user_id, username)
    if not target_id:
        await update.message.reply_text(f"❌ Не могу найти пользователя {username}")
        await update.message.delete()
        return
    
    # Проверки
    if is_creator(target_id):
        await update.message.reply_text("❌ Это создатель!")
        await update.message.delete()
        return
    
    # Назначаем главным админом
    user_ranks[target_id] = "head_admin"
    await update.message.reply_text(f"✅ {target_name} назначен Главным Администратором!")
    print(f"👑 Назначен главный админ: {target_name} (ID: {target_id})")

async def команда_минус_сс(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда -сс - снять ранг"""
    if not is_head_admin_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    # Получаем целевого пользователя
    user_id, username = extract_target_user(update, context)
    if not user_id and not username:
        await update.message.reply_text("❌ Укажите пользователя: ответьте на сообщение, @username или ID")
        await update.message.delete()
        return
    
    # Разрешаем user_id
    target_id, target_username, target_name = await resolve_user_id(context, user_id, username)
    if not target_id:
        await update.message.reply_text(f"❌ Не могу найти пользователя {username}")
        await update.message.delete()
        return
    
    # Проверки
    if is_creator(target_id):
        await update.message.reply_text("❌ Нельзя изменять ранг создателя!")
        await update.message.delete()
        return
    
    if has_permission(target_id, get_rank(update.message.from_user.id)):
        await update.message.reply_text("❌ Нельзя снимать ранг пользователю с равным или высшим рангом!")
        await update.message.delete()
        return
    
    # Снимаем ранг
    if target_id in user_ranks:
        old_rank = user_ranks[target_id]
        del user_ranks[target_id]
        await update.message.reply_text(f"✅ С {target_name} снят ранг ({old_rank})!")
        print(f"🗑️ Снят ранг: {target_name} (ID: {target_id}), был: {old_rank}")
    else:
        await update.message.reply_text(f"⚠️ {target_name} не имеет ранга!")
        await update.message.delete()

async def команда_садм(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда .садм - список всех рангов"""
    if not is_moderator_or_higher(update.message.from_user.id):
        await update.message.delete()
        return
    
    if len(user_ranks) <= 1:
        await update.message.reply_text("👑 Есть только Создатель!")
        return
    
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
    
    # Остальные
    for user_id, rank in sorted_users:
        try:
            user = await context.bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else "нет @"
            rank_name = "👑 Администратор" if rank == "head_admin" else "⚡ Модератор"
            text += f"{rank_name}: {user.first_name} {username}\n"
        except:
            text += f"{rank}: ID {user_id}\n"
    
    await update.message.reply_text(text)

async def команда_салл(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда .салл - снять ВСЕ ранги"""
    if not is_creator(update.message.from_user.id):
        await update.message.delete()
        return
    
    removed_count = len(user_ranks) - 1
    user_ranks.clear()
    user_ranks[CREATOR_ID] = "creator"
    
    await update.message.reply_text(f"✅ Сняты все ранги! Удалено: {removed_count}")
    print(f"🔥 Сняты все ранги, остался только создатель")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений"""
    text = update.message.text.lower().strip()
    
    for keyword, response in RESPONSES.items():
        if ' ' not in keyword:
            if keyword in text.split():
                await update.message.reply_text(
                    response,
                    parse_mode='Markdown' if keyword == "правила" else None
                )
                return
        else:
            if keyword in text:
                await update.message.reply_text(
                    response,
                    parse_mode='Markdown' if keyword == "правила" else None
                )
                return

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Работаю")

# ===================== ЗАПУСК =====================
def main():
    print("=" * 50)
    print("🤖 БОТ ЗАПУСКАЕТСЯ")
    print("=" * 50)
    
    if not TOKEN:
        print("❌ НЕТ ТОКЕНА! Добавь переменную TOKEN")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # ОБНОВЛЕННЫЕ КОМАНДЫ - работают и по ответу, и по @username, и по ID
    app.add_handler(MessageHandler(filters.Regex(r'^\.дел$'), команда_дел))
    app.add_handler(MessageHandler(filters.Regex(r'^\.пинг$'), команда_пинг))
    app.add_handler(MessageHandler(filters.Regex(r'^\+кик(\s+.*)?$'), команда_кик))
    app.add_handler(MessageHandler(filters.Regex(r'^\+сс(\s+.*)?$'), команда_плюс_сс))
    app.add_handler(MessageHandler(filters.Regex(r'^\+глсс(\s+.*)?$'), команда_плюс_глсс))
    app.add_handler(MessageHandler(filters.Regex(r'^\-сс(\s+.*)?$'), команда_минус_сс))
    app.add_handler(MessageHandler(filters.Regex(r'^\.садм$'), команда_садм))
    app.add_handler(MessageHandler(filters.Regex(r'^\.салл$'), команда_салл))
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🔥 БОТ ЗАПУЩЕН И РАБОТАЕТ!")
    print("📌 Команды работают:")
    print("   1. По ответу на сообщение")
    print("   2. По @username: +кик @username")
    print("   3. По ID: +сс 123456789")
    print("\nОжидаю сообщения...\n")
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
