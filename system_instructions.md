# 🛡️ AI 釣魚郵件偵測系統 - 系統架構文件 (System Architecture)

## 1. 系統概述 (System Overview)
本系統旨在建立一個能偵測並還原惡意混淆編碼的 AI 釣魚郵件識別系統。核心設計理念為「**防禦優先 (Defense-in-Depth)**」，在將資料送入 AI 語言模型進行分析前，必須先經過嚴格的清洗與強制解碼程序，以應對攻擊者常用的混淆與編碼繞過手法。

本文件作為 AI Agent 或開發者進行後續開發、維護與擴充的權威指導方針。

---

## 2. 核心 API 介面定義與調用範例 (API Interfaces & Examples)

為了讓前端、AI 模型與資料處理模組完全解耦並便於互相調用，系統內部定義了以下核心 API 介面，供後續 AI Agent 實作與串接使用。

### 2.1 資料前處理與解碼模組 (`decoder.py`)

- **功能描述**：負責過濾不相關字元、實作惡意特徵提取，並對隱藏的編碼字串進行深度遞迴解碼。
- **介面名稱**：`process_text(payload: str) -> Tuple[str, List[str]]`
- **參數**：
  - `payload` (String)：使用者輸入的原始釣魚郵件或可疑文本。
- **回傳值**：
  1. `cleaned_text` (String)：清洗完畢且已把可疑 URL/IP 替換為特徵 Token (`[EVIL_URL]`) 的標準化明文。
  2. `decode_logs` (List[String])：記錄每一步解碼動作的日誌清單，提供給前端做 UI 可視化與透明度展示。

**✅ 調用範例 (Python)**：
```python
from decoder import process_text

# 包含 HTML 以及 Base64 編碼惡意網址的原始 Payload
raw_email = "Click here to verify: <a href='http://example.com'>http://base64-aHR0cDovL2V2aWwuY29t</a>"

cleaned_text, logs = process_text(raw_email)

print("Cleaned Text:")
print(cleaned_text)
# Output: "Click here to verify: [EVIL_URL]"

print("\nLogs:")
for log in logs:
    print(log)
# Output: 
# [HTML_Removed] Removed tags <a>.
# [Base64_Decode] Decoded 'aHR0cDovL2V2aWwuY29t' to 'http://evil.com'.
# [Tokenized] Replaced 'http://evil.com' with '[EVIL_URL]'.
```

### 2.2 AI 推論模組 (`inference.py`)

- **功能描述**：接收標準化明文，並透過微調後的 Transformer 模型進行語意分析與威脅評估。
- **介面名稱**：`predict(cleaned_text: str) -> Dict[str, Union[str, float]]`
- **參數**：
  - `cleaned_text` (String)：已經過 `decoder.py` 清洗處理後的標準化明文（可能帶有 Token）。
- **回傳值**：
  - 回傳 Dict 格式，包含分類結果標籤 (`label`) 與信心機率數值 (`probability`)。

**✅ 調用範例 (Python)**：
```python
from inference import predict

# 送入已清理且加入惡意 Token 的字串
cleaned_input = "Please verify your account immediately at [EVIL_URL] to prevent suspension."

result = predict(cleaned_input)

print(result)
# Output: {"label": "Phishing", "probability": 0.985}
```

---

## 3. 核心模組規格 (Core Modules Specification)

### 3.1 前端介面層 (Frontend Interface Layer)
- **檔案/模組**：`app.py`
- **技術棧**：Streamlit
- **輸入 (Input)**：使用者輸入的原始釣魚信件文本 (Raw Text)。
- **輸出 (Output)**：UI 渲染 (包含預測結果、信心機率、解碼對比日誌)。
- **職責與實作要求**：
  1. **輸入攔截與安全限制**：限制最大字元長度（例如 5000 字元），防止 DoS 攻擊。
  2. **模組橋接**：調用 `decoder.py` 與 `inference.py`，作為系統的 Controller。
  3. **解碼可視化**：接收解碼器的執行日誌，在 UI 上並列顯示「原始文本」與「解碼後明文」，提升透明度。

### 3.2 資料前處理與邏輯解碼層 (Data Processing & Decoding Layer)
- **檔案/模組**：`decoder.py`
- **技術棧**：Python 內建函式庫 (`re`, `base64`, `urllib.parse`)
- **輸入 (Input)**：原始釣魚信件文本 (Raw Text)。
- **輸出 (Output)**：
  1. 乾淨且標準化、帶有特徵 Token 的明文 (Cleaned Text)。
  2. 解碼過程的詳細日誌 (Decoding Log)。
- **職責與實作要求**：
  1. **基礎清洗**：移除 HTML 標籤 (`<...>`)、腳本代碼與多餘的空白字元。
  2. **遞迴解碼 (Recursive Decoding)**：實作偵測 Base64 與 URL Encoding 的邏輯。若解碼後的字串仍包含編碼特徵，需持續深度解碼，直到字串不再變化為止。
  3. **惡意特徵提取 (Tokenization)**：基於 Regex，將可疑的 IP 網址或異常長度的網域名稱，強制替換為模型易於識別的專屬 Token（例如 `[EVIL_URL]`, `[SUSPICIOUS_IP]`）。

### 3.3 AI 推論層 (AI Inference Layer)
- **檔案/模組**：`inference.py`
- **技術棧**：Hugging Face `transformers`, `torch`
- **輸入 (Input)**：來自 `decoder.py` 處理完的乾淨明文 (Cleaned Text)。
- **輸出 (Output)**：分類標籤 (如 `Phishing`, `Safe`) 與信心機率 (Probability)。
- **職責與實作要求**：
  1. **模型載入與封裝**：載入微調後的語言模型（如基於 `distilbert-base-uncased` 微調的版本），並封裝為單一介面 `predict(text)` 供前端呼叫。
  2. **語意分析**：針對輸入文本的上下文與特殊的惡意 Token 進行推論。
  3. **效能要求**：推論過程需輕量化，確保在 CPU 環境（無 GPU）下也能提供秒級回應。

### 3.4 模型訓練與測試驗證層 (Training & Red Teaming Layer)
- **檔案/模組**：`train.py`, `test_payloads.txt`, `Adversarial_Testing_Report.md`
- **職責與實作要求**：
  1. **離線訓練 (`train.py`)**：使用清洗並遞迴解碼過的 Kaggle 資料集（如 Enron）對基礎模型進行 Fine-Tuning。需產出 F1-Score, Precision, Recall 及 False Positive Rate (FPR) 評估報告。
  2. **AI 紅隊演練 (Red Teaming)**：建構進階對抗樣本（同形異義字、零寬度字元、干擾詞稀釋）對 Inference 引擎進行壓力測試，並記錄繞過成功的 Payload 以作為下一代模型改進依據。

---

## 4. 資料流向細節 (Data Flow Breakdown)
1. 用戶於 Streamlit 送出 Payload。
2. `app.py` 進行長度校驗 `if len(payload) > 5000: return Error`。
3. `app.py` 呼叫 `decoder.py -> process_text(payload)`。
4. `decoder.py` 執行 `remove_html()` -> `recursive_decode()` -> `tokenize_malicious_links()`，並回傳 `(cleaned_text, decode_logs)` 給 `app.py`。
5. `app.py` 呼叫 `inference.py -> predict(cleaned_text)`。
6. `inference.py` 回傳 `{"label": "Phishing", "probability": 0.98}`。
7. `app.py` 渲染結果區塊（顯示 0.98 Phishing）與日誌區塊（顯示 decode_logs）。

---

## 5. 開發與部署規範 (Development & Deployment Rules)
1. **解耦架構**：`decoder.py` 獨立於 `inference.py`。即使模型判斷失誤（假陰性），解碼日誌仍須忠實呈現被隱藏的惡意網址供人工驗證。
2. **模型權重管理**：大型模型權重檔 (`.bin`, `.safetensors`) **嚴禁**提交至 Git，必須使用 Git LFS 管理，或存放在外部空間。
3. **防禦優先原則**：任何進來的字串皆須被視為「惡意構造」，不可信任任何外部輸入的格式與長度。
