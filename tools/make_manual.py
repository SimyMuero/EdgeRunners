# -*- coding: utf-8 -*-
"""產生 說明.html（截圖自動嵌入，單檔可攜）"""

import base64
import io
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SHOT_LOCATE = os.environ.get('SHOT_LOCATE', r'C:\Temp\ui_locate.png')
SHOT_SIM = os.environ.get('SHOT_SIM', r'C:\Temp\ui_sim.png')
SHOT_SET = os.environ.get('SHOT_SET', r'C:\Temp\ui_settings.png')
SHOT_WARN = os.environ.get('SHOT_WARN', r'C:\Temp\ui_warn.png')
OUT = os.path.join(HERE, '說明.html')


def img_b64(path, width=1200):
    im = Image.open(path).convert('RGB')
    if im.width > width:
        h = int(im.height * width / im.width)
        im = im.resize((width, h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=86, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


HTML = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EdgeRunners 使用說明</title>
<style>
  :root {
    --text: #1f2733; --muted: #6a7488; --line: #e2e6ec;
    --accent: #2f6fed; --bg: #f6f8fb; --card: #fff;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 0 20px 80px;
    background: var(--bg); color: var(--text);
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
    font-size: 15px; line-height: 1.85;
  }
  .wrap { max-width: 940px; margin: 0 auto; }
  header { padding: 48px 0 28px; border-bottom: 1px solid var(--line); }
  h1 { margin: 0 0 6px; font-size: 30px; letter-spacing: .01em; }
  .sub { margin: 0; color: var(--muted); font-size: 15px; }
  .badge {
    display: inline-block; margin-top: 12px; padding: 3px 10px;
    background: #e9f0fe; color: var(--accent); border-radius: 999px;
    font-size: 12.5px; font-weight: 600;
  }
  nav {
    margin: 26px 0 10px; padding: 16px 20px;
    background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  }
  nav ol { margin: 0; padding-left: 20px; columns: 2; column-gap: 32px; }
  nav a { color: var(--accent); text-decoration: none; }
  nav a:hover { text-decoration: underline; }
  h2 {
    margin: 48px 0 14px; font-size: 21px;
    padding-left: 12px; border-left: 4px solid var(--accent);
  }
  h3 { margin: 26px 0 8px; font-size: 16.5px; }
  p { margin: 10px 0; }
  ul, ol { padding-left: 22px; }
  li { margin: 6px 0; }
  code {
    background: #eef1f6; padding: 1px 6px; border-radius: 5px;
    font-family: Consolas, monospace; font-size: 13.5px;
  }
  table {
    width: 100%; border-collapse: collapse; margin: 14px 0 18px;
    background: var(--card); border: 1px solid var(--line); border-radius: 10px;
    overflow: hidden; font-size: 14px;
  }
  th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--line); }
  th { background: #f0f3f8; font-weight: 600; font-size: 13px; color: var(--muted); }
  tr:last-child td { border-bottom: none; }
  td:first-child { white-space: nowrap; font-weight: 600; }
  figure { margin: 20px 0 28px; }
  figure img {
    width: 100%; border: 1px solid var(--line); border-radius: 10px;
    box-shadow: 0 6px 24px rgba(20, 30, 50, .10); display: block;
  }
  figcaption { margin-top: 8px; color: var(--muted); font-size: 13px; text-align: center; }
  .note {
    margin: 18px 0; padding: 14px 18px; border-radius: 10px;
    background: #fff8e8; border: 1px solid #f2e2bd; font-size: 14px;
  }
  .note b { color: #a5741a; }
  .warn {
    margin: 18px 0; padding: 14px 18px; border-radius: 10px;
    background: #fdeeee; border: 1px solid #f5d5d5; font-size: 14px;
  }
  .warn b { color: #b93a3a; }
  .ok {
    margin: 18px 0; padding: 14px 18px; border-radius: 10px;
    background: #eefaf3; border: 1px solid #cdeedb; font-size: 14px;
  }
  .faq {
    background: var(--card); border: 1px solid var(--line); border-radius: 12px;
    padding: 4px 20px; margin: 16px 0;
  }
  .faq h3 { margin: 18px 0 6px; color: var(--accent); }
  .faq h3:first-child { margin-top: 16px; }
  .faq p { margin: 0 0 16px; }
  footer {
    margin-top: 60px; padding-top: 22px; border-top: 1px solid var(--line);
    color: var(--muted); font-size: 13px;
  }
  @media print {
    body { background: #fff; font-size: 12pt; }
    nav { display: none; }
    h2 { page-break-after: avoid; }
    figure { page-break-inside: avoid; }
  }
</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>EdgeRunners</h1>
  <p class="sub">iPhone 定位修改與運動軌跡模擬工具</p>
  <span class="badge">v0.4.4</span>
</header>

<nav>
  <ol>
    <li><a href="#start">第一次使用（6 步）</a></li>
    <li><a href="#ui">介面導覽</a></li>
    <li><a href="#gesture">手勢操作</a></li>
    <li><a href="#locate">修改定位</a></li>
    <li><a href="#sim">運動模擬</a></li>
    <li><a href="#faq">常見問題</a></li>
    <li><a href="#files">檔案位置與備份</a></li>
  </ol>
</nav>

<h2 id="start">第一次使用（6 步）</h2>

<div class="warn">
  <b>兩個先決條件，缺一不可。</b><br><br>
  <b>① Apple 手機通訊服務（usbmuxd）</b><br>
  Windows 靠它才認得出 iPhone，通常是安裝 Apple 軟體時一併裝好的 ——
  iTunes 官網版、Microsoft Store 的「Apple Devices」、或愛思助手等第三方工具都會裝。
  電腦上完全沒有 Apple 軟體的話，請裝 <b>iTunes 官網版</b>（apple.com/itunes/download/win64），裝完<b>務必重新開機</b>。<br>
  <span style="color:var(--muted)">※ 程式啟動時會做實際連線測試，並依實際狀況給對應建議。</span><br><br>
  <b>② 能傳資料的 USB 線</b><br>
  只能充電的線會出現「<b>手機有在充電，但電腦完全看不到裝置</b>」，這是最容易被誤判成程式問題的坑。<br>
  請用 <b>C to C</b> 線，或標明支援資料傳輸的線；便宜的 A to C 線常常只接了電源線。
</div>

<ol>
  <li><b>安裝 iTunes</b> 並重新開機。<br>
      <span style="color:var(--muted)">裝好後可開「工作管理員 → 服務」確認 <code>Apple Mobile Device Service</code> 狀態是「執行中」。</span></li>
  <li><b>插上 iPhone</b>，用能傳資料的 USB 線。手機解鎖後會問「要信任這部電腦嗎」，點<b>信任</b>並輸入密碼。</li>
  <li><b>開啟開發者模式</b>：設定 → 隱私權與安全性 → 滑到最下面 → 開發者模式 → 打開 → 手機重開機 → 開機後再確認一次。<br>
      <span style="color:var(--muted)">※ 這個選項要手機<b>接過電腦並按過信任</b>之後才會出現。</span><br>
      <span style="color:var(--muted)">※ iOS 16 以後這個選項<b>預設是隱藏的</b>。如果滑到底還找不到，
      回到程式主畫面，狀態列下方會有一行「<b>找不到「開發者模式」？點此讓它出現</b>」——
      按下去，程式會向手機送出開發請求，選項就會出現在設定裡。</span></li>
  <li><b>關掉自動鎖定</b>：設定 → 顯示與亮度 → 自動鎖定 → <b>永不</b>。<br>
      <span style="color:var(--muted)">※ 螢幕一暗，模擬就會中斷（會出現 DeviceLocked）。</span></li>
  <li><b>打開 EdgeRunners</b>。右上角狀態列應該顯示 <code>已連接 iPhone · iOS xx · DDI 已掛載</code>（綠色點）。</li>
  <li><b>第一次按「注入」或「開始模擬」時</b>，程式會自動掛載開發者映像檔，<b>需要 30～90 秒</b>，請耐心等，不要關程式。</li>
</ol>

<div class="note">
  <b>狀態列三種顏色：</b>🟢 綠＝已連接且映像檔已掛載　🟡 黃＝已連接但映像檔未掛載（按注入時會自動掛）　🔴 紅＝沒抓到手機
</div>

<div class="note">
  <b>程式一開就跳紅字？</b> 代表連不上手機通訊服務（usbmuxd）或缺少必要檔案。
  紅字會依實際狀況給對應建議（沒裝 Apple 軟體 / 裝了但服務沒起來 / 服務卡住 / 線材問題），
  照著做即可；也可以按紅字下方的「<b>複製診斷資訊</b>」把環境資料貼給開發者。
</div>

<h2 id="ui">介面導覽</h2>

<figure>
  <img src="__LOCATE__" alt="修改定位頁面">
  <figcaption>「修改定位」頁：左邊地圖，右邊操作面板</figcaption>
</figure>

<p>左側是<b>高德地圖</b>，右上角可切換<b>修改定位</b>與<b>運動模擬</b>兩個頁籤。左上角兩顆按鈕：</p>

<table>
  <tr><th>按鈕</th><th>作用</th></tr>
  <tr><td>清圖</td><td>清掉地圖上畫的路線、預覽動畫與選點</td></tr>
  <tr><td>復位</td><td>有路線時縮放到路線範圍；沒有路線時回到開啟程式時的視野</td></tr>
</table>

<figure>
  <img src="__SIM__" alt="運動模擬頁面">
  <figcaption>「運動模擬」頁：畫好路線後會顯示長度與預估時間</figcaption>
</figure>

<h2 id="gesture">手勢操作</h2>

<table>
  <tr><th>操作</th><th>效果</th></tr>
  <tr><td>左鍵單擊</td><td>在地圖上選一個點（右側會顯示高德座標與 GPS 座標）</td></tr>
  <tr><td>左鍵按住拖曳</td><td>移動地圖</td></tr>
  <tr><td>右鍵按住拖曳</td><td>畫路線（放開右鍵結束）</td></tr>
  <tr><td>滾輪</td><td>縮放地圖</td></tr>
  <tr><td>按住常見定位項目約 0.3 秒</td><td>拖曳排序（順序會自動存檔）</td></tr>
</table>

<div class="note">
  <b>為什麼有兩種座標？</b> 高德地圖用的是中國加密的「火星座標（GCJ-02）」，iPhone 用的是「GPS 座標（WGS-84）」，兩者在中國大陸境內相差 300～700 公尺。程式已自動換算，你只要認右邊那組 <b>GPS</b> 數字即可。
</div>

<h2 id="locate">修改定位</h2>

<ol>
  <li>在地圖上<b>單擊</b>想去的位​置（或用「自選定位」貼上座標，記得選 <code>GPS</code> 或 <code>高德</code>）。</li>
  <li>按<b>注入該座標</b>。約 5 秒後（首次要掛映像檔，約 1 分鐘）按鈕會變成「已注入 ✓」。</li>
  <li>打開手機的「地圖」App，藍點應該已經跳到該位置。</li>
  <li>要還原：按<b>恢復真實定位</b>，或直接關掉程式（程式會自動收尾）。</li>
</ol>

<p>也可以直接點右側<b>常見定位</b>清單裡的地點，地圖會飛過去並選中該點。</p>

<h3>加入自己的常用地點</h3>
<p>選好一個點後，按<b>★ 把當前選點加入常見定位</b>，輸入名稱即可（清單只顯示名稱，保持乾淨）。<br>
   也可以用記事本編輯 <code>common_location.txt</code>，程式啟動時會自動讀取。</p>

<h2 id="sim">運動模擬</h2>

<h3>操作流程</h3>
<ol>
  <li>切到<b>運動模擬</b>頁籤。</li>
  <li><b>右鍵按住拖曳</b>畫出要跑的路線，放開右鍵結束。</li>
  <li>設定<b>速度</b>、<b>抖動</b>、是否<b>循環</b>與<b>次數</b>。</li>
  <li>看「路線統計」確認長度與預估時間。</li>
  <li>（建議）按<b>預覽</b>先看動畫確認路線形狀 —— <b>預覽不會改變手機定位</b>。</li>
  <li>按<b>開始模擬</b>。若這是剛畫的路線，會問要不要存進「已有路線」。</li>
  <li>進度條會顯示已跑時間與剩餘時間；按<b>中止模擬</b>可隨時停止。</li>
  <li>結束後會問<b>是否恢復真實定位</b>。</li>
</ol>

<h3>參數說明</h3>
<table>
  <tr><th>參數</th><th>說明</th></tr>
  <tr><td>速度</td><td>單位公尺/秒。下方會即時換算成 km/h 與配速。<br>
    散步 1.2　走路 1.4　慢跑 2.8　跑步 3.3　快跑 4.5　腳踏車 5.5　開車 11</td></tr>
  <tr><td>抖動</td><td>0～3 公尺。0 是完全平滑的直線，越大越像真人（左右搖晃、速度忽快忽慢）。建議 1.0～1.5。</td></tr>
  <tr><td>循環</td><td>勾選後會用直線把終點接回起點，形成閉環，並重複跑「次數」圈。</td></tr>
  <tr><td>次數</td><td>只在勾選循環時可用。</td></tr>
</table>

<div class="note">
  <b>預覽動畫：</b>路線 15 公里以內用 10 秒跑完，超過 15 公里用 15 秒。預覽純粹是畫面動畫，<b>不會送出任何指令給手機</b>。
</div>

<h2 id="faq">常見問題</h2>

<div class="faq">

<h3>Q0. 一開始就抓不到手機，狀態列一直紅燈</h3>
<p>電腦要能跟 iPhone 通訊，靠的是 Apple 的 <b>usbmuxd</b>（Windows 上就是
   「Apple Mobile Device Service」這個服務）。<b>這個服務不是只有 iTunes 會裝</b> ——
   Microsoft Store 的「Apple Devices」、愛思助手之類的第三方工具、甚至筆電預裝的舊版 Apple 軟體，
   都可能把它裝好。所以「沒裝 iTunes」不等於「不能連」。</p>

<p>程式用的是<b>實際連線測試</b>：先試著跟 usbmuxd 通話，通了就不警告。
   所以如果有人沒裝 iTunes 卻能正常使用，程式也不會跳紅字。<br>
   <b>看到紅字，代表真的連不上。</b>依紅字寫的內容處理即可（整理如下）：</p>

<table>
  <tr><th>紅字說</th><th>做法</th></tr>
  <tr><td>找不到 usbmuxd，且電腦沒有 Apple 軟體</td>
      <td>裝 <b>iTunes 官網版</b>（apple.com/itunes/download/win64）或 Microsoft Store 的「Apple Devices」，裝完<b>重新開機</b></td></tr>
  <tr><td>找不到服務，但電腦「確實裝了 Apple 軟體」</td>
      <td>iTunes 安裝不完整（服務元件沒註冊成功，舊電腦常見）：<br>
          1. 控制台 → 程式和功能 → iTunes → <b>變更 → 修復</b><br>
          2. 不行就完整移除，改裝<b>官網版</b>（不要用 Microsoft Store 版）<br>
          3. 重開機</td></tr>
  <tr><td>服務存在但沒有在執行</td>
      <td>Win+R → 輸入 <code>services.msc</code> → 「Apple Mobile Device Service」→ 右鍵啟動；或直接重開機</td></tr>
  <tr><td>服務正在執行，但仍連不上</td>
      <td>服務卡住了。重開機，或到 services.msc 對它按「重新啟動」</td></tr>
</table>

<p>以上都試過仍不行，再檢查下面這一項 —— <b>這是最常被誤判成程式問題的坑</b>。</p>

<h3>Q0-2. 手機在充電，但電腦完全看不到裝置</h3>
<p><b>九成是線材問題。</b>USB 線裡面有四條關鍵線：VBUS（+5V）、GND、D+、D-。
便宜的「充電線」常常<b>只接了電源兩條</b>，D+/D- 根本沒接 ——
手機看到 5V 就開始充電，但沒辦法被電腦辨識。</p>

<table>
  <tr><th>線材</th><th>狀況</th></tr>
  <tr><td><b>C to C</b>（USB-C 對 USB-C）</td><td>✅ 幾乎一定含資料線，最保險</td></tr>
  <tr><td><b>A to C</b>，有品牌、標明資料傳輸</td><td>✅ 可用</td></tr>
  <tr><td><b>A to C</b>，便宜的充電線</td><td>❌ 常常只有電源，會出現「能充電、看不到裝置」</td></tr>
</table>

<p><b>30 秒自我驗證：</b>拿同一條線去接一支 Android 手機或 USB-C 隨身碟。<br>
   如果電腦照樣看不到 → <b>就是線的問題，換線結案</b>，跟軟體無關。</p>

<p>另外也可能不是線，而是<b>那個 USB 孔只供電</b>：機殼前置面板、螢幕上的 USB、廉價 HUB 常見。
   遇到就先換到主機板後方的 USB 孔試試。</p>

<figure>
  <img src="__WARN__" alt="連不上手機通訊服務的警告">
  <figcaption>連不上 usbmuxd 時，程式一啟動就會在右上角跳紅字並附處理建議</figcaption>
</figure>

<h3>Q1. 地圖一片空白或一直轉圈</h3>
<p>先看有沒有連網路（地圖底圖必須連網）。如果網路正常，多半是<b>高德 Key 失效</b>或<b>沒填安全密鑰</b>。<br>
   解法：按右上角 <b>⚙</b> 貼上新的 Key 與 jscode（見 Q3）。</p>

<h3>Q2. 地圖報錯 INVALID_USER_KEY 或 INVALID_USER_SCODE</h3>
<p><b>INVALID_USER_KEY</b>＝Key 不存在或被刪除；<b>INVALID_USER_SCODE</b>＝安全密鑰（jscode）不對。
兩個都要重新申請，然後按 ⚙ 更新。</p>

<h3>Q3. 怎麼換 Key</h3>
<p>1. 到 <b>console.amap.com</b> 註冊/登入 → 應用管理 → 建立新應用 → 添加 Key → 服務平台選「<b>Web端 (JSAPI)</b>」。<br>
   2. 拿到 <b>Key</b> 與 <b>安全密鑰 jscode</b> 兩組字串。<br>
   3. 回到程式，按右上角 <b>⚙</b>，貼上後按「儲存並重載」。</p>

<figure>
  <img src="__SET__" alt="設定視窗">
  <figcaption>按右上角 ⚙ 打開設定，貼上新 Key 與 jscode</figcaption>
</figure>

<h3>Q4. 狀態列一直顯示「未連接 iPhone」</h3>
<p>依序檢查：線是不是只能充電的線（換一條）→ 換一個 USB 孔 → 手機是否解鎖 → 有沒有按「信任」→ 電腦的 Apple Mobile Device 服務是否在跑（裝 iTunes 會一併裝好）。</p>

<h3>Q5. 按了注入，等很久都沒反應</h3>
<p>第一次使用時程式要先<b>掛載開發者映像檔</b>，需要 30～90 秒，按鈕會顯示「準備中…」。之後每次只要 5 秒左右。</p>

<h3>Q6. 出現「手機鎖住了」或 DeviceLocked</h3>
<p>解鎖手機並讓螢幕保持亮著，再按一次。<b>務必把「自動鎖定」設成「永不」</b>，否則模擬跑到一半會中斷。</p>

<h3>Q7. 提示沒有開啟開發者模式</h3>
<p>設定 → 隱私權與安全性 → 開發者模式 → 打開 → 重開機 → 開機後確認。這個選項在手機「接過電腦並按過信任」之後才會出現。</p>

<h3>Q8. 模擬跑一半就停了</h3>
<p>三個常見原因：手機螢幕鎖了、USB 線鬆了、電腦進入休眠。檢查這三點後重新開始即可。程式會保留你剛才的路線與參數。</p>

<h3>Q9. 沒有網路可以用嗎？</h3>
<p><b>模擬本身不需要網路</b>（走 USB），但<b>地圖底圖需要連網</b>。<br>
   斷網時地圖會空白，但右側面板仍可操作，也能直接選「已有路線」按開始模擬。</p>

<h3>Q10. 模擬結束後手機定位沒恢復</h3>
<p>按<b>恢復真實定位</b>。若沒反應，拔掉 USB 線或重開機也會恢復。</p>

<h3>Q11. 地圖上某些地方（例如國外）沒有細節</h3>
<p>高德地圖在中國大陸以外地區的底圖非常簡略，這是高德的覆蓋範圍限制，不是程式問題。定位本身仍然可以正常注入。</p>

<h3>Q12. 常見定位的順序可以調整嗎？</h3>
<p>可以，<b>按住該項目約 0.3 秒</b>後上下拖曳即可，放開就自動存檔。</p>

</div>

<h2 id="files">檔案位置與備份</h2>

<p>所有資料都在程式同一個資料夾裡：</p>

<table>
  <tr><th>檔案</th><th>內容</th></tr>
  <tr><td>EdgeRunners.exe</td><td>主程式</td></tr>
  <tr><td>_internal\\</td><td>執行時需要的檔案，<b>不能刪</b></td></tr>
  <tr><td>config.json</td><td>高德 Key、視窗大小位置、上次地圖視野、常見定位清單</td></tr>
  <tr><td>routes.json</td><td>已保存的路線</td></tr>
  <tr><td>說明.html</td><td>本文件</td></tr>
</table>

<p><b>備份</b>：複製 <code>config.json</code> 與 <code>routes.json</code> 即可，換電腦時放回同一資料夾就還原了。</p>
<p><b>重設</b>：刪掉這兩個檔案，程式下次啟動會用預設值（Key 也會清空，記得重新填）。</p>

<footer>
  本軟體由浙江大學學生 MueroSimy 開發，完全免費開源，僅供學習交流，嚴禁商業與違法用途。<br>
  地圖資料 © 高德地圖（AutoNavi）。使用本工具造成的任何後果由使用者自行承擔。
</footer>

</div>
</body>
</html>
"""


def main():
    parts = HTML
    if os.path.exists(SHOT_LOCATE):
        parts = parts.replace('__LOCATE__', img_b64(SHOT_LOCATE))
    else:
        print('缺少截圖：', SHOT_LOCATE)
    if os.path.exists(SHOT_SIM):
        parts = parts.replace('__SIM__', img_b64(SHOT_SIM))
    else:
        print('缺少截圖：', SHOT_SIM)
    if os.path.exists(SHOT_SET):
        parts = parts.replace('__SET__', img_b64(SHOT_SET))
    else:
        print('缺少截圖：', SHOT_SET)
    if os.path.exists(SHOT_WARN):
        parts = parts.replace('__WARN__', img_b64(SHOT_WARN))
    else:
        print('缺少截圖：', SHOT_WARN)

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(parts)
    print('已產生', OUT, '%.0f KB' % (os.path.getsize(OUT) / 1024))


if __name__ == '__main__':
    main()







