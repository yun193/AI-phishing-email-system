# 釣魚郵件解碼與清洗模組 (Decoder Module) 架構設計書

## 1. 模組定位與目標
本模組主要負責將原始的電子郵件文本 (Raw Email Text) 進行前置處理。針對釣魚信件中常見的混淆技術（Base64、URL Encoding）進行自動還原，並清洗掉會干擾機器學習模型判斷的雜訊（HTML 標籤、多餘空白），最終輸出乾淨的明文特徵供後續模型訓練使用。

---

## 2. 核心處理流程 (Data Flow)
當外部程式傳入一筆郵件字串時，系統將依序執行以下管線 (Pipeline)：

1. **輸入驗證：** 確認輸入為字串格式，過濾空值 (Null/NaN)。
2. **URL 解析 (Task 2)：** 掃描並還原 `%20`, `%3D` 等 URL 編碼字元。
3. **Base64 解碼 (Task 2)：** 透過正規表示式定位潛在的 Base64 區塊，嘗試解碼並替換為可讀明文。
4. **HTML 標籤清除 (Task 3)：** 移除 `<script>`, `<a>`, `<p>` 等網頁標籤，將其替換為空白。
5. **空白字元正規化 (Task 3)：** 將連續的空格、換行符號 (`\n`)、定位符號 (`\t`) 壓縮為單一空格，並去除首尾空白。
6. **輸出結果：** 回傳處理完畢的乾淨字串。

---

## 3. 類別與接口設計 (Class & Interface Design)
所有邏輯皆封裝於 `PhishingDecoder` 類別中。對外僅暴露單一主接口，降低模組耦合度；內部邏輯拆分為獨立方法，便於後續擴充與單元測試。

| 方法名稱 (Method) | 訪問級別 (Visibility) | 參數 (Input) | 回傳值 (Output) | 功能說明 |
| :--- | :--- | :--- | :--- | :--- |
| `process_text` | **Public (公開)** | `text` (str) | `str` | **主接口**。依序執行所有解碼與清洗流程。 |
| `_decode_url` | Private (內部) | `text` (str) | `str` | 尋找並解碼 URL Encoding 字串。 |
| `_decode_base64` | Private (內部) | `text` (str) | `str` | 透過 Regex 尋找 Base64 特徵並嘗試解碼。 |
| `_clean_html` | Private (內部) | `text` (str) | `str` | 將所有 HTML 標籤替換為空白。 |
| `_normalize_spaces`| Private (內部) | `text` (str) | `str` | 壓縮多餘空白、換行，並執行 `strip()`。 |

---

## 4. 詳細接口定義 (API Specifications)

### 主接口：`process_text(self, text: str) -> str`

* **參數：**
  * `text` (`str`): 原始的郵件內容字串。若傳入非字串型態 (如 `None` 或 Pandas 的 `NaN`)，系統會自動處理。
* **回傳：**
  * `str`: 經過解碼與清洗後的明文字串。若輸入無效則回傳空字串 `""`。

**使用範例：**
```python
from decoder import PhishingDecoder

decoder = PhishingDecoder()
raw_email = "Click <b>here</b>: %68%74%74%70%3A%2F%2F%62%61%64%2E%63%6F%6D"
clean_email = decoder.process_text(raw_email) 

print(clean_email)
# 預期輸出: "Click here: [http://bad.com](http://bad.com)"
```

---

## 5. 例外與邊界條件處理 (Error & Edge Case Handling)
為確保資料處理過程的穩定性，本模組內建以下防呆與容錯機制：

* **Base64 假陽性 (False Positives)：** 若擷取到的字串符合 Base64 格式，但無法成功解碼為 UTF-8 字串（例如剛好是一串無意義的英數字），模組會攔截例外錯誤，並保留原始字串不作替換。
* **非字串輸入 (Non-string Inputs)：** 讀取資料集時常遇到缺失值，若傳入 `process_text` 的值並非 `str` 類型，將直接回傳 `""`，避免程式崩潰。
* **HTML 標籤沾黏問題：** 在清除 HTML 標籤時，採取「替換為單一空白」而非直接刪除的策略，防止 `<p>Hello</p>World` 變成 `HelloWorld` 導致單字語意遺失。