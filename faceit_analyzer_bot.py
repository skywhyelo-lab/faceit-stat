import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

import aiohttp
import matplotlib.pyplot as plt
import matplotlib
from io import BytesIO
import re

matplotlib.use('Agg')
plt.style.use('dark_background')

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
FACEIT_API_KEY = os.getenv('FACEIT_API_KEY', 'YOUR_API_KEY_HERE')
FACEIT_API_URL = "https://open.faceit.com/data/v4"
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
DB_PATH = "faceit_stats.db"

# States для ConversationHandler
WAITING_PROFILE1, WAITING_PROFILE2 = range(2)

# ==================== DATABASE ====================
class StatsDB:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            player1_id TEXT,
            player1_nickname TEXT,
            player2_id TEXT,
            player2_nickname TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            p1_stats TEXT,
            p2_stats TEXT,
            comparison TEXT
        )''')
        conn.commit()
        conn.close()

    def save_analysis(self, user_id: int, p1_id: str, p1_nick: str, p2_id: str, p2_nick: str, 
                     p1_stats: dict, p2_stats: dict, comparison: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO analyses 
                    (user_id, player1_id, player1_nickname, player2_id, player2_nickname, p1_stats, p2_stats, comparison)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                 (user_id, p1_id, p1_nick, p2_id, p2_nick, 
                  json.dumps(p1_stats), json.dumps(p2_stats), comparison))
        conn.commit()
        conn.close()

    def get_player_history(self, user_id: int, player_nickname: str, limit: int = 10) -> List[dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''SELECT timestamp, p1_stats, p2_stats FROM analyses 
                    WHERE user_id = ? AND (player1_nickname = ? OR player2_nickname = ?)
                    ORDER BY timestamp DESC LIMIT ?''',
                 (user_id, player_nickname, player_nickname, limit))
        results = c.fetchall()
        conn.close()
        
        history = []
        for ts, p1_stats, p2_stats in results:
            p1 = json.loads(p1_stats)
            p2 = json.loads(p2_stats)
            stats = p1 if p1['nickname'] == player_nickname else p2
            history.append({'timestamp': ts, 'stats': stats})
        return history

db = StatsDB()

# ==================== FACEIT API ====================
async def get_player_stats(nickname: str) -> Optional[dict]:
    """Получить статистику игрока с Faceit API"""
    headers = {"Authorization": f"Bearer {FACEIT_API_KEY}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            # Получить ID игрока
            async with session.get(f"{FACEIT_API_URL}/players", 
                                  params={"nickname": nickname},
                                  headers=headers) as resp:
                if resp.status != 200:
                    return None
                player_data = await resp.json()
                player_id = player_data['player_id']
            
            # Получить подробную статистику
            async with session.get(f"{FACEIT_API_URL}/players/{player_id}/stats/cs2",
                                  headers=headers) as resp:
                if resp.status != 200:
                    return None
                stats = await resp.json()
            
            # Получить последние матчи
            async with session.get(f"{FACEIT_API_URL}/players/{player_id}/history",
                                  params={"game": "cs2", "limit": 20},
                                  headers=headers) as resp:
                matches = await resp.json() if resp.status == 200 else {}
            
            return {
                'player_id': player_id,
                'nickname': player_data.get('nickname'),
                'avatar': player_data.get('avatar'),
                'stats': stats,
                'matches': matches
            }
    except Exception as e:
        logger.error(f"API Error: {e}")
        return None

def parse_player_stats(player_data: dict) -> dict:
    """Парсить и форматировать статистику"""
    stats = player_data['stats']
    lifetime_stats = stats.get('lifetime', {})
    
    # Извлечение основных метрик
    kd_ratio = float(lifetime_stats.get('Kills', 0)) / max(1, float(lifetime_stats.get('Deaths', 0)))
    hs_percent = float(lifetime_stats.get('Headshot %', 0))
    win_rate = float(lifetime_stats.get('Win Rate %', 0))
    matches = int(lifetime_stats.get('Matches', 0))
    
    # Статистика по картам
    map_stats = {}
    for key in lifetime_stats:
        if ' Wins' in key:
            map_name = key.replace(' Wins', '')
            wins = int(lifetime_stats.get(key, 0))
            total = int(lifetime_stats.get(f'{map_name} Matches', 1))
            map_stats[map_name] = {
                'wins': wins,
                'total': total,
                'wr': (wins / total * 100) if total > 0 else 0
            }
    
    return {
        'nickname': player_data['nickname'],
        'player_id': player_data['player_id'],
        'avatar': player_data['avatar'],
        'kd_ratio': round(kd_ratio, 2),
        'hs_percent': round(hs_percent, 1),
        'win_rate': round(win_rate, 1),
        'matches': matches,
        'kills': int(lifetime_stats.get('Kills', 0)),
        'deaths': int(lifetime_stats.get('Deaths', 0)),
        'headshots': int(lifetime_stats.get('Headshots', 0)),
        'map_stats': map_stats
    }

def compare_players(p1_stats: dict, p2_stats: dict) -> str:
    """Создать сравнение двух игроков"""
    lines = []
    lines.append(f"📊 <b>Сравнение: {p1_stats['nickname']} vs {p2_stats['nickname']}</b>\n")
    
    # K/D Ratio
    kd_winner = p1_stats['nickname'] if p1_stats['kd_ratio'] > p2_stats['kd_ratio'] else p2_stats['nickname']
    lines.append(f"⚔️ <b>K/D Ratio:</b> {p1_stats['nickname']} {p1_stats['kd_ratio']} vs {p2_stats['kd_ratio']} {p2_stats['nickname']}")
    lines.append(f"   ➜ Лучше: <b>{kd_winner}</b>\n")
    
    # Headshot %
    hs_winner = p1_stats['nickname'] if p1_stats['hs_percent'] > p2_stats['hs_percent'] else p2_stats['nickname']
    lines.append(f"🎯 <b>Headshot %:</b> {p1_stats['nickname']} {p1_stats['hs_percent']}% vs {p2_stats['hs_percent']}% {p2_stats['nickname']}")
    lines.append(f"   ➜ Лучше: <b>{hs_winner}</b>\n")
    
    # Win Rate
    wr_winner = p1_stats['nickname'] if p1_stats['win_rate'] > p2_stats['win_rate'] else p2_stats['nickname']
    lines.append(f"🏆 <b>Win Rate:</b> {p1_stats['nickname']} {p1_stats['win_rate']}% vs {p2_stats['win_rate']}% {p2_stats['nickname']}")
    lines.append(f"   ➜ Лучше: <b>{wr_winner}</b>\n")
    
    # Matches
    lines.append(f"📈 <b>Матчей сыграно:</b> {p1_stats['nickname']} {p1_stats['matches']} vs {p2_stats['matches']} {p2_stats['nickname']}\n")
    
    # Анализ карт
    lines.append("<b>🗺️ По картам:</b>\n")
    all_maps = set(p1_stats['map_stats'].keys()) | set(p2_stats['map_stats'].keys())
    for map_name in sorted(all_maps):
        p1_map = p1_stats['map_stats'].get(map_name)
        p2_map = p2_stats['map_stats'].get(map_name)
        
        if p1_map and p2_map:
            p1_wr = p1_map['wr']
            p2_wr = p2_map['wr']
            winner = "👤" if p1_wr > p2_wr else "🤖" if p2_wr > p1_wr else "⚖️"
            lines.append(f"  {map_name}: {p1_stats['nickname']} {p1_wr:.0f}% {winner} {p2_wr:.0f}% {p2_stats['nickname']}")
        elif p1_map:
            lines.append(f"  {map_name}: {p1_stats['nickname']} {p1_map['wr']:.0f}% 📍 (не играет)")
        else:
            lines.append(f"  {map_name}: (не играет) 📍 {p2_stats['nickname']} {p2_map['wr']:.0f}%")
    
    # Рекомендации
    lines.append("\n💡 <b>Рекомендации:</b>")
    
    if p1_stats['hs_percent'] < 25:
        lines.append(f"  • {p1_stats['nickname']}: работай над точностью (headshot {p1_stats['hs_percent']}%)")
    
    if p2_stats['hs_percent'] < 25:
        lines.append(f"  • {p2_stats['nickname']}: работай над точностью (headshot {p2_stats['hs_percent']}%)")
    
    map_weakness_p1 = min(p1_stats['map_stats'].items(), key=lambda x: x[1]['wr'], default=None)
    if map_weakness_p1 and map_weakness_p1[1]['wr'] < 40:
        lines.append(f"  • {p1_stats['nickname']}: слабо на {map_weakness_p1[0]} ({map_weakness_p1[1]['wr']:.0f}% WR)")
    
    map_weakness_p2 = min(p2_stats['map_stats'].items(), key=lambda x: x[1]['wr'], default=None)
    if map_weakness_p2 and map_weakness_p2[1]['wr'] < 40:
        lines.append(f"  • {p2_stats['nickname']}: слабо на {map_weakness_p2[0]} ({map_weakness_p2[1]['wr']:.0f}% WR)")
    
    return "\n".join(lines)

def create_comparison_chart(p1_stats: dict, p2_stats: dict) -> BytesIO:
    """Создать график сравнения"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle(f'{p1_stats["nickname"]} vs {p2_stats["nickname"]}', fontsize=16, fontweight='bold')
    
    # K/D Ratio
    ax = axes[0, 0]
    players = [p1_stats['nickname'], p2_stats['nickname']]
    kd = [p1_stats['kd_ratio'], p2_stats['kd_ratio']]
    bars = ax.bar(players, kd, color=['#ff6b6b', '#4ecdc4'])
    ax.set_ylabel('K/D Ratio')
    ax.set_title('K/D Ratio')
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom')
    
    # Headshot %
    ax = axes[0, 1]
    hs = [p1_stats['hs_percent'], p2_stats['hs_percent']]
    bars = ax.bar(players, hs, color=['#ff6b6b', '#4ecdc4'])
    ax.set_ylabel('Headshot %')
    ax.set_title('Headshot %')
    ax.set_ylim(0, 100)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom')
    
    # Win Rate
    ax = axes[1, 0]
    wr = [p1_stats['win_rate'], p2_stats['win_rate']]
    bars = ax.bar(players, wr, color=['#ff6b6b', '#4ecdc4'])
    ax.set_ylabel('Win Rate %')
    ax.set_title('Win Rate %')
    ax.set_ylim(0, 100)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom')
    
    # Matches
    ax = axes[1, 1]
    matches = [p1_stats['matches'], p2_stats['matches']]
    bars = ax.bar(players, matches, color=['#ff6b6b', '#4ecdc4'])
    ax.set_ylabel('Matches')
    ax.set_title('Total Matches')
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom')
    
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, facecolor='#1e1e1e')
    buf.seek(0)
    plt.close()
    return buf

# ==================== TELEGRAM HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовый экран"""
    keyboard = [
        [InlineKeyboardButton("📊 Анализировать", callback_data='analyze')],
        [InlineKeyboardButton("📈 История", callback_data='history')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎮 <b>Faceit Stats Analyzer</b>\n\n"
        "Анализирую статистику игроков на Faceit и даю подробный отчет.\n\n"
        "Выбери что хочешь сделать:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def analyze_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало анализа - запрос первого игрока"""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "👤 <b>Введи ник первого игрока (или ссылку на профиль Faceit)</b>:\n\n"
        "Пример: <code>skywhyelo</code>\n"
        "или: <code>https://www.faceit.com/en/players/skywhyelo</code>",
        parse_mode=ParseMode.HTML
    )
    return WAITING_PROFILE1

async def get_profile1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить первого игрока"""
    text = update.message.text.strip()
    nickname = extract_nickname(text)
    
    context.user_data['profile1'] = nickname
    
    await update.message.reply_text(
        f"✅ Первый игрок: <b>{nickname}</b>\n\n"
        "👤 <b>Теперь введи ник второго игрока:</b>",
        parse_mode=ParseMode.HTML
    )
    return WAITING_PROFILE2

async def get_profile2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить второго игрока и выполнить анализ"""
    text = update.message.text.strip()
    nickname = extract_nickname(text)
    
    profile1 = context.user_data['profile1']
    profile2 = nickname
    
    # Показываем статус загрузки
    msg = await update.message.reply_text("⏳ Загружаю статистику...")
    
    try:
        # Получаем данные
        p1_data = await get_player_stats(profile1)
        p2_data = await get_player_stats(profile2)
        
        if not p1_data:
            await msg.edit_text(f"❌ Не найден игрок: <b>{profile1}</b>", parse_mode=ParseMode.HTML)
            return ConversationHandler.END
        
        if not p2_data:
            await msg.edit_text(f"❌ Не найден игрок: <b>{profile2}</b>", parse_mode=ParseMode.HTML)
            return ConversationHandler.END
        
        # Парсим статистику
        p1_stats = parse_player_stats(p1_data)
        p2_stats = parse_player_stats(p2_data)
        
        # Создаем отчет
        comparison_text = compare_players(p1_stats, p2_stats)
        
        # Сохраняем в БД
        db.save_analysis(update.message.from_user.id, p1_stats['player_id'], p1_stats['nickname'],
                        p2_stats['player_id'], p2_stats['nickname'], p1_stats, p2_stats, comparison_text)
        
        # Отправляем текстовый отчет
        await msg.edit_text(comparison_text, parse_mode=ParseMode.HTML)
        
        # Создаем и отправляем график
        chart = create_comparison_chart(p1_stats, p2_stats)
        await update.message.reply_photo(
            photo=chart,
            caption="📊 Визуальное сравнение",
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Error in analysis: {e}")
        await msg.edit_text(f"❌ Ошибка при анализе: {str(e)}", parse_mode=ParseMode.HTML)
    
    return ConversationHandler.END

async def history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать историю анализов"""
    await update.callback_query.answer()
    
    await update.callback_query.edit_message_text(
        "📈 <b>История анализов</b>\n\n"
        "Введи ник игрока для просмотра истории его статистики:",
        parse_mode=ParseMode.HTML
    )

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать помощь"""
    await update.callback_query.answer()
    
    help_text = (
        "<b>📚 Справка</b>\n\n"
        "<b>Команды:</b>\n"
        "/start - главное меню\n"
        "/analyze - начать анализ двух игроков\n"
        "/compare <ник1> <ник2> - быстрый анализ\n\n"
        "<b>Что анализирует бот:</b>\n"
        "✓ K/D Ratio - отношение убийств к смертям\n"
        "✓ Headshot % - процент выстрелов в голову\n"
        "✓ Win Rate - процент выигранных матчей\n"
        "✓ Статистика по картам\n"
        "✓ Общее кол-во матчей\n\n"
        "<b>Рекомендации:</b>\n"
        "Анализирует слабые места и дает советы по улучшению 💡"
    )
    
    await update.callback_query.edit_message_text(help_text, parse_mode=ParseMode.HTML)

async def quick_compare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрая команда /compare"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /compare <ник1> <ник2>\n"
            "Пример: /compare skywhyelo romanch1k"
        )
        return
    
    profile1 = context.args[0]
    profile2 = context.args[1]
    
    msg = await update.message.reply_text("⏳ Загружаю статистику...")
    
    try:
        p1_data = await get_player_stats(profile1)
        p2_data = await get_player_stats(profile2)
        
        if not p1_data or not p2_data:
            await msg.edit_text("❌ Один из игроков не найден")
            return
        
        p1_stats = parse_player_stats(p1_data)
        p2_stats = parse_player_stats(p2_data)
        
        comparison_text = compare_players(p1_stats, p2_stats)
        
        await msg.edit_text(comparison_text, parse_mode=ParseMode.HTML)
        
        chart = create_comparison_chart(p1_stats, p2_stats)
        await update.message.reply_photo(photo=chart, caption="📊 Сравнение")
        
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)}")

def extract_nickname(text: str) -> str:
    """Извлечь ник из текста или ссылки"""
    # Если это ссылка
    if 'faceit.com/en/players/' in text:
        return text.split('/players/')[-1].strip('/')
    # Если это просто ник
    return text.strip()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок"""
    query = update.callback_query
    
    if query.data == 'analyze':
        return await analyze_start(update, context)
    elif query.data == 'history':
        return await history_callback(update, context)
    elif query.data == 'help':
        return await help_callback(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена"""
    await update.message.reply_text("❌ Анализ отменен. /start для меню")
    return ConversationHandler.END

# ==================== MAIN ====================
def main():
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler для анализа
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("analyze", analyze_start),
            CallbackQueryHandler(analyze_start, pattern='^analyze$')
        ],
        states={
            WAITING_PROFILE1: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_profile1)],
            WAITING_PROFILE2: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_profile2)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("compare", quick_compare))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("🤖 Бот запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()
