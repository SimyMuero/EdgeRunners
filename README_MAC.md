# EdgeRunners v0.5.2 — macOS 版建置說明

這是 **macOS 版的原始碼**，需要在 Mac 上執行一次打包，才會產生可雙擊的 `EdgeRunners.app`。

> 先前的 `EdgeRunners.app` 是 v0.3.1 的舊版；這份原始碼已升級到 **v0.5.2**，
> 補上了「模擬跑到一半停住」、「注入失敗誤判成功」、「找不到開發者模式」等修正。

---

## 為什麼要自己打包

`.app` 裡的 Python 程式是**編譯進去**的（`Contents/MacOS/EdgeRunners`），
在 Windows 上無法重新編譯 macOS 的應用程式，所以必須在 Mac 上跑一次打包。

好消息是：**整個流程只有 3 個指令**，不需要懂程式。

---

## 開始前準備

| 項目 | 說明 |
|---|---|
| macOS | 12 (Monterey) 以上 |
| Python | 3.11 ～ 3.13（**不支援 3.14**，因為 pymobiledevice3 的相依套件還沒跟上） |
| 網路 | 需要下載約 200 MB 的套件 |
| 手機 | iPhone，iOS 17 以上，需開啟開發者模式 |

### 安裝 Python（如果沒有）

```bash
# 先裝 Homebrew（若已裝過可跳過）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安裝 Python 3.12
brew install python@3.12
```

---

## 打包步驟

### 1. 解壓縮

把 `EdgeRunners_mac_src_v0.5.2.zip` 解壓到任意位置（例如 `~/Desktop/EdgeRunners`）。

### 2. 開啟終端機，進入資料夾

```bash
cd ~/Desktop/EdgeRunners
```

> 小技巧：在 Finder 對資料夾按右鍵 →「服務」→「新建位於檔案夾的終端機視窗」。

### 3. 執行打包腳本

```bash
chmod +x build_mac.sh
./build_mac.sh
```

腳本會自動：

1. 建立虛擬環境 `.venv`
2. 安裝 `requirements.txt` 的相依套件
3. 安裝 PyInstaller
4. 打包成 `dist/EdgeRunners.app`

**第一次大約 5～10 分鐘**，中間會跑很多訊息，正常。

### 4. 測試

```bash
open dist/EdgeRunners.app
```

---

## 首次開啟被 macOS 攔下怎麼辦

會看到「無法打開 EdgeRunners，因為無法驗證開發者」之類的訊息，這是正常的（應用程式沒有 Apple 簽章）。

**解法**：在 Finder 對 `EdgeRunners.app` **按右鍵 →「打開」→ 再按一次「打開」**。

之後就可以直接雙擊了。

---

## 設定檔位置

macOS 版把設定放在：

```
~/Library/Application Support/EdgeRunners/
├── config.json     高德 Key、視窗位置、常見定位
└── routes.json     已保存的路線
```

> 與 Windows 版不同（Windows 放在 exe 旁邊）。這是 macOS 的慣例，也避免寫入 `.app` 內部。

**要重設**：把這個資料夾刪掉，重新開啟程式即可。

---

## 與 Windows 版的差異

| 項目 | Windows | macOS |
|---|---|---|
| 打包產物 | `EdgeRunners.exe` + `_internal/` | `EdgeRunners.app` |
| iTunes 需求 | **必須**（提供 usbmuxd） | **不需要**（macOS 內建） |
| 設定檔位置 | 程式旁邊 | `~/Library/Application Support/EdgeRunners/` |
| 網路介面 | wintun（需要管理員權限） | utun（核心內建） |

---

## 需要回報什麼

測試時如果出問題，請把以下資訊記下來：

1. **能不能開啟視窗**（有無錯誤訊息）
2. **狀態列顯示什麼**（綠燈／紅字內容）
3. **按「注入該座標」後手機有沒有反應**
4. 終端機若有訊息，複製貼上

### 除錯模式（不打包也能跑）

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py            # 直接開視窗
python app.py --browser  # 用瀏覽器開，方便看 console
```

---

## 專案結構

```
EdgeRunners/
├── app.py              主程式（本機 HTTP 服務 + 視窗）
├── core/               座標轉換、裝置控制、軌跡生成、設定
├── web/                前端（地圖、手勢、UI）
├── assets/             icon.icns、logo
├── build_mac.spec      macOS 打包設定
├── build_mac.sh        一鍵打包腳本
└── requirements.txt    相依套件
```

---

## 授權

MIT License · 本軟體由浙江大學學生 MueroSimy 開發，完全免費開源，僅供學習交流。
