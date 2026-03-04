# 🛡️ AI 釣魚郵件偵測系統 - 推論模組架構 (Inference Architecture)

## 1. 模組概述 (Module Overview)

`inference.py` 是 AI 釣魚郵件偵測系統的核心推論引擎 (AI Inference Layer)。它的主要職責是接收由資料前處理與邏輯解碼層 (`decoder.py`) 處理過後的「標準化明文」(Cleaned Text)，並透過已訓練好的機器學習模型進行即時的分類推論，最後回傳該文本的分類標籤（例如：`Phishing` 或 `Safe`）以及模型的信心機率。

本模組設計為極輕量化且與前端/解碼邏輯完全解耦，允許毫秒等級的回應速度，非常適合部署於資源受限（如無 GPU 的 CPU 主機）的生產環境中。

---

## 2. 核心 API 介面定義 (Core API Interface)

本模組對外提供單一的推論介面 `predict`，供應用程式的控制器（如 `app.py` 之下游）調用。

### 介面名稱：`predict`
```python
def predict(cleaned_text: str) -> Dict[str, Union[str, float]]:
```

### 參數 (Arguments):
*   `cleaned_text` (String): 
    *   **描述**：已經過清洗、去標籤化且替換異常特徵 Token (例如 `[EVIL_URL]`, `[SUSPICIOUS_IP]`) 的標準化字串。
    *   **限制**：不可為空字串或僅含空白的字串。

### 回傳值 (Returns):
*   **型別**：`Dict[str, Union[str, float]]`
*   **內容結構**：
    包含推論結果的字典物件。
    *   成功時回傳範例：
        ```json
        {
          "label": "Phishing",
          "probability": 0.985
        }
        ```
        *   `label` (str): 分類結果標籤，通常為 `"Phishing"`（釣魚郵件）或 `"Safe"`（安全），首字母會自動大寫。
        *   `probability` (float): 模型對此分類的信心機率，經四捨五入至小數點後四位。
    *   失敗或例外錯誤時回傳範例：
        ```json
        {
          "error": "Input text cannot be empty."
        }
        ```

---

## 3. 模組載入機制與資源管理 (Initialization & Model Loading)

`inference.py` 在被匯入 (Import) 時，會執行一次性的全域初始化操作，以將模型載入記憶體中，避免每次呼叫 `predict` 時重複讀取硬碟，進而提升推論效能。

### 3.1 目錄與路徑解析
*   **預設模型目錄**：`./models`
*   **環境變數覆蓋**：可透過設定作業系統環境變數 `MODEL_DIR` 來指定自訂的模型路徑，增加部署彈性。
*   **目標檔案**：
    *   `model.pkl`：包含特徵萃取 (如 `TfidfVectorizer`) 與分類器 (如 `RandomForestClassifier`) 的完整 Scikit-Learn Pipeline 物件。
    *   `label_map.json`：用以將模型預測的整數 ID (如 `0`, `1`) 對應至具體字串標籤 (如 `"Safe"`, `"Phishing"`) 的映射檔。

### 3.2 載入邏輯與錯誤容忍
1.  **檢查 `model.pkl`**：使用 `joblib.load()` 將序列化的模型載入記憶體。若不存在，全域 `classifier` 變數將維持為 `None`，不阻斷程式載入，但調用 `predict` 時將返回錯誤提示需先執行 `train.py`。
2.  **載入 `label_map.json`**：讀取 JSON 格式的標籤映射，並建立 `id2label` 的反查字典。
3.  **預設降級策略 (Fallback)**：若 `label_map.json` 不存在，系統自動降級採用預設映射 `{0: "Safe", 1: "Phishing"}`，確保模型依然能給出具有業務意義的推論結果。

---

## 4. 資料流向細節 (Data Flow Breakdown)

當調用 `predict(cleaned_text)` 時，內部執行的完整資料流向如下：

1.  **狀態與防呆檢查 (Sanity Check)**：
    *   檢查 `classifier` 是否已成功初始化：若為 `None`，立即阻斷並回傳 `"error": "Classifier is not initialized..."`。
    *   檢查 `cleaned_text` 內容：若傳入空字串或全空白，即刻回傳 `"error": "Input text cannot be empty."`，防止後續 Pipeline 拋出例外。

2.  **特徵轉型與機率運算 (Feature Transformation & Inference)**：
    *   呼叫 `classifier.predict([cleaned_text])` 取得預測類別的內部 Integer ID。這部分 `joblib` 會先自動套用 TF-IDF 將字串轉換為向量，再送入隨機森林。
    *   同時呼叫 `classifier.predict_proba([cleaned_text])` 取得所有類別上的預測機率陣列。

3.  **數值萃取與格式化 (Extraction & Formatting)**：
    *   **信心機率 (Confidence)**：使用 `np.max(probabilities)` 取出機率陣列中的最大值做為最終信心分數，並轉型為 Python 原生 `float`。
    *   **標籤查找 (Label Lookup)**：利用步驟 2 拿到的預測 ID，透過 `id2label` 字典反查得實際標籤名稱字串 (如 `"phishing"`)。
    *   **文字正規化**：對取出的標籤名稱執行 `.capitalize()` 確保首字大寫（統一前端 UI 呈現標準）。
    *   **四捨五入**：信心機率分數呼叫 `round(confidence, 4)` 取至小數點第四位。

4.  **最終回傳 (Return)**：
    *   封裝為 Dict 結構返回。若在上述流向中有任何非預期例外（如維度錯誤），則以 `try-except` 捕獲，並回傳帶有 `"error": f"Inference failed: {e}"` 的 JSON 相容字典。

---

## 5. 相依套件與技術棧 (Dependencies)

*   **`joblib`**：高效載入與反序列化大型機器學習模型管道 (`.pkl`)。
*   **`numpy`**：支援快速的數值與陣列運算，以提取最高機率。
*   **`json`**：存取模型附屬的標籤映射描述檔。
*   *備註：推論環境中仍需安裝 `scikit-learn`（預設要求為此套件產生 `.pkl` 的版本範圍內），以保證特徵轉換介面齊全。*
