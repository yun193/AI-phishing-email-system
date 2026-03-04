# 釣魚郵件解碼與清洗模組 (Decoder Module) 架構設計書

本文件定義 `decoder.py`模組的內部架構、介面規格及執行流程。該模組負責接收原始郵件文本，並透過遞迴解碼與特徵替換機制，輸出乾淨明文供後端機器學習模型（如NLP）進一步訓練使用。

------------------------------------------------------------------------

## 1. 模組職責範圍 (Scope of Responsibilities)

-   **自動化解碼 (Recursive Decoding)：**\
    自動偵測並還原 URL Encoding（如 `%20`）與 Base64 編碼，且具備
    **遞迴深度控制**，確保多層級混淆的文本能被有效解析，同時防範惡意死迴圈攻擊。

-   **基礎內容清洗 (Basic Cleansing)：**\
    移除腳本（`<script>...</script>`）、網頁標籤（`<...>`）與多餘的不可見字元（換行、連續空白）。

-   **惡意特徵提取 (Feature Tokenization)：**\
    將釣魚信件特有的高風險指標（如直接使用的 IP
    地址、異常長度的網域）抽象化為專屬 Token（如 `[SUSPICIOUS_IP]`,
    `[EVIL_URL]`），以強化模型的特徵識別能力。

-   **處理日誌追蹤 (Decoding Logging)：**\
    記錄解碼深度的每一次變更與特徵替換行為，協助後續資安分析與除錯。

------------------------------------------------------------------------

## 2. 系統架構流程 (System Architecture Pipeline)

當一筆 Raw Email Text 送入本系統時，將會依序經過以下管線：

1.  **Safety Check：** 確認輸入格式，過濾無效資料。
2.  **Script Removal：** 優先刪除帶有執行邏輯的 `<script>` 及其內容。
3.  **Recursive Decoding Engine：**
    -   偵測並替換 URL Encoding。
    -   偵測並解碼 Base64。
    -   若字串在本輪發生改變，且未達最大深度限制（預設 10
        層），則進入下一輪遞迴解碼。
4.  **HTML Cleansing：** 移除剩餘的基礎 HTML 標籤。
5.  **Tokenization：** 透過正規表示式匹配，將 IP 替換為
    `[SUSPICIOUS_IP]`，將過長網址替換為 `[EVIL_URL]`。
6.  **Normalization：** 壓縮多餘空白字元與換行。
7.  **Output：** 回傳處理完成的 Cleaned Text 與 Decoding Log。

------------------------------------------------------------------------

## 3. 類別與方法定義 (Class & Method Definitions)

模組核心邏輯皆封裝於 `PhishingDecoder` 類別內。

  ---------------------------------------------------------------------------------------------------------
  方法名稱 (Method)      訪問級別   參數 (Input)  回傳型態 (Output)    功能說明
  ---------------------- ---------- ------------- -------------------- ------------------------------------
  `process_text`         Public     `text` (str)  `tuple[str, list]`   主 API。執行完整前處理管線，回傳
                                                                       (Cleaned Text, Log)。

  `_decode_url`          Private    `text` (str)  `tuple[str, bool]`   執行單次 URL
                                                                       解碼。回傳布林值表示是否發生替換。

  `_decode_base64`       Private    `text` (str)  `tuple[str, bool]`   執行單次 Base64
                                                                       解碼。回傳布林值表示是否發生替換。

  `_tokenize_features`   Private    `text` (str)  `tuple[str, list]`   將特定的 IP 與超長網址替換為
                                                                       Token，並記錄至 Log。

  `_normalize_spaces`    Private    `text` (str)  `str`                清除多餘的空白、換行或定位字元。
  ---------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 4. 外部介面呼叫規格 (API Interface)

### 函數：`process_text(text: str) -> tuple[str, list[str]]`

這是外部系統（例如 Pandas 資料處理腳本）與此模組互動的唯一入口。

### 輸入參數 (Parameters)

-   `text` (`str`)：待處理的原始字串。\
    若傳入非字串資料（例如 `None` 或 `NaN`），系統會回傳
    `("", ["Error log"])`。

### 回傳值 (Returns)

1.  `Cleaned Text`
    (`str`)：經過所有清理、解碼與特徵替換程序後的乾淨明文。
2.  `Decoding Log`
    (`list[str]`)：記錄此次處理過程的日誌清單，包含解碼深度、特徵替換紀錄等。

### 使用範例 (Code Example)

``` python
from decoder import PhishingDecoder

decoder = PhishingDecoder()
raw_payload = "Click: %68%74%74%70%3A%2F%2F%31%39%32%2E%31%36%38%2E%31%2E%31"

clean_text, process_log = decoder.process_text(raw_payload)

print(f"Clean Text: {clean_text}")
# 預期輸出:
# Clean Text: Click: [SUSPICIOUS_IP]
```

------------------------------------------------------------------------

## 5. 異常處理與邊界條件 (Error Handling & Edge Cases)

-   **防禦性無限迴圈 (Infinite Loop Protection)：**\
    針對 Recursive Decoding 設定了 `max_depth`
    限制。若遇惡意攻擊者建構會互相解碼的無限循環字串，系統會在達到深度限制時強制中斷迴圈，保留當下結果並於
    Log 記錄警告。

-   **Base64 假陽性防護 (Base64 False Positives)：**\
    針對符合 Base64 格式但實際為一般文本的情況（例如長度超過 12
    的英數單字），若嘗試解碼發生錯誤，或解碼後的字元為無法閱讀的亂碼（`isprintable() == False`），則判定為誤判，保留原始字串不作替換。