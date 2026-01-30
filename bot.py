import os
import time
import re
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

# ===================== ТВОЯ ГИФКА С ПИЦЦЕЙ =====================
PIZZA_GIF = "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExYjhiMjY4MjdwMm43cHY0MG9pcm54N24xdHFscXJiZGk2ZWFubzRlMiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Z3Dz0f7pNHns4/giphy.gif"

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
    "пицца": "",  # Пустая строка, так как будем отправлять только гифку
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

# ===================== КОМАНДА ИНФОФЛУД (ИСПРАВЛЕННАЯ) =====================
async def команда_инфофлуд(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда '.инфофлуд' - показывает статистику чата"""
    try:
        chat_id = update.message.chat_id
        
        # Получаем количество участников
        all_members_count = await context.bot.get_chat_member_count(chat_id)
        
        # Отправляем сообщение со статистикой (без ботов)
        message = (
            f"📊 <b>Информация о чате</b>\n"
            f"👥 <b>Участники:</b> {all_members_count}\n"
            f"🔗 <b>Ссылка на</b> <a href='https://t.me/lunacyyflood'>инфо</a>"
        )
        
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            quote=True,
            disable_web_page_preview=True  # скрывает ссылку снизу
        )
        
        print(f"📊 Отправил инфофлуд для чата {chat_id}")
        
    except Exception as e:
        print(f"❌ Ошибка в команде инфофлуд: {e}")
        await update.message.reply_text("❌ Не удалось получить информацию о чате...")

# ===================== КОМАНДА ПИЦЦЫ =====================
async def команда_пицца(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда 'пицца' - отправляет гифку с пиццей БЕЗ ПОДПИСИ"""
    try:
        # Отправляем гифку с пиццей БЕЗ ПОДПИСИ
        await update.message.reply_animation(
            animation=PIZZA_GIF,
            quote=True
        )
        
        print(f"🍕 Отправил пиццу пользователю {update.message.from_user.first_name}")
        
    except Exception as e:
        print(f"❌ Ошибка отправки пиццы: {e}")
        await update.message.reply_text("❌ Не удалось отправить пиццу...")

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
async def get_user_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        return user.id, user.username, user.first_name
    
    text = message.text or ""
    
    if '@' in text:
        match = re.search(r'@([a-zA-Z0-9_]{5,})', text)
        if match:
            username = match.group(1)
            try:
                user = await context.bot.get_chat(f"@{username}")
                return user.id, user.username, user.first_name
            except:
                return None, username, f"@{username}"
    
    match = re.search(r'(\d{9,})', text)
    if match:
        user_id = int(match.group(1))
        try:
            user = await context.bot.get_chat(user_id)
            return user.id, user.username, user.first_name
        except:
            return user_id, None, f"ID {user_id}"
    
    return None, None, None

# ===================== КОМАНДЫ МОДЕРАЦИИ =====================
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
    """Обработка сообщений"""
    text = update.message.text.lower().strip()
    text_clean = text.rstrip('?!.,;:')
    
    # Проверяем на заготовленные ответы
    if text_clean in RESPONSES:
        response = RESPONSES[text_clean]
        
        # Особый случай: если написали "пицца" - отправляем ТОЛЬКО гифку
        if text_clean == "пицца":
            try:
                await update.message.reply_animation(
                    animation=PIZZA_GIF,
                    quote=True
                )
                print(f"🍕 Отправил пиццу по запросу 'пицца'")
                return
            except:
                # Если не получилось отправить гифку
                await update.message.reply_text("❌ Не удалось отправить пиццу...", quote=True)
                return
        
        # Для всех остальных ответов отправляем текст
        if response:  # Только если есть текст для ответа
            await update.message.reply_text(
                response,
                parse_mode='Markdown' if text_clean == "правила" else None,
                quote=True
            )
        return
    
    if text in RESPONSES:
        response = RESPONSES[text]
        if response and text == "пицца":
            try:
                await update.message.reply_animation(
                    animation=PIZZA_GIF,
                    quote=True
                )
                print(f"🍕 Отправил пиццу по запросу 'пицца'")
            except:
                await update.message.reply_text("❌ Не удалось отправить пиццу...", quote=True)
        elif response:
            await update.message.reply_text(response, quote=True)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Работаю")

# ===================== ЗАПУСК БОТА =====================
def main():
    print("=" * 50)
    print("🤖 БОТ ЗАПУСКАЕТСЯ")
    print("=" * 50)
    
    if not TOKEN:
        print("❌ НЕТ ТОКЕНА!")
        return
    
    print(f"📦 Загружено {len(RESPONSES)} автоответов")
    print(f"👑 Создатель ID: {CREATOR_ID}")
    print(f"🍕 Гифка пиццы: ✅ загружена")
    print("=" * 50)
    
    while True:
        try:
            app = Application.builder().token(TOKEN).build()
            
            # Основные команды
            app.add_handler(MessageHandler(filters.Regex(r'^\.дел$'), команда_дел))
            app.add_handler(MessageHandler(filters.Regex(r'^\.пинг$'), команда_пинг))
            app.add_handler(MessageHandler(filters.Regex(r'^\+кик'), команда_кик))
            
            # Команда инфофлуд (исправленная)
            app.add_handler(MessageHandler(filters.Regex(r'^\.инфофлуд$'), команда_инфофлуд))
            
            # Команды рангов
            app.add_handler(MessageHandler(filters.Regex(r'^\+сс'), команда_плюс_сс))
            app.add_handler(MessageHandler(filters.Regex(r'^\+глсс'), команда_плюс_глсс))
            app.add_handler(MessageHandler(filters.Regex(r'^\-сс'), команда_минус_сс))
            app.add_handler(MessageHandler(filters.Regex(r'^\.садм$'), команда_садм))
            app.add_handler(MessageHandler(filters.Regex(r'^\.салл$'), команда_салл))
            
            # Команда пиццы (можно вызывать разными способами)
            app.add_handler(MessageHandler(filters.Regex(r'^пицца$'), команда_пицца))
            app.add_handler(MessageHandler(filters.Regex(r'^\.пицца$'), команда_пицца))
            app.add_handler(MessageHandler(filters.Regex(r'^!пицца$'), команда_пицца))
            
            # Стандартные
            app.add_handler(CommandHandler("start", start_command))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            print("🔥 БОТ ЗАПУЩЕН И РАБОТАЕТ!")
            print("🎯 Команды: .дел .пинг +кик +сс -сс +глсс .садм .салл")
            print("📊 Команда: .инфофлуд")
            print("🍕 Пицца: просто напиши 'пицца' или '.пицца'")
            print("\nОжидаю сообщения...\n")
            
            app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            print(f"💥 Ошибка: {e}")
            print("🔄 Перезапуск через 10 секунд...")
            time.sleep(10)

if __name__ == "__main__":
    main()
