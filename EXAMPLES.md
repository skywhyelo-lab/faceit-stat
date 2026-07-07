# 📚 Примеры использования Faceit Stats Analyzer Bot

## 🎯 Типичные сценарии использования

### Сценарий 1: Проверить форму перед матчем

1. Открой Telegram бота
2. Напиши: `/compare skywhyelo romanch1k`
3. Получишь:
   - Сравнение K/D, HS%, WR
   - Графики
   - Советы по слабостям

**Результат:**
```
📊 Сравнение: skywhyelo vs romanch1k

⚔️ K/D Ratio: skywhyelo 1.24 vs 1.31 romanch1k
   ➜ Лучше: romanch1k

🎯 Headshot %: skywhyelo 28.5% vs 31.2% romanch1k
   ➜ Лучше: romanch1k

🏆 Win Rate: skywhyelo 52% vs 58% romanch1k
   ➜ Лучше: romanch1k

📈 Матчей сыграно: skywhyelo 412 vs 358 romanch1k

🗺️ По картам:
  Anubis: skywhyelo 48% ⚖️ 48% romanch1k
  Dust2: skywhyelo 55% 👤 51% romanch1k
  Inferno: skywhyelo 50% 🤖 54% romanch1k
  Mirage: skywhyelo 52% 👤 49% romanch1k
  Nuke: skywhyelo 45% 🤖 52% romanch1k
  Overpass: skywhyelo 49% 🤖 53% romanch1k
  Vertigo: skywhyelo 58% 👤 44% romanch1k

💡 Рекомендации:
  • romanch1k: слабо на Vertigo (44% WR)
  • skywhyelo: работай над точностью (headshot 28.5%)
```

---

### Сценарий 2: Интерактивный анализ

1. Напиши `/analyze`
2. Нажми кнопку "📊 Анализировать"
3. Введи: `skywhyelo`
4. Введи: `https://www.faceit.com/en/players/romanch1k`
5. Получи полный отчет + график

**Преимущество:** не нужно помнить точные ники, можно вставлять ссылки.

---

### Сценарий 3: Отслеживание прогресса

Анализируй одного игрока каждую неделю:

```
День 1: /compare skywhyelo dummy_opponent
День 8: /compare skywhyelo dummy_opponent
День 15: /compare skywhyelo dummy_opponent
```

Бот сохранит все данные в БД и сможет показать тренд:
- Растет ли K/D?
- Улучшается ли HS%?
- На каких картах прогресс?

---

## 🔧 Продвинутые команды и расширения

### Расширение 1: Анализ последних 20 матчей

Добавить в код отслеживание recent stats:

```python
async def get_recent_stats(nickname: str) -> dict:
    """Получить статистику последних матчей"""
    headers = {"Authorization": f"Bearer {FACEIT_API_KEY}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{FACEIT_API_URL}/players",
                              params={"nickname": nickname},
                              headers=headers) as resp:
            player_id = (await resp.json())['player_id']
        
        # Последние матчи
        async with session.get(f"{FACEIT_API_URL}/players/{player_id}/history",
                              params={"game": "cs2", "limit": 20},
                              headers=headers) as resp:
            matches = await resp.json()
    
    # Анализ последних 20 матчей
    recent_kd = []
    recent_wins = 0
    
    for match in matches['items']:
        stats = match['stats']
        kd = stats['K'] / max(1, stats['D'])
        recent_kd.append(kd)
        if stats['Result'] == '1':
            recent_wins += 1
    
    return {
        'recent_kd': sum(recent_kd) / len(recent_kd) if recent_kd else 0,
        'recent_wr': recent_wins / len(matches['items']) * 100,
        'trend': 'up' if recent_kd[-5:] > recent_kd[:-5] else 'down'
    }
```

### Расширение 2: Уведомления при достижении целей

```python
# Добавить отслеживание целей
GOALS = {
    'skywhyelo': {
        'target_elo': 3000,
        'target_hs': 35,
        'target_wr': 55
    },
    'romanch1k': {
        'target_elo': 2900,
        'target_hs': 32,
        'target_wr': 52
    }
}

async def check_goals(nickname: str, stats: dict):
    """Проверить достижение целей"""
    if nickname not in GOALS:
        return None
    
    goals = GOALS[nickname]
    achievements = []
    
    if stats['hs_percent'] >= goals['target_hs']:
        achievements.append(f"🎯 Достиг целевого HS: {stats['hs_percent']}%!")
    
    if stats['win_rate'] >= goals['target_wr']:
        achievements.append(f"🏆 Достиг целевого WR: {stats['win_rate']}%!")
    
    return achievements
```

### Расширение 3: Рейтинг команды

```python
async def team_rating(players: List[str]) -> dict:
    """Оценить силу команды"""
    stats_list = []
    
    for player in players:
        stats = parse_player_stats(await get_player_stats(player))
        stats_list.append(stats)
    
    avg_kd = sum(s['kd_ratio'] for s in stats_list) / len(stats_list)
    avg_hs = sum(s['hs_percent'] for s in stats_list) / len(stats_list)
    avg_wr = sum(s['win_rate'] for s in stats_list) / len(stats_list)
    
    # Рейтинг команды
    team_rating = (avg_kd * 50) + (avg_hs * 0.5) + (avg_wr * 0.5)
    
    return {
        'team_rating': team_rating,
        'avg_kd': avg_kd,
        'avg_hs': avg_hs,
        'avg_wr': avg_wr,
        'players': stats_list
    }
```

---

## 📊 Примеры вывода графиков

Бот создает график с 4 диаграммами:

```
┌─────────────────────────────────────┐
│   skywhyelo vs romanch1k            │
├─────────────────────────────────────┤
│  K/D Ratio      │  Headshot %       │
│  [████] 1.24    │  [████] 28.5%     │
│  [█████] 1.31   │  [█████] 31.2%    │
├─────────────────────────────────────┤
│  Win Rate %     │  Total Matches    │
│  [████████] 52% │  [████████] 412   │
│  [██████████]58%│  [███████] 358    │
└─────────────────────────────────────┘
```

---

## 🎮 Интеграция с другими инструментами

### Интеграция с Discord (бонус скрипт)

```python
# Если захочешь использовать Faceit анализ в Discord боте
import discord
from discord.ext import commands

class FaceitCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='compare')
    async def compare(self, ctx, player1: str, player2: str):
        """Сравнить игроков"""
        async with ctx.typing():
            p1 = await get_player_stats(player1)
            p2 = await get_player_stats(player2)
            
            comparison = compare_players(
                parse_player_stats(p1),
                parse_player_stats(p2)
            )
            
            embed = discord.Embed(
                title=f"{p1['nickname']} vs {p2['nickname']}",
                description=comparison,
                color=discord.Color.purple()
            )
            
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FaceitCog(bot))
```

---

## 💾 Работа с базой данных

### Просмотр истории анализов

```python
import sqlite3

def view_all_analyses():
    conn = sqlite3.connect('faceit_stats.db')
    c = conn.cursor()
    c.execute('SELECT * FROM analyses ORDER BY timestamp DESC LIMIT 20')
    
    for row in c.fetchall():
        print(f"{row[6]} - {row[3]} vs {row[5]}")
    
    conn.close()

# Запуск
view_all_analyses()
```

### Экспорт статистики в CSV

```python
import csv
from datetime import datetime

def export_stats(player_nickname: str, output_file: str = None):
    if output_file is None:
        output_file = f"{player_nickname}_stats.csv"
    
    conn = sqlite3.connect('faceit_stats.db')
    c = conn.cursor()
    
    c.execute('''SELECT timestamp, p1_stats, p2_stats 
                FROM analyses 
                WHERE player1_nickname = ? OR player2_nickname = ?
                ORDER BY timestamp DESC''',
             (player_nickname, player_nickname))
    
    results = c.fetchall()
    conn.close()
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Дата', 'K/D', 'HS%', 'WR%', 'Матчей'])
        
        for ts, p1_stats, p2_stats in results:
            p1 = json.loads(p1_stats)
            p2 = json.loads(p2_stats)
            stats = p1 if p1['nickname'] == player_nickname else p2
            
            writer.writerow([
                ts,
                stats['kd_ratio'],
                stats['hs_percent'],
                stats['win_rate'],
                stats['matches']
            ])
    
    print(f"✅ Экспортировано в {output_file}")

# Использование
export_stats('skywhyelo')
```

---

## 🚀 Готовые сценарии для быстрого анализа

### Перед матчем (2 мин)
```
/compare skywhyelo romanch1k
```

### После матча (проверить прогресс)
```
/analyze
[введи нику]
[введи нику]
```

### Еженедельный отчет
```
# Каждый понедельник в 10:00
/compare skywhyelo romanch1k
/compare владик skywhyelo
```

---

## 📝 Пользовательские метрики

Если нужны дополнительные метрики, вот как их добавить:

```python
def calculate_custom_metrics(stats: dict) -> dict:
    return {
        'consistency': stats['win_rate'] / 100,  # 0-1
        'aggression': stats['kd_ratio'] / 2,     # 0-1
        'precision': stats['hs_percent'] / 100,  # 0-1
        'experience': min(stats['matches'] / 1000, 1),  # 0-1
        'overall_score': (
            (stats['kd_ratio'] / 2) * 0.35 +
            (stats['hs_percent'] / 100) * 0.25 +
            (stats['win_rate'] / 100) * 0.25 +
            (min(stats['matches'] / 1000, 1)) * 0.15
        ) * 10  # 0-10
    }
```

---

## ✅ Чек-лист для использования

- [x] Установил зависимости
- [x] Получил Faceit API Key
- [x] Получил Telegram Bot Token
- [x] Запустил бота
- [x] Добавил бота в Telegram
- [x] Сделал первый анализ
- [x] Проверил графики
- [x] Сохранил результат в БД

**Готово! Теперь можешь анализировать статистику когда угодно!** 🎮
