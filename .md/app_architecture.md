# 前端系統架構設計書 (app_architecture.md)

本文件專注於定義 AI 釣魚郵件偵測系統前端組件 (`app.py`) 的內部架構、職責範圍與資料流。做為串接 `decoder.py` 與 `inference.py` 的橋樑，前端應用扮演著 Controller 與 UI Rendering 的雙重角色。

## 1. 模組定位與職責 (Role & Responsibilities)
`app.py` 是整個專案唯一面向終端使用者的介面，其核心職責包含：
1. **輸入與防護 (Input & Guardrails)**：負責接收使用者提交的原始資料（包含單筆字串與批量 `.txt` 檔案），並執行第一線的 DoS 防護（例如字數上限 5000 字元攔截、空值檢驗）。
2. **流程中控 (Pipeline Orchestration)**：協調與呼叫下層的資料清洗模組 (`decoder.py`) 與推論引擎 (`inference.py`)。
3. **錯誤攔截與透明化 (Error Handling & Transparency)**：統一捕捉後端拋出的任何 `Exception`，並將其轉換為人類可讀的錯誤訊息（不吃掉錯誤、不瞎猜）。
4. **結果渲染 (UI Rendering)**：在畫面上清楚、並列地呈現「原始輸入」、「解碼對比日誌」以及「最終威脅判定與機率」。

---

## 2. 系統元件劃分 (Component Breakdown)

為了達到高內聚、低耦合，`app.py` 內部依職責劃分為以下幾個核心區塊（Functions/Methods）：

### A. 依賴載入與初始化層 (`load_modules`)
* **目的**：安全地動態引入 `decoder.py` 與 `inference.py`。
* **行為**：若載入過程發生 `ModuleNotFoundError`（例如伺服器未安裝 `transformers`），或模型權重檔損壞，此區塊會以 `try-except` 包覆，並透過 Streamlit 拋出具體的錯誤追蹤 (Traceback)，隨後優雅地中斷應用 (`st.stop()`)。

### B. UI 控制與佈局層 (`main`)
* **目的**：定義網頁的標題、排版結構與分頁邏輯。
* **佈局設計**：使用 Streamlit Tabs 功能將介面分為兩大區塊：
  * **Tab 1 - 單筆檢測 (Single Text Analysis)**：提供 `st.text_area` 處理臨時性的文字審查。
  * **Tab 2 - 批量分析 (Batch File Analysis)**：提供 `st.file_uploader` 接收包含了多筆驗測樣本的文本檔案 (`.txt`)。

### C. 批量與解析邏輯層 (`process_batch_file`)
* **目的**：拆解使用者上傳的文字檔，將無結構的文本轉換為結構化清單。
* **行為**：讀取位元組資料並以 `utf-8` 解碼，透過正規表示式（Regex）切分出獨立的 Payload。例如：針對 `test_payloads.txt` 中帶有 `1. [...]` 的標題結構進行智慧切割。
* **迭代處理**：將拆分出來的 List，利用迴圈依序餵給 `decoder` 與 `inference`，並整理成清單字典 (`List[Dict]`)。

### D. 渲染與報告層 (`render_single_result`, `render_batch_report`)
* **目的**：將 JSON 格式的推論結果轉譯為直覺的視覺化元件。
* **單筆渲染 (`render_single_result`)**：
  * 使用 Columns 將判定結果與機率並排展示（綠色代表 Safe、紅色警告代表 Phishing）。
  * 以 Markdown 的 Code Block 並列顯示「清洗前」與「清洗後」的文本，實踐「零黑箱」原則。
* **批量渲染 (`render_batch_report`)**：
  * 引入 `pandas.DataFrame`。
  * 將迴圈處理完的 `List[Dict]` 轉換為易於閱讀且可排序的結構化表格。欄位包含 `ID`, `Prediction`, `Probability`, `Cleaned Text Snippet`。
  * 支援直接在畫面上查閱所有 Payload 的表現結果。

---

## 3. 核心資料流向 (Data Flow)

### 3.1 單筆檢測資料流 (Single Payload Flow)
1. 使用者於 `Text Area` 輸入字串 `raw_payload`，點擊 [分析]。
2. 防護層：檢查 `len(raw_payload) <= 5000`且不為空值。
3. 管線層：`cleaned_text = decoder.process_text(raw_payload)`。
4. 推論層：`prediction_dict = inference.predict(cleaned_text)`。
5. 渲染層：傳遞 `raw_payload`, `cleaned_text`, `prediction_dict` 至 `render_single_result()` 在視窗下半部繪製對比面板與分數。

### 3.2 批量檔案檢測資料流 (Batch File Flow)
1. 使用者於 `File Uploader` 上傳 `.txt`。
2. 點擊 [開始批量分析]。
3. 檔案流：以字串讀取內容 `file_content`。
4. 解析層：`payloads_list = extract_payloads(file_content)`，取得 10 筆或數十筆字串。
5. 迭代層：針對 `payloads_list` 中的每一筆執行迴圈，各自經過 `decoder` 與 `inference` 處理，若某一筆發生例外，該筆的判定記為 `"Error"`，繼續下一筆。
6. 匯總層：將蒐集到的結果陣列交由 `pd.DataFrame()`，並呼叫 `st.dataframe()` 呈現在 UI 表格中。

---

## 4. 異常處理規範 (Exception Handling Standards)
在 `app.py` 中，所有的外部呼叫（載入模組、讀取上傳檔案、經過正則替換、呼叫模型）都必須處於 `try-except Exception as e` 區塊之內。捕捉到的例外使用 `traceback.format_exc()` 取出完整錯誤棧，並透過 `st.error()` 顯示在出錯的位置（單筆則顯示在主版面，批量則顯示於 DataFrame 對應行的備註內），**絕對禁止**系統以閃退或全白畫面的形式陷入停頓。
