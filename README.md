# EdgeRunners

<img src="assets/logo.png" width="200" alt="MueroSimy's Studio">

iPhone 定位修改與運動軌跡模擬工具 —— 內建高德地圖，用滑鼠點選或畫線，就能讓 iPhone 移動到任何地方。

> 本軟體由浙江大學學生 MueroSimy 開發，完全免費開源，僅供學習交流，嚴禁商業與違法用途。

---

## 下載

👉 **[下載最新版本](https://github.com/simymuero/EdgeRunners/releases/latest)**

下載 `EdgeRunners_vX.X.X_public.zip` → 解壓 → 雙擊 `EdgeRunners.exe`。
**不需要安裝 Python**，但需要先裝 iTunes（見下方系統需求）。

> ⚠️ 請下載 **Release** 裡的 zip，不要下載 GitHub 自動產生的 `Source code` 壓縮檔 —— 那是原始碼，沒有 exe。

## 功能

- **修改定位**：地圖上單擊任一位置 → 按「注入該座標」→ 手機 GPS 立刻跳過去
- **運動軌跡模擬**：右鍵拖曳畫出路線 → 設定速度與抖動 → 按「開始模擬」，手機沿路線移動
- **四種參數即時換算**：速度（m/s）、時速（km/h）、配速（min/km）同步顯示
- **抖動模擬**：0～3 公尺的左右搖晃 + 速度波動，讓軌跡不像機器畫的
- **循環路線**：自動用直線把終點接回起點，可指定重複圈數
- **預覽動畫**：開始前先用動畫跑一遍（**不會移動手機**）
- **常見定位**：常用地點一鍵跳轉，支援長按拖曳排序
- **座標自動換算**：高德（GCJ-02）↔ GPS（WGS-84），誤差 < 1 公分

## 系統需求

| 項目 | 需求 |
|---|---|
| 作業系統 | Windows 10 / 11（64 位元） |
| **Apple 手機通訊服務** | ⚠️ **必要**。Windows 需要 `Apple Mobile Device Service`（usbmuxd）才看得到 iPhone。<br>它**不是只有 iTunes 會裝**：Microsoft Store 的「Apple Devices」、愛思助手等第三方工具、部分筆電預裝的 Apple 軟體都可能已裝好。<br>沒有的話裝 [iTunes 官網版](https://www.apple.com/itunes/download/win64) 或 Microsoft Store 的「Apple Devices」，裝完**重新開機**。<br>程式會做**實際連線測試**判斷，不會只看服務名稱，所以能連就不會誤報。 |
| WebView2 | Win11 內建；Win10 需安裝 [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) |
| 手機 | iPhone，iOS 17 以上（需開啟「開發者模式」） |
| **傳輸線** | ⚠️ **必須能傳資料**（USB-C to C，或標明支援資料傳輸的線）。<br>只能充電的線會出現「手機有在充電，但電腦完全看不到裝置」—— 這是最常被誤判成程式問題的坑。<br>便宜的 A to C 線常常只接了電源線。 |
| 網路 | 只有地圖底圖需要；定位注入與軌跡模擬**完全離線可運作** |

程式啟動時會做**實際連線測試**（能不能跟 usbmuxd 通話）來判斷環境，而不是只看服務名稱 ——
所以「沒裝 iTunes 但已有其他工具裝好服務」的電腦不會被誤報。

## 快速開始

1. **先安裝 iTunes 並重新開機**（見上方系統需求，這是最常見的失敗原因）
2. 下載 `EdgeRunners_vX.X.X.zip` 並解壓（**解壓後整個資料夾一起帶著跑，不要只複製 exe**）
3. 手機插上 USB，解鎖，按「信任」
4. 手機開啟開發者模式：設定 → 隱私權與安全性 → 開發者模式 → 重開機
5. 手機設定 → 顯示與亮度 → 自動鎖定 → **永不**（否則模擬會中斷）
6. 雙擊 `EdgeRunners.exe`

第一次按「注入」或「開始模擬」時，程式會自動掛載開發者映像檔，需要 **30～90 秒**。

詳細操作與疑難排解請看隨附的 **`說明.html`**。

### 高德 Key 要自己申請

因為 Key 不能公開分享，程式首次啟動時地圖會是空的：

1. 到 [console.amap.com](https://console.amap.com/dev/key/app) 註冊（需實名認證）
2. 應用管理 → 建立新應用 → 添加 Key → 服務平台選「**Web端 (JSAPI)**」
3. 取得 **Key** 與 **安全密鑰 jscode**
4. 在程式右上角按 **⚙** 貼上 → 儲存並重載

## 從原始碼執行

```bash
git clone https://github.com/simymuero/EdgeRunners.git
cd EdgeRunners
python -m pip install -r requirements.txt
python app.py
```

開發模式支援幾個除錯參數：

```bash
python app.py --browser        # 改用預設瀏覽器開啟（不開 WebView2 視窗）
set ER_PORT=8790 && python app.py   # 固定連接埠，方便測試 API
```

## 打包成 exe

```bash
python -m pip install pyinstaller
build.bat
```

產出在 `dist\EdgeRunners\`。打包後的程式跟開發模式有兩個關鍵差異，已在程式內處理：

- 沒有系統 Python 可用 → 子行程改用 `EdgeRunners.exe --pmd <參數>` 呼叫內建的 pymobiledevice3
- 需要額外打包 `pykdebugparser/trace.codes` 與 `pytun_pmd3/wintun/*.dll`，否則定位指令會失敗

## 專案結構

```
EdgeRunners/
├── app.py               本機 HTTP 服務 + WebView2 視窗 + API
├── core/
│   ├── coords.py        WGS-84 / GCJ-02 / BD-09 座標轉換
│   ├── device.py        pymobiledevice3 子行程管理（全域鎖、忙碌旗標、輸出排空）
│   ├── track.py         軌跡生成（等弧長重採樣 + 抖動 + 閉環）與 GPX 輸出
│   ├── gpx.py           GPX 讀取
│   ├── locations.py     common_location.txt 解析
│   └── settings.py      設定檔讀寫
├── web/
│   ├── index.html       介面結構
│   ├── style.css        樣式
│   └── app.js           地圖、手勢、預覽動畫、API 呼叫
├── tools/
│   └── make_manual.py   產生說明.html（自動嵌入截圖）
├── build.spec           PyInstaller 設定
└── build.bat            一鍵打包
```

## 幾個實作上的坑（給想改的人）

| 問題 | 原因 | 解法 |
|---|---|---|
| 模擬跑到一半停住 | 每個 CLI 指令都會建一條 wintun tunnel，背景輪詢與模擬互搶 | 全域 CLI 鎖 + 忙碌時暫停輪詢 |
| 子行程莫名卡死 | `stdout=PIPE` 沒人讀，64KB 緩衝區寫滿就阻塞 | 獨立執行緒持續排空輸出 |
| 注入指令直接中斷 | `pymobiledevice3` 結束時會 `input("Press ENTER to exit>")` | 給子行程一條不關閉的 stdin |
| 模擬跑完卻永遠「進行中」 | 同上，行程卡在等 Enter | 超過總時長 1.5 秒就主動收掉 |
| 打包版無法定位 | 缺 `pykdebugparser/trace.codes` | PyInstaller `--collect-data pykdebugparser` |

## 授權

[MIT License](LICENSE)

地圖資料 © 高德地圖（AutoNavi）。本專案與高德、Apple 均無隸屬關係。
使用本工具造成的任何後果由使用者自行承擔。
