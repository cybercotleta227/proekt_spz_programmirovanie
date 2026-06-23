import sqlite3
import requests
import ssl
import aiohttp
import urllib3
import json
import re
import os
from datetime import datetime
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from vkbottle.http import AiohttpClient


bot = Bot(token="vk1.a.z8V2eZxwan-UC0sAJNNmYdLBJ0eEx-Rru6OabompBCE58kwY4BXVgiKRNdt-vX4rlk2oNgYyw0eWraBCldn55zYn4v7y4ee8q1TyYepeZZ2Zhf2XyhDgmpxGmuQt2VWkTbUNAxlcsW4U0ojlazU1fjVOklbU6CRpAgsaWTJmL6fiKC8POP-ZL9GBkta_yQ129a0vCghOGBziG9_uf02ocw")


ADMIN_VK_ID = 123456789  


HEROES_DATABASE = {
    1: "Anti-Mage", 2: "Axe", 3: "Bane", 4: "Bloodseeker", 5: "Crystal Maiden",
    6: "Drow Ranger", 7: "Earthshaker", 8: "Juggernaut", 9: "Mirana", 10: "Morphling",
    11: "Nevermore (SF)", 12: "Phantom Lancer", 13: "Puck", 14: "Pudge", 15: "Razor",
    16: "Sand King", 17: "Storm Spirit", 18: "Sven", 19: "Tiny", 20: "Vengeful Spirit",
    21: "Windranger", 22: "Zeus", 23: "Kunkka", 25: "Lina", 26: "Lion", 27: "Shadow Shaman",
    28: "Slardar", 29: "Tidehunter", 30: "Witch Doctor", 31: "Lich", 32: "Riki",
    33: "Enigma", 34: "Tinker", 35: "Sniper", 36: "Necrophos", 37: "Warlock",
    38: "Beastmaster", 39: "Queen of Pain", 40: "Venomancer", 41: "Faceless Void",
    42: "Skeleton King (WK)", 43: "Death Prophet", 44: "Phantom Assassin", 45: "Pugna",
    46: "Templar Assassin", 47: "Viper", 48: "Luna", 49: "Dragon Knight", 50: "Dazzle",
    51: "Clockwerk", 52: "Leshrac", 53: "Nature's Prophet", 54: "Lifestealer", 55: "Dark Seer",
    56: "Clinkz", 57: "Omniknight", 58: "Enchantress", 59: "Huskar", 60: "Night Stalker",
    61: "Broodmother", 62: "Bounty Hunter", 63: "Weaver", 64: "Jakiro", 65: "Batrider",
    66: "Chen", 67: "Spectre", 68: "Ancient Apparition", 69: "Doom", 70: "Ursa",
    71: "Spirit Breaker", 72: "Gyrocopter", 73: "Alchemist", 74: "Invoker", 75: "Silencer",
    76: "Outworld Destroyer", 77: "Lycan", 78: "Brewmaster", 79: "Shadow Demon", 80: "Lone Druid",
    81: "Chaos Knight", 82: "Meepo", 83: "Treant Protector", 84: "Ogre Magi", 85: "Undying",
    86: "Rubick", 87: "Disruptor", 88: "Nyx Assassin", 89: "Naga Siren", 90: "Keeper of the Light",
    91: "Io", 92: "Visage", 93: "Slark", 94: "Medusa", 95: "Troll Warlord",
    96: "Centaur Warrunner", 97: "Magnus", 98: "Timbersaw", 99: "Bristleback", 100: "Tusk",
    101: "Skywrath Mage", 102: "Abaddon", 103: "Elder Titan", 104: "Legion Commander",
    105: "Techies", 106: "Ember Spirit", 107: "Earth Spirit", 108: "Underlord", 109: "Terrorblade",
    110: "Phoenix", 111: "Oracle", 112: "Winter Wyvern", 113: "Arc Warden", 114: "Monkey King",
    119: "Dark Willow", 120: "Pangolier", 121: "Grimstroke", 123: "Hoodwink", 126: "Void Spirit",
    128: "Snapfire", 129: "Mars", 135: "Dawnbreaker", 136: "Marci", 137: "Primal Beast",
    138: "Muerta", 145: "Kez"
}


def log_event(level, message_text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_string = f"[{timestamp}] [{level.upper()}] {message_text}\n"
    print(log_string.strip())
    try:
        with open("bot_log.txt", "a", encoding="utf-8") as file:
            file.write(log_string)
    except Exception as e:
        print(f"Критическая ошибка записи лога: {e}")


def init_db():
    try:
        conn = sqlite3.connect("dota_stats.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_users (
                vk_user_id INTEGER UNIQUE,
                first_seen TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_stats (
                vk_user_id INTEGER, account_id INTEGER, win_count INTEGER, loss_count INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS match_stats (
                vk_user_id INTEGER, account_id INTEGER, match_id INTEGER, hero_name TEXT, kda TEXT, result TEXT
            )
        ''')
        conn.commit()
        conn.close()
        log_event("info", "База данных успешно инициализирована.")
    except Exception as e:
        log_event("error", f"Ошибка инициализации БД: {e}")

def parse_dota_rank(rank_tier):
    if not rank_tier:
        return "Скрытый ранг 👤"
    tier = rank_tier // 10
    stars = rank_tier % 10
    
    ranks = {
        1: "Рекрут (Herald)", 2: "Страж (Guardian)", 3: "Рыцарь (Crusader)",
        4: "Герой (Archon)", 5: "Властелин (Legend)", 6: "Божество (Ancient)",
        7: "Божество+ (Divine)", 8: "Титан (Immortal) 🏆"
    }
    rank_name = ranks.get(tier, "Неизвестно")
    if tier == 8:
        return rank_name
    return f"{rank_name} [{stars} ⭐]"

def search_player_by_nick(vanity_name):
    url = f"https://api.opendota.com/api/search?q={vanity_name}"
    try:
        response = requests.get(url, verify=False)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0].get("account_id")
    except Exception as e:
        log_event("error", f"Ошибка поиска по нику {vanity_name}: {e}")
    return None



def get_player_profile(account_id):
    url = f"https://api.opendota.com/api/players/{account_id}"
    try:
        response = requests.get(url, verify=False)
        if response.status_code == 200:
            data = response.json()
            profile = data.get("profile", {})
            return {
                "name": profile.get("personaname", "Неизвестный"),
                "rank_tier": data.get("rank_tier"),
                "leaderboard_rank": data.get("leaderboard_rank"),
                "mmr_estimate": data.get("mmr_estimate", {}).get("estimate", "Нет")
            }
    except Exception as e:
        log_event("error", f"Ошибка API профиля {account_id}: {e}")
    return None

def get_top_heroes(account_id):
    url = f"https://api.opendota.com/api/players/{account_id}/heroes"
    try:
        response = requests.get(url, verify=False)
        if response.status_code == 200:
            heroes_data = response.json()
            played_heroes = [h for h in heroes_data if h.get("games", 0) > 0]
            played_heroes.sort(key=lambda x: x.get("games", 0), reverse=True)
            
            top_three = []
            for h in played_heroes[:3]:
                hero_id = int(h.get("hero_id"))
                games = h.get("games", 0)
                wins = h.get("win", 0)
                winrate = round((wins / games) * 100, 2) if games > 0 else 0
                top_three.append({
                    "name": HEROES_DATABASE.get(hero_id, f"Hero {hero_id}"),
                    "games": games,
                    "winrate": winrate
                })
            return top_three
    except Exception as e:
        log_event("error", f"Ошибка API топ героев {account_id}: {e}")
    return None

def get_dota_wl(account_id):
    url = f"https://api.opendota.com/api/players/{account_id}/wl"
    try:
        response = requests.get(url, verify=False)
        if response.status_code == 200:
            data = response.json()
            return data.get("win", 0), data.get("lose", 0)
    except Exception as e:
        log_event("error", f"Ошибка API WL {account_id}: {e}")
    return None, None


def get_recent_3_matches(account_id):
    url = f"https://api.opendota.com/api/players/{account_id}/recentMatches"
    try:
        response = requests.get(url, verify=False)
        if response.status_code == 200 and len(response.json()) > 0:
            # Берём первые 3 матча из списка истории
            raw_matches = response.json()[:3]
            parsed_matches = []
            
            for match in raw_matches:
                match_id = match.get("match_id")
                hero_id = match.get("hero_id")
                
                hero_name = HEROES_DATABASE.get(hero_id, f"Hero ID: {hero_id}")
                kda = f"{match.get('kills', 0)}/{match.get('deaths', 0)}/{match.get('assists', 0)}"
                
                is_radiant = match.get("player_slot", 0) < 128
                result = "Победа 🏆" if (is_radiant == match.get("radiant_win", True)) else "Поражение 💔"
                
                parsed_matches.append({
                    "match_id": match_id,
                    "hero": hero_name,
                    "kda": kda,
                    "result": result,
                    "gpm": match.get("gold_per_min", 0),
                    "xpm": match.get("xp_per_min", 0),
                    "damage": match.get("hero_damage", 0),
                    "towers": match.get("tower_damage", 0),
                    "cs": match.get("last_hits", 0)
                })
            return parsed_matches
    except Exception as e:
        log_event("error", f"Ошибка API 3-х матчей {account_id}: {e}")
    return None



def check_and_register_user(vk_id):
    conn = sqlite3.connect("dota_stats.db")
    cursor = conn.cursor()
    cursor.execute("SELECT vk_user_id FROM bot_users WHERE vk_user_id = ?", (vk_id,))
    user = cursor.fetchone()
    if not user:
        now_str = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO bot_users VALUES (?, ?)", (vk_id, now_str))
        conn.commit()
        log_event("info", f"Зарегистрирован новый пользователь бота: {vk_id}")
    conn.close()

def save_wl_to_db(vk_id, account_id, wins, losses):
    conn = sqlite3.connect("dota_stats.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO player_stats VALUES (?, ?, ?, ?)", (vk_id, account_id, wins, losses))
    conn.commit()
    conn.close()

def save_match_to_db(vk_id, account_id, match_id, hero, kda, result):
    conn = sqlite3.connect("dota_stats.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO match_stats VALUES (?, ?, ?, ?, ?, ?)", (vk_id, account_id, match_id, hero, kda, result))
    conn.commit()
    conn.close()

def get_all_bot_users():
    conn = sqlite3.connect("dota_stats.db")
    cursor = conn.cursor()
    cursor.execute("SELECT vk_user_id FROM bot_users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def get_db_global_stats():
    conn = sqlite3.connect("dota_stats.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bot_users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM player_stats")
    total_wl_requests = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM match_stats")
    total_match_requests = cursor.fetchone()[0]
    conn.close()
    return total_users, total_wl_requests, total_match_requests


def get_menu_keyboard(account_id):
    return (
        Keyboard(inline=True)
        .add(Text("👤 Профиль", {"action": "profile", "id": int(account_id)}), color=KeyboardButtonColor.PRIMARY)
        .add(Text("🔥 Топ Герои", {"action": "top_heroes", "id": int(account_id)}), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("📊 Общая статистика", {"action": "wl", "id": int(account_id)}), color=KeyboardButtonColor.SECONDARY)
        # Переименовали кнопку для точности
        .add(Text("🎮 Последние 3 матча", {"action": "match", "id": int(account_id)}), color=KeyboardButtonColor.POSITIVE)
        .get_json()
    )

@bot.on.message()
async def main_handler(message: Message):
    check_and_register_user(message.from_id)
    raw_text = message.text.strip()

    # --- БЛОК 1: КОМАНДЫ АДМИНИСТРАТОРА ---
    if message.from_id == ADMIN_VK_ID:
        if raw_text.lower() == "/admin_stats":
            u_count, wl_count, m_count = get_db_global_stats()
            adm_msg = (
                f"⚙️ [АДМИН-ПАНЕЛЬ] Статистика бота:\n\n"
                f"👥 Всего пользователей в базе: {u_count}\n"
                f"📊 Запросов общей статы: {wl_count}\n"
                f"🎮 Запросов истории игр: {m_count}"
            )
            await message.answer(adm_msg)
            log_event("admin", f"Администратор {message.from_id} вызвал панель статистики.")
            return

        elif raw_text.lower().startswith("/broadcast "):
            broadcast_text = message.text[11:].strip()
            if not broadcast_text:
                await message.answer("❌ Текст рассылки не может быть пустым.")
                return
            all_users = get_all_bot_users()
            success_count = 0
            await message.answer(f"⏳ Запускаю рассылку на {len(all_users)} пользователей...")
            for user_id in all_users:
                try:
                    await bot.api.messages.send(user_id=user_id, message=broadcast_text, random_id=0)
                    success_count += 1
                except Exception:
                    pass
            await message.answer(f"✅ Рассылка завершена! Успешно доставлено: {success_count}/{len(all_users)}")
            log_event("admin", f"Администратор выполнил рассылку. Успешно: {success_count}")
            return


    if message.payload:
        try:
            payload_data = json.loads(message.payload)
            action = payload_data.get("action")
            account_id = payload_data.get("id")
            
            log_event("info", f"Пользователь {message.from_id} нажал кнопку [{action}] для ID {account_id}")

            if action == "profile":
                prof = get_player_profile(account_id)
                if not prof:
                    await message.answer("Профиль скрыт или недоступен.")
                    return
                rank_text = parse_dota_rank(prof["rank_tier"])
                if prof["leaderboard_rank"]:
                    rank_text += f" (Топ-{prof['leaderboard_rank']} Мира)"
                
                msg = (
                    f"👤 Дота-профиль игрока [{account_id}]:\n"
                    f"📝 Никнейм: {prof['name']}\n"
                    f"🏅 Ранг: {rank_text}\n"
                    f"🧮 Оценка MMR: {prof['mmr_estimate']}\n\n"
                    f"🔗 Ссылка на профиль:\nhttps://ru.dotabuff.com/players/{account_id}"
                )
                await message.answer(msg)
                return

            elif action == "top_heroes":
                top = get_top_heroes(account_id)
                if not top:
                    await message.answer("Не удалось загрузить сигнатурных героев. Профиль закрыт.")
                    return
                msg = f"🔥 Топ-3 лучших героя аккаунта {account_id}:\n\n"
                emojis = ["1️⃣", "2️⃣", "3️⃣"]
                for i, h in enumerate(top):
                    msg += f"{emojis[i]} {h['name']}\n   └ Игр: {h['games']} | Винрейт: {h['winrate']}%\n"
                await message.answer(msg)
                return

            elif action == "wl":
                wins, losses = get_dota_wl(account_id)
                if wins is None:
                    await message.answer("Данные не получены. Настройки приватности скрыты.")
                    return
                save_wl_to_db(message.from_id, account_id, wins, losses)
                total = wins + losses
                wr = round((wins / total) * 100, 2) if total > 0 else 0
                await message.answer(f"📊 Статистика {account_id}:\nПобед: {wins}\nПоражений: {losses}\nВинрейт: {wr}%\n\n✓ Логи сохранены!")
                return

            
            elif action == "match":
                matches = get_recent_3_matches(account_id)
                if not matches:
                    await message.answer("История игр недоступна. Откройте профиль в настройках Dota 2.")
                    return
                
                report_chunks = [f"🎮 Результаты последних 3 матчей [{account_id}]:\n"]
                match_emojis = ["1️⃣", "2️⃣", "3️⃣"]
                
                for idx, m in enumerate(matches):
                    
                    save_match_to_db(message.from_id, account_id, m["match_id"], m["hero"], m["kda"], m["result"])
                    
                    
                    match_report = (
                        f"\n{match_emojis[idx]} **Матч {idx+1}**\n"
                        f"🆔 ID Игры: {m['match_id']}\n"
                        f"🦸 Герой: {m['hero']}\n"
                        f"🏁 Результат: {m['result']}\n"
                        f"⚔️ Счёт KDA: {m['kda']}\n"
                        f"🌾 Добито крипов: {m['cs']}\n"
                        f"💰 Золото/Мин (GPM): {m['gpm']}\n"
                        f"🧪 Опыт/Мин (XPM): {m['xpm']}\n"
                        f"💥 Урон по героям: {m['damage']:,}\n"
                        f"🏰 Урон по зданиям: {m['towers']:,}\n"
                        f"────────────────────"
                    )
                    report_chunks.append(match_report)
                
                report_chunks.append("\n\n✓ Данные всех матчей сохранены в файл .db")
                final_text = "\n".join(report_chunks)
                
                await message.answer(final_text)
                return
        except Exception as e:
            log_event("error", f"Ошибка обработки payload кнопки: {e}")

    
    account_id = None

    if raw_text.isdigit():
        account_id = int(raw_text)

    elif "profiles/" in raw_text:
        match = re.search(r"profiles/(\d+)", raw_text)
        if match:
            account_id = int(match.group(1))

    elif "id/" in raw_text:
        match = re.search(r"id/([^/]+)", raw_text)
        if match:
            vanity_name = match.group(1)
            await message.answer("🔍 Распознана буквенная ссылка. Вычисляю ID игрока в Steam...")
            account_id = search_player_by_nick(vanity_name)

    if account_id:
        if account_id > 7656117960265728:
            account_id = account_id - 76561197960265728
            
        keyboard = get_menu_keyboard(account_id)
        await message.answer(
            f"🎯 Профиль {account_id} найден!\nВыберите тип аналитики ниже:",
            keyboard=keyboard
        )
        log_event("info", f"Пользователь {message.from_id} успешно запросил меню для ID: {account_id}")
    else:
        if raw_text.startswith("/"):
            return
        welcome_text = (
            "🤖 Привет!\n\n"
            "Просто отправь мне любой из вариантов:\n"
            "👉 ID игрока (например: 129416024)\n"
            "👉 Ссылку на Steam профиль (цифровую)\n\n"
        )
        await message.answer(welcome_text)


async def disable_ssl_check(bot_instance: Bot):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    bot_instance.api.http_client = AiohttpClient(connector=aiohttp.TCPConnector(ssl=ssl_context))
    log_event("info", "Проверка SSL-сертификатов успешно отключена.")

bot.on_startup.append(disable_ssl_check(bot))

if __name__ == "__main__":
    init_db()
    log_event("info", "Запуск BotPolling... Бот готов принимать сообщения.")
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    bot.run()