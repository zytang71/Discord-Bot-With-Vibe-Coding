from __future__ import annotations

import asyncio
import os
import random
import xml.etree.ElementTree as ET

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from yt_dlp import YoutubeDL

load_dotenv()

DISCORD_TOKEN = (os.getenv("DISCORD_TOKEN") or "").strip()
TENOR_KEY = (os.getenv("TENOR_KEY") or "").strip() or None


intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


JOKES = [
    "我問電腦：可以關機了嗎？它回我：Ctrl+Alt+Del 你自己來。",
    "為什麼程式設計師喜歡大自然？因為那裡有樹 (trees) 和根 (roots)。",
    "工程師的心靈雞湯：人生不順就先 git revert。",
    "沒有 bug 的程式不一定是好程式，但有測試的程式比較安心。",
    "有一天 0 遇到 8，0 說：哇，你的腰帶好時尚。",
]


TRIVIA_QUESTIONS: list[dict] = [
    {"question": "地球上最大的海洋是？", "choices": ["大西洋", "印度洋", "太平洋", "北冰洋"], "answer": "C"},
    {"question": "貓咪發出咕嚕聲通常代表？", "choices": ["很生氣", "很緊張", "覺得放鬆", "聽到雷聲"], "answer": "C"},
    {"question": "一年有幾個月是 31 天？", "choices": ["6", "7", "8", "9"], "answer": "B"},
    {"question": "哪個不是「水果」？（按常見食物分類）", "choices": ["番茄", "蘋果", "香蕉", "葡萄"], "answer": "A"},
    {"question": "「哈利波特」的學校叫什麼？", "choices": ["霍格華茲", "魔法森林學院", "阿茲卡班", "德姆蘭"], "answer": "A"},
    {"question": "太陽系中最接近太陽的行星是？", "choices": ["水星", "金星", "地球", "火星"], "answer": "A"},
    {"question": "下列哪個是哺乳類？", "choices": ["鯊魚", "海豚", "章魚", "海星"], "answer": "B"},
    {"question": "「一公尺」等於幾公分？", "choices": ["10", "100", "1000", "10000"], "answer": "B"},
    {"question": "披薩最常見的切法是？", "choices": ["正方形", "三角形", "圓形", "星形"], "answer": "B"},
    {"question": "台灣常見的便利商店不包含？", "choices": ["7-ELEVEN", "全家", "萊爾富", "Costco"], "answer": "D"},
    {"question": "「OK」手勢通常代表？", "choices": ["不行", "可以", "快跑", "別說話"], "answer": "B"},
    {"question": "下列哪個顏色不是彩虹的七色之一？", "choices": ["紅", "橙", "粉", "紫"], "answer": "C"},
    {"question": "一天有幾小時？", "choices": ["12", "18", "24", "36"], "answer": "C"},
    {"question": "「熊貓」最常吃的是？", "choices": ["竹子", "魚", "肉", "果子"], "answer": "A"},
    {"question": "世界上使用人口最多的語言是？（以母語人口常見說法）", "choices": ["英文", "西班牙文", "中文", "法文"], "answer": "C"},
    {"question": "打招呼最常見的時間用語：早上好對應？", "choices": ["Good night", "Good morning", "Good bye", "Good luck"], "answer": "B"},
    {"question": "下列哪個是「行星」不是「恆星」？", "choices": ["太陽", "北極星", "火星", "天狼星"], "answer": "C"},
    {"question": "「剪刀石頭布」中，剪刀贏什麼？", "choices": ["石頭", "布", "剪刀", "全部"], "answer": "B"},
    {"question": "哪個是常見的社群平台？", "choices": ["Discord", "Photoshop", "Excel", "Notepad"], "answer": "A"},
    {"question": "「番茄醬」常見的主要原料是？", "choices": ["蘋果", "番茄", "紅蘿蔔", "辣椒"], "answer": "B"},
    {"question": "下列哪個動物會冬眠？", "choices": ["熊（部分種類）", "長頸鹿", "海馬", "鴿子"], "answer": "A"},
    {"question": "「金字塔」最有名的所在地是？", "choices": ["希臘", "埃及", "日本", "巴西"], "answer": "B"},
    {"question": "下列哪個是樂器？", "choices": ["小提琴", "望遠鏡", "指南針", "吸塵器"], "answer": "A"},
    {"question": "常見的「紅綠燈」綠燈表示？", "choices": ["停", "慢", "走", "倒退"], "answer": "C"},
]


YDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
}


async def get_session() -> aiohttp.ClientSession:
    return bot.http_session


async def fetch_gif(query: str) -> str | None:
    # 首選 Tenor（需 API key），否則改用免費的 cataas 隨機貓咪 GIF 當簡易替代
    session = await get_session()
    if TENOR_KEY:
        params = {
            "q": query,
            "key": TENOR_KEY,
            "limit": 10,
            "contentfilter": "medium",
            "media_filter": "gif",
        }
        async with session.get("https://tenor.googleapis.com/v2/search", params=params) as resp:
            if resp.status < 400:
                data = await resp.json()
                results = data.get("results", [])
                if results:
                    picked = random.choice(results)
                    media = picked.get("media_formats", {})
                    gif = media.get("gif", {})
                    url = gif.get("url") or picked.get("itemurl")
                    if url:
                        return url
    # fallback：不需金鑰，提供一張隨機貓咪 GIF
    async with session.get("https://cataas.com/cat/gif") as resp:
        if resp.status < 400:
            return str(resp.url)
    return None


# ----------------------------
# RPG
# ----------------------------

rpg_state: dict[int, dict] = {}


def _xp_to_next(level: int) -> int:
    return 8 + level * 4


def _ensure_rpg(user_id: int) -> dict:
    if user_id not in rpg_state:
        rpg_state[user_id] = {
            "level": 1,
            "xp": 0,
            "gold": 0,
            "max_hp": 20,
            "hp": 20,
            "potions": 1,
            "encounter": None,  # {"name": str, "hp": int, "max_hp": int}
        }
    return rpg_state[user_id]


def _level_up_if_needed(state: dict) -> list[str]:
    messages: list[str] = []
    while state["xp"] >= _xp_to_next(state["level"]):
        state["xp"] -= _xp_to_next(state["level"])
        state["level"] += 1
        state["max_hp"] += 2
        state["hp"] = state["max_hp"]
        state["potions"] += 1
        messages.append(f"升級！現在等級 {state['level']}，最大 HP {state['max_hp']}，並獲得 1 瓶藥水。")
    return messages


def _rpg_status(state: dict) -> str:
    encounter = state.get("encounter")
    encounter_line = ""
    if encounter:
        encounter_line = f"\n遭遇中：{encounter['name']}（HP {encounter['hp']}/{encounter['max_hp']}）"
    return (
        f"等級 {state['level']} | XP {state['xp']}/{_xp_to_next(state['level'])}\n"
        f"HP {state['hp']}/{state['max_hp']} | 金幣 {state['gold']} | 藥水 {state['potions']}"
        f"{encounter_line}"
    )


def run_rpg_action(user_id: int, action: str) -> str:
    if action == "start":
        rpg_state[user_id] = {
            "level": 1,
            "xp": 0,
            "gold": 0,
            "max_hp": 20,
            "hp": 20,
            "potions": 1,
            "encounter": None,
        }
        return "冒險開始！用 /rpg explore 出門探索吧。"

    state = _ensure_rpg(user_id)

    if action == "help":
        return (
            "RPG 指令：\n"
            "- /rpg explore：探索（可能遇到怪/寶箱/休息點）\n"
            "- /rpg fight：戰鬥一回合（需要先探索遇到怪）\n"
            "- /rpg flee：逃跑（可能掉少量金幣）\n"
            "- /rpg rest：休息回血\n"
            "- /rpg potion：喝藥水回血\n"
            "- /rpg shop：花 5 金幣買 1 瓶藥水\n"
            "- /rpg status：查看狀態"
        )

    if action == "status":
        return _rpg_status(state)

    if action == "rest":
        heal = min(8 + state["level"], state["max_hp"] - state["hp"])
        state["hp"] += heal
        return f"你休息了一下，回復 {heal} HP。\n{_rpg_status(state)}"

    if action == "potion":
        if state["potions"] <= 0:
            return f"你沒有藥水了。\n{_rpg_status(state)}"
        if state["hp"] >= state["max_hp"]:
            return f"你已經滿血，不用喝藥水。\n{_rpg_status(state)}"
        state["potions"] -= 1
        heal = min(12, state["max_hp"] - state["hp"])
        state["hp"] += heal
        return f"你喝下藥水，回復 {heal} HP。\n{_rpg_status(state)}"

    if action == "shop":
        if state["gold"] < 5:
            return f"商店：藥水 5 金幣/瓶。你的金幣不夠。\n{_rpg_status(state)}"
        state["gold"] -= 5
        state["potions"] += 1
        return f"你買了一瓶藥水！\n{_rpg_status(state)}"

    encounter = state.get("encounter")

    if action == "explore":
        if encounter:
            return f"你已經在遭遇戰中了！先用 /rpg fight 或 /rpg flee。\n{_rpg_status(state)}"

        roll = random.random()
        if roll < 0.55:
            names = ["史萊姆", "小狼", "哥布林", "骷髏兵", "野豬"]
            name = random.choice(names)
            max_hp = 10 + state["level"] * 3 + random.randint(0, 4)
            state["encounter"] = {"name": name, "hp": max_hp, "max_hp": max_hp}
            return f"你遇到了 {name}！用 /rpg fight 開打，或 /rpg flee 逃跑。\n{_rpg_status(state)}"
        if roll < 0.75:
            gold = random.randint(2, 6)
            xp = random.randint(1, 4)
            state["gold"] += gold
            state["xp"] += xp
            msgs = [f"你找到一個小寶箱：+{gold} 金幣，+{xp} XP。"]
            msgs.extend(_level_up_if_needed(state))
            msgs.append(_rpg_status(state))
            return "\n".join(msgs)
        if roll < 0.90:
            heal = min(6 + state["level"], state["max_hp"] - state["hp"])
            state["hp"] += heal
            return f"你找到一處營火，回復 {heal} HP。\n{_rpg_status(state)}"
        state["gold"] += 1
        return f"你迷路了一小段路，但撿到 1 枚金幣。\n{_rpg_status(state)}"

    if action == "fight":
        if not encounter:
            return "目前沒有遇到怪，先用 /rpg explore 探索。"

        player_damage = random.randint(3, 6 + state["level"])
        encounter["hp"] -= player_damage
        lines = [f"你對 {encounter['name']} 造成 {player_damage} 傷害。"]

        if encounter["hp"] <= 0:
            reward_gold = random.randint(4, 8) + state["level"]
            reward_xp = random.randint(3, 6) + state["level"] // 2
            state["gold"] += reward_gold
            state["xp"] += reward_xp
            state["encounter"] = None
            lines.append(f"{encounter['name']} 倒下了！獲得 +{reward_gold} 金幣、+{reward_xp} XP。")
            lines.extend(_level_up_if_needed(state))
            lines.append(_rpg_status(state))
            return "\n".join(lines)

        monster_damage = random.randint(1, 4 + state["level"])
        state["hp"] -= monster_damage
        lines.append(f"{encounter['name']} 反擊，你受到 {monster_damage} 傷害。")

        if state["hp"] <= 0:
            lost = max(0, state["gold"] // 2)
            state["gold"] -= lost
            state["hp"] = state["max_hp"]
            state["encounter"] = None
            lines.append(f"你倒下了！損失 {lost} 金幣，醒來時已回滿血。")
            lines.append(_rpg_status(state))
            return "\n".join(lines)

        lines.append(_rpg_status(state))
        return "\n".join(lines)

    if action == "flee":
        if not encounter:
            return "目前沒有遇到怪，不用逃跑。"
        penalty = min(state["gold"], random.randint(0, 3))
        state["gold"] -= penalty
        state["encounter"] = None
        return f"你成功逃跑了！掉了 {penalty} 金幣。\n{_rpg_status(state)}"

    return "未知行動。用 /rpg help 查看可用指令。"


# ----------------------------
# Trivia
# ----------------------------


class RPGView(discord.ui.View):
    """簡易互動式按鈕版 RPG。"""

    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        actions = [
            ("explore", "探索"),
            ("fight", "戰鬥"),
            ("flee", "逃跑"),
            ("rest", "休息"),
            ("potion", "喝藥"),
            ("shop", "商店"),
            ("status", "狀態"),
            ("help", "幫助"),
        ]
        for value, label in actions:
            self.add_item(self._make_button(value, label))

    def _make_button(self, action: str, label: str) -> discord.ui.Button:
        button = discord.ui.Button(label=label, style=discord.ButtonStyle.primary)

        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("這不是你的冒險進度喔。", ephemeral=True)
                return
            result = run_rpg_action(self.owner_id, action)
            await interaction.response.edit_message(content=result, view=self)

        button.callback = callback  # type: ignore
        return button

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

trivia_state: dict[int, dict] = {}
trivia_scores: dict[int, dict[int, int]] = {}


class TriviaGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="trivia", description="知識問答（輕鬆版）")

    @app_commands.command(name="ask", description="出一題")
    async def ask(self, interaction: discord.Interaction):
        picked = random.choice(TRIVIA_QUESTIONS)
        trivia_state[interaction.channel_id] = picked
        choices_text = "\n".join(
            f"{label}. {picked['choices'][idx]}"
            for idx, label in enumerate(["A", "B", "C", "D"])
        )
        await interaction.response.send_message(
            f"題目：{picked['question']}\n{choices_text}\n用 `/trivia answer` 回答。"
        )

    @app_commands.command(name="answer", description="回答目前題目")
    @app_commands.choices(
        choice=[
            app_commands.Choice(name="A", value="A"),
            app_commands.Choice(name="B", value="B"),
            app_commands.Choice(name="C", value="C"),
            app_commands.Choice(name="D", value="D"),
        ]
    )
    async def answer(self, interaction: discord.Interaction, choice: app_commands.Choice[str]):
        current = trivia_state.get(interaction.channel_id)
        if not current:
            await interaction.response.send_message("目前沒有題目，先用 `/trivia ask` 出題。", ephemeral=True)
            return

        trivia_state.pop(interaction.channel_id, None)
        correct = current["answer"]
        if choice.value == correct:
            guild_scores = trivia_scores.setdefault(interaction.guild_id or 0, {})
            guild_scores[interaction.user.id] = guild_scores.get(interaction.user.id, 0) + 1
            await interaction.response.send_message("答對了！+1 分")
        else:
            await interaction.response.send_message(f"可惜答錯，正解是 {correct}。")

    @app_commands.command(name="score", description="查看本伺服器排行榜（前 10）")
    async def score(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id or 0
        scores = trivia_scores.get(guild_id, {})
        if not scores:
            await interaction.response.send_message("目前沒有分數紀錄，先玩幾題吧。")
            return
        top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:10]
        lines = []
        for i, (user_id, score) in enumerate(top, start=1):
            lines.append(f"{i}. <@{user_id}>：{score} 分")
        await interaction.response.send_message("排行榜（前 10）：\n" + "\n".join(lines))


# ----------------------------
# Auto-feed (YouTube)
# ----------------------------

video_subscriptions: dict[int, dict[str, dict]] = {}


async def fetch_latest_video(channel_id: str) -> tuple[str | None, str | None]:
    session = await get_session()
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    async with session.get(feed_url) as resp:
        if resp.status >= 400:
            return None, None
        xml_text = await resp.text()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None, None
    ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        return None, None
    vid_el = entry.find("yt:videoId", ns)
    title_el = entry.find("atom:title", ns)
    if vid_el is None or title_el is None:
        return None, None
    return vid_el.text, title_el.text


class AutoFeed(app_commands.Group):
    def __init__(self):
        super().__init__(name="autofeed", description="自動推播 YouTube 新影片")

    @app_commands.command(name="add", description="新增追蹤頻道")
    @app_commands.describe(channel_id="YouTube 頻道 ID", target="推播到的文字頻道")
    async def add(self, interaction: discord.Interaction, channel_id: str, target: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        vid, title = await fetch_latest_video(channel_id)
        if not vid:
            await interaction.edit_original_response(content="無法取得影片，請確認頻道 ID。")
            return
        guild_map = video_subscriptions.setdefault(interaction.guild_id or 0, {})
        guild_map[channel_id] = {"target": target.id, "last_video": vid}
        await interaction.edit_original_response(content=f"已追蹤頻道 {channel_id}；目前最新：{title}")

    @app_commands.command(name="remove", description="移除追蹤頻道")
    @app_commands.describe(channel_id="YouTube 頻道 ID")
    async def remove(self, interaction: discord.Interaction, channel_id: str):
        guild_map = video_subscriptions.setdefault(interaction.guild_id or 0, {})
        existed = guild_map.pop(channel_id, None)
        await interaction.response.send_message("已移除。" if existed else "未找到此頻道。", ephemeral=True)

    @app_commands.command(name="list", description="列出追蹤頻道")
    async def list(self, interaction: discord.Interaction):
        guild_map = video_subscriptions.get(interaction.guild_id or 0, {})
        if not guild_map:
            await interaction.response.send_message("目前沒有追蹤任何頻道。")
            return
        lines = [
            f"ID: {cid} -> <#{meta['target']}> (最後推播: {meta['last_video']})"
            for cid, meta in guild_map.items()
        ]
        await interaction.response.send_message("\n".join(lines))


@tasks.loop(minutes=5)
async def poll_videos():
    if not video_subscriptions:
        return
    session = await get_session()
    for guild_id, feeds in list(video_subscriptions.items()):
        for channel_id, meta in list(feeds.items()):
            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            try:
                async with session.get(feed_url) as resp:
                    if resp.status >= 400:
                        continue
                    xml_text = await resp.text()
                root = ET.fromstring(xml_text)
                ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
                entry = root.find("atom:entry", ns)
                if entry is None:
                    continue
                vid_el = entry.find("yt:videoId", ns)
                title_el = entry.find("atom:title", ns)
                if vid_el is None or title_el is None:
                    continue
                video_id = vid_el.text
                if video_id == meta.get("last_video"):
                    continue
                meta["last_video"] = video_id
                feeds[channel_id] = meta
                target_channel = bot.get_channel(meta["target"]) or await bot.fetch_channel(meta["target"])
                if isinstance(target_channel, discord.abc.Messageable):
                    await target_channel.send(
                        f"新影片發布：{title_el.text}\nhttps://www.youtube.com/watch?v={video_id}"
                    )
            except Exception as exc:
                print(f"推播輪詢錯誤 ({channel_id}): {exc}")


# ----------------------------
# Commands
# ----------------------------


@bot.tree.command(name="gif", description="生成或搜尋一張 GIF")
@app_commands.describe(prompt="想要的主題，例如 happy cat")
async def gif(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    url = await fetch_gif(prompt)
    if not url:
        await interaction.edit_original_response(content="找不到相關 GIF，或尚未設定 TENOR_KEY。")
        return
    embed = discord.Embed(title=f"GIF: {prompt}")
    embed.set_image(url=url)
    await interaction.edit_original_response(embed=embed)


@bot.tree.command(name="joke", description="給你一個隨機笑話")
async def joke(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(JOKES))


async def _ensure_voice(interaction: discord.Interaction) -> discord.VoiceClient | None:
    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("需要在伺服器中使用此指令。", ephemeral=True)
        return None
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("請先加入語音頻道。", ephemeral=True)
        return None
    voice_client = interaction.guild.voice_client if interaction.guild else None
    if voice_client and voice_client.channel == interaction.user.voice.channel:
        return voice_client
    try:
        return await interaction.user.voice.channel.connect()
    except Exception:
        await interaction.response.send_message("無法連線語音頻道，請確認機器人權限。", ephemeral=True)
        return None


@bot.tree.command(name="play", description="播放 YouTube 音樂（可貼連結或輸入關鍵字）")
@app_commands.describe(query="YouTube 連結，或輸入關鍵字我幫你搜尋")
async def play(interaction: discord.Interaction, query: str):
    voice = await _ensure_voice(interaction)
    if not voice:
        return
    await interaction.response.defer()

    def ydl_extract():
        with YoutubeDL(YDL_OPTS) as ydl:
            target = query if query.startswith("http") else f"ytsearch1:{query}"
            info = ydl.extract_info(target, download=False)
            # ytsearch 回傳會包在 entries
            if "entries" in info:
                info = info["entries"][0]
            return info["url"], info.get("title", "音樂")

    try:
        loop = asyncio.get_running_loop()
        audio_url, title = await loop.run_in_executor(None, ydl_extract)
    except Exception as exc:
        await interaction.edit_original_response(content=f"抓取音訊失敗：{exc}")
        return

    try:
        source = await discord.FFmpegOpusAudio.from_probe(audio_url, options="-vn")
    except Exception:
        await interaction.edit_original_response(content="FFmpeg 初始化失敗，請確認已安裝並在 PATH。")
        return

    if voice.is_playing():
        voice.stop()
    voice.play(source, after=lambda e: print(f"播放錯誤: {e}") if e else None)
    await interaction.edit_original_response(content=f"正在播放：{title}")


@bot.tree.command(name="rpg", description="簡易文字 RPG")
@app_commands.choices(
    action=[
        app_commands.Choice(name="start", value="start"),
        app_commands.Choice(name="help", value="help"),
        app_commands.Choice(name="explore", value="explore"),
        app_commands.Choice(name="fight", value="fight"),
        app_commands.Choice(name="flee", value="flee"),
        app_commands.Choice(name="rest", value="rest"),
        app_commands.Choice(name="potion", value="potion"),
        app_commands.Choice(name="shop", value="shop"),
        app_commands.Choice(name="status", value="status"),
    ]
)
async def rpg(interaction: discord.Interaction, action: app_commands.Choice[str]):
    result = run_rpg_action(interaction.user.id, action.value)
    view = RPGView(interaction.user.id)
    await interaction.response.send_message(result, view=view)


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game("娛樂中"))
    print(f"Logged in as {bot.user} (guilds={len(bot.guilds)})")


@bot.event
async def setup_hook():
    bot.http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))
    bot.tree.add_command(TriviaGroup())
    bot.tree.add_command(AutoFeed())
    poll_videos.start()
    await bot.tree.sync()


async def main():
    if not DISCORD_TOKEN:
        raise RuntimeError("缺少 DISCORD_TOKEN 環境變數")
    try:
        async with bot:
            await bot.start(DISCORD_TOKEN)
    finally:
        if hasattr(bot, "http_session") and not bot.http_session.closed:
            await bot.http_session.close()


if __name__ == "__main__":
    asyncio.run(main())
