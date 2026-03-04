# 🛡️ AI 釣魚郵件偵測系統 - 訓練模組架構 (Train Architecture)

## 1. 模組概述 (Module Overview)

`train.py` 是 AI 釣魚郵件偵測系統的模型訓練層 (Training Layer)。它的主要任務是處理已經清洗完成的離線資料集，建立機器學習管道 (Pipeline)，進行特徵工程與模型訓練，最後產出可用於線上環境推論的模型檔案與效能評估報告。

此模組設計為離線執行的腳本程式，不參與任何線上即時的資料流。支援透過命令列介面 (CLI) 以及 Python 本地匯入的方式進行操作，以提供最大化的開發彈性與可重現性。

---

## 2. 核心操作介面定義 (Core Interface)

本模組同時支援 CLI 指令操作與函數級別的介面呼叫。

### 2.1 函數級介面 (Python API)

當其他系統腳本需要編程化地觸發訓練或評估時，可匯入以下核心函式：

#### `train_model`
*   **功能描述**：執行從資料載入、特徵萃取到模型擬合 (Fit) 的完整流程，並儲存模型與映射檔。
*   **介面名稱**：
    ```python
    def train_model(
        data_path: str,
        text_col: str = "text",
        label_col: str = "label",
        output_dir: str = "./models",
        test_size: float = 0.2,
        max_features: int = 50000,
        n_estimators: int = 200,
        max_depth: Optional[int] = None,
    ) -> Tuple[Pipeline, pd.Series, pd.Series, Dict[str, int]]
    ```
*   **參數**：
    *   `data_path`: 來源 CSV 資料檔或 `.csv.zip` 壓縮檔的路徑。
    *   `text_col`, `label_col`: CSV 中欲作為特徵與標籤的欄位名稱。
    *   `output_dir`: 訓練完成的模型 `.pkl` 以及標籤 JSON 寫入之目錄。
    *   `test_size`: 資料切分作為驗證集的比例（預設 `0.2` 即 8:2）。
    *   `max_features`: TF-IDF 所保有的最大詞彙數。
    *   `n_estimators`: 分類器 (Random Forest) 的決策樹數量。
    *   `max_depth`: 分類器最大深度，避免過擬合使用，留空代表不限制。
*   **回傳值**：
    為方便後續評估函式直接使用，回傳一組包含模型與驗證集資料的 Tuple (`pipeline`, `X_test`, `y_test`, `label2id`)。

#### `evaluate_model`
*   **功能描述**：接收已訓練的 Pipeline，針對測試集進行驗證，產出評估指標並畫出混淆矩陣圖。
*   **介面名稱**：
    ```python
    def evaluate_model(
        pipeline: Pipeline,
        X_test: pd.Series,
        y_test: pd.Series,
        label2id: Dict[str, int],
        output_dir: str = "./models",
    ) -> Dict[str, Any]
    ```

### 2.2 命令列介面 (CLI API)

此為最主要的使用方式。開發者可透過指令調整超參數（Hyperparameters）並批次進行訓練。

```bash
python train.py --data_path <CSV路徑> --text_col <文本欄> --label_col <標籤欄> \
                --output_dir <輸出目錄> --test_size <驗證集比例> \
                --max_features <特徵數量> --n_estimators <決策樹數量> --max_depth <最大深度>
```

---

## 3. 輸出產出物 (Output Artifacts)

訓練與評估執行完畢後，預設於 `--output_dir` (例如 `./models/`) 中會生成四大核心產物，以供下游 `inference.py` 與系統管理者使用：

1.  **`model.pkl`**：使用 `joblib` 序列化的完整 Scikit-Learn Pipeline 物件，包含了已擬合 (Fitted) 的 `TfidfVectorizer` (特徵萃取) 與 `RandomForestClassifier` (推論模型)。
2.  **`label_map.json`**：紀錄從文字標籤對應至預測 ID 的映射關係 (如：`{"Safe": 0, "Phishing": 1}`)。
3.  **`eval_report.json`**：結構化的效能評估報告。包含 F1-Score、Precision、Recall、FPR（偽陽性率）與各類型的預測數目。
4.  **`confusion_matrix.png`**：視覺化輸出的混淆矩陣圖形，便於技術人員直觀評估模型是否有發生嚴重假陽性或假陰性判斷問題。

---

## 4. 資料流向細節 (Data Flow Breakdown)

在透過 CLI 啟動的完整訓練生命週期中，資料集的內部流向如下：

1.  **參數解析與環境設定 (Initialization)**：
    *   `argparse` 讀取並驗證使用者傳遞的命令列參數。
    *   呼叫 `set_seed(42)` 固定 Python 標準庫與 Numpy/Scikit-Learn 的亂數種子，以確保每一次以相同超參數與資料集執行的訓練結果完全 100% 可重現 (Reproducible)。

2.  **載入資料集與自動清洗 (`load_and_split_data`)**：
    *   檢查輸入檔案。若為 `.csv.zip` 封裝格式，程式會直接在記憶體中解壓縮 (`zipfile.ZipFile`) 並讀取第一個 CSV 檔案，不需事先處理。
    *   清理無效值：刪除包含空值 (NaN) 的紀錄。
    *   標籤轉換與適應 (Auto-Encoding)：若找不到指定的標籤欄位，會嘗試自動猜測 (如 "Target", "Class")。同時，將可讀的字串標籤透過 `label2id` 對應轉化為整數 `label_id` 欄位，以符合模型的數學運算要求。

3.  **資料切分 (Data Splitting)**：
    *   基於 `--test_size` (預設 0.2 或佔 20%)，使用 `train_test_split` 演算法且設定 `stratify=y` 進行分層隨機抽樣。此處確保分開的 `X_train` 與 `X_test` 含有比例相近的跨類別樣本，防止因不平衡切片導致成效評估偏差。

4.  **建構機器學習演算管線 (`build_pipeline`)**：
    *   **Layer 1: 特徵工程轉換器 (TfidfVectorizer)**
        *   將長篇文本提取為多維矩陣：此設定排除常見英文無腦停用詞 (`english`)、過濾掉極罕見（小於 2 次）與極常見（超過 95% 佔比）的字彙來降噪。同時捕捉單個詞 (Unigram) 以及連續兩個詞 (Bigram) 的語境關係。
    *   **Layer 2: 分類器 (RandomForestClassifier)**
        *   將高維度特徵矩陣送入隨機森林，強制啟用 `class_weight="balanced"` 設定，以動態增加少數樣本類別的權重，避免模型被多數類別過度「帶風向」。

5.  **模型擬合與儲存 (Model Fitting & Exporting)**：
    *   向 Pipeline 核心提交指令 `pipeline.fit(X_train, y_train)` 正式啟動特徵提取與決策樹的建構流程。
    *   將已建立好的「大腦」dump 成硬碟上的 `model.pkl`，並一併寫入對應的 `label_map.json` 定義。

6.  **效能評測與視覺化匯出 (`evaluate_model`)**：
    *   將之前保留從未見過的 `X_test` 重新餵給訓練好的 pipeline，取得對應的一批預測集合 `predictions`。
    *   透過 Scikit-Learn 的 metrics 套件相互交叉比對真實標籤 `y_test` 與 `predictions` 群體。
    *   計算 **FPR (False Positive Rate)**：特別關注正常信件被「誤判」為釣魚的安全容忍問題。
    *   使用 `matplotlib` 背景渲染技術產製並寫入 `confusion_matrix.png`。最後將成效印列至終端機，並存下 JSON 格式報表。
