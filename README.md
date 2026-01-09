# Discord-Bot-With-Vibe-Coding

Python 版娛樂向 Discord Bot，提供：
- GIF 產生/搜尋（Tenor）
- 隨機笑話
- YouTube 播歌（語音頻道）
- 文字 RPG（探索/戰鬥流程）
- YouTube 新片自動推播
- 知識問答（偏輕鬆題庫 + 計分）

## 你需要準備什麼（API / 軟體）
- `DISCORD_TOKEN`：Discord Developer Portal 建立 Bot 後取得。
- 選填 `TENOR_KEY`：Tenor GIF API Key（沒有也能用 Bot；若未填，`/gif` 會自動換用「隨機貓咪 GIF」簡易來源）。
- `ffmpeg`：播歌功能需要（`/play`）。確保 `ffmpeg` 在系統 PATH 可執行。
  - Windows 常見做法：安裝 ffmpeg 後把 `bin` 加到 PATH，再用 `ffmpeg -version` 確認。

## 需要開哪些權限 / 設定
### Discord Developer Portal（Bot 設定）
- **Privileged Gateway Intents**：本專案不需要 Message Content Intent（已關閉），保留預設即可。
- **必要 Intents**：`Guilds`、`Voice States`（程式內已設定）。

### 邀請 Bot 到伺服器（OAuth2）
在 OAuth2 URL Generator 勾選：
- Scopes：`bot`、`applications.commands`
- Bot Permissions（建議最小集合）：
  - **文字**：`Send Messages`、`Embed Links`（GIF/嵌入訊息）、（選擇性）`Read Message History`
  - **語音**：`Connect`、`Speak`

> 若你希望自動推播到特定頻道，也要確保該頻道對 Bot 開放 `Send Messages` / `Embed Links`。

## 安裝與執行
```bash
pip install -r requirements.txt
cp .env.example .env  # 或自行建立 .env
# 編輯 .env 填入 DISCORD_TOKEN 與（選填）TENOR_KEY
python -m src.bot
```

## 指令（Slash）
- `/gif prompt:<文字>`：回傳一張對應主題的 GIF；若未設定 `TENOR_KEY`，會改回傳隨機貓咪 GIF。
- `/joke`：隨機笑話。
- `/play query:<YouTube 連結或關鍵字>`：可貼連結，也可直接輸入關鍵字（會自動搜尋第一首），加入語音頻道並播放（需 ffmpeg）。
- `/rpg action:start|help|explore|fight|flee|rest|potion|shop|status`：文字 RPG；下完指令會附帶互動按鈕面板，直接點選即可繼續探索/戰鬥。
- `/autofeed add channel_id:<YT頻道ID> target:<文字頻道>`：追蹤頻道並自動推播。
  - `/autofeed remove channel_id:<YT頻道ID>`
  - `/autofeed list`
- `/trivia ask`：出題
  - `/trivia answer choice:A|B|C|D`：回答
  - `/trivia score`：看分數

## 環境變數範例（.env）
```
DISCORD_TOKEN=your_discord_bot_token_here
TENOR_KEY=optional_tenor_api_key
```

## 注意事項
- 首次啟動會自動同步 Slash 指令；若指令沒有顯示，等待一下或重新登入/邀請 Bot。
- YouTube 音訊來源使用 `yt-dlp` 擷取串流，可能受地區/年齡限制或平台變更影響；若失效我可以再幫你改成「播放清單/搜尋/替代來源」模式。
