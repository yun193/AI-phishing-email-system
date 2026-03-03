# 釣魚電子郵件檢測系統 — 架構書

**系統名稱：** Phishing Email Detector  
**模型演算法：** Random Forest  
**訓練策略：** Pipeline + K-Fold Cross Validation  
**版本：** v1.0  
**日期：** 2026-03-03  

---

## 目錄

1. [系統概述](#1-系統概述)
2. [系統架構總覽](#2-系統架構總覽)
3. [目錄結構](#3-目錄結構)
4. [模組說明](#4-模組說明)
   - 4.1 [資料層 (Data Layer)](#41-資料層-data-layer)
   - 4.2 [特徵工程層 (Feature Engineering Layer)](#42-特徵工程層-feature-engineering-layer)
   - 4.3 [模型訓練層 (Model Training Layer)](#43-模型訓練層-model-training-layer)
   - 4.4 [評估層 (Evaluation Layer)](#44-評估層-evaluation-layer)
   - 4.5 [推論層 (Inference Layer)](#45-推論層-inference-layer)
5. [Pipeline 設計](#5-pipeline-設計)
6. [K-Fold 交叉驗證設計](#6-k-fold-交叉驗證設計)
7. [介面設計 (Interface)](#7-介面設計-interface)
8. [資料流程圖](#8-資料流程圖)
9. [技術選型](#9-技術選型)
10. [錯誤處理策略](#10-錯誤處理策略)
11. [擴充性設計](#11-擴充性設計)

---

## 1. 系統概述

本系統旨在透過機器學習方法，自動判斷輸入的電子郵件文本是否為釣魚郵件（Phishing Email）。

### 核心功能

- 接收電子郵件文本（主旨 + 內文）作為輸入
- 使用 Random Forest 分類器進行二元分類（釣魚 / 正常）
- 輸出判斷結果及信心分數（Confidence Score）
- 支援批次預測與單筆即時預測

### 判斷類別

| 類別 | 標籤 | 說明 |
|------|------|------|
| 正常郵件 | `0` | 合法電子郵件 |
| 釣魚郵件 | `1` | 惡意/詐騙電子郵件 |

---

## 2. 系統架構總覽

```
┌─────────────────────────────────────────────────────────┐
│                      使用者介面層                         │
│         CLI / REST API / Python Function Call            │
└──────────────────────┬──────────────────────────────────┘
                       │ 輸入文本
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    推論層 (Inference)                     │
│              載入已訓練 Pipeline 模型                     │
│           → 文本預處理 → 特徵提取 → 預測                 │
└──────────────────────┬──────────────────────────────────┘
                       │ 預測結果 + 信心分數
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    輸出結果層                             │
│     { label: "phishing/legitimate", confidence: 0.xx }  │
└─────────────────────────────────────────────────────────┘

─────────────── 訓練流程（離線）───────────────

┌──────────┐    ┌─────────────┐    ┌───────────────┐
│  原始資料  │ → │  資料預處理  │ → │  特徵工程層    │
│  (CSV)   │    │  清洗/分割   │    │  TF-IDF/統計  │
└──────────┘    └─────────────┘    └───────┬───────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │   Pipeline 建構         │
                              │  Preprocessor +         │
                              │  TfidfVectorizer +      │
                              │  RandomForestClassifier │
                              └───────────┬────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │  K-Fold 交叉驗證        │
                              │  (StratifiedKFold, k=5) │
                              └───────────┬────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │  模型評估               │
                              │  Accuracy/F1/AUC/ROC   │
                              └───────────┬────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │  儲存最佳模型           │
                              │  model/pipeline.pkl    │
                              └────────────────────────┘
```

---

## 3. 目錄結構

```
phishing_email_detector/
│
├── data/
│   ├── raw/
│   │   └── emails.csv              # 原始資料集（含標籤欄位）
│   ├── processed/
│   │   ├── train.csv               # 訓練集
│   │   └── test.csv                # 測試集
│   └── README.md                   # 資料集說明
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py              # 資料載入與分割
│   ├── preprocessor.py             # 文本清洗與預處理
│   ├── feature_engineering.py      # 特徵提取（TF-IDF + 統計特徵）
│   ├── model.py                    # Pipeline 建構 + K-Fold 訓練
│   ├── evaluator.py                # 模型評估指標
│   └── predictor.py                # 推論介面
│
├── model/
│   └── pipeline.pkl                # 已訓練並序列化之 Pipeline 模型
│
├── notebooks/
│   └── exploration.ipynb           # 資料探索與實驗
│
├── tests/
│   ├── test_preprocessor.py
│   ├── test_model.py
│   └── test_predictor.py
│
├── main.py                         # 主程式進入點（CLI）
├── requirements.txt                # 相依套件
└── README.md                       # 專案說明
```

---

## 4. 模組說明

### 4.1 資料層 (Data Layer)

**檔案：** `src/data_loader.py`

#### 職責
- 載入原始 CSV 資料集
- 執行訓練集 / 測試集分割（預設 80% / 20%）
- 確保類別分佈平衡（Stratified Split）

#### 輸入格式

| 欄位名稱 | 型別 | 說明 |
|----------|------|------|
| `subject` | `str` | 郵件主旨 |
| `body` | `str` | 郵件內文 |
| `label` | `int` | 標籤：0=正常，1=釣魚 |

#### 核心介面

```python
class DataLoader:
    def load(self, filepath: str) -> pd.DataFrame
    def split(self, df: pd.DataFrame, test_size: float = 0.2) 
              -> tuple[pd.DataFrame, pd.DataFrame]
```

---

### 4.2 特徵工程層 (Feature Engineering Layer)

**檔案：** `src/preprocessor.py` + `src/feature_engineering.py`

#### 文本預處理步驟

```
原始文本
   │
   ▼
1. 合併主旨與內文 (subject + " " + body)
   │
   ▼
2. 轉換為小寫
   │
   ▼
3. 移除 HTML 標籤 (<a>, <img> ...)
   │
   ▼
4. 移除特殊符號、多餘空白
   │
   ▼
5. Tokenization（分詞）
   │
   ▼
6. 停用詞移除 (Stop Words Removal)
   │
   ▼
7. 詞幹還原 (Stemming / Lemmatization)
   │
   ▼
清洗後文本
```

#### 特徵類型

| 特徵類型 | 說明 | 實作方式 |
|----------|------|----------|
| TF-IDF 詞頻特徵 | 詞彙的 TF-IDF 權重向量 | `TfidfVectorizer` |
| URL 數量 | 郵件中超連結個數 | Regex 統計 |
| 緊迫詞彙數 | 含有 "urgent", "verify" 等詞彙數量 | 關鍵字清單比對 |
| 大寫字比率 | 全大寫字母佔比 | 字串分析 |
| 感嘆號數量 | `!` 符號出現次數 | 字元計數 |

#### 核心介面

```python
class TextPreprocessor(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None) -> "TextPreprocessor"
    def transform(self, X) -> list[str]

class StatisticalFeatureExtractor(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None) -> "StatisticalFeatureExtractor"
    def transform(self, X) -> np.ndarray  # shape: (n_samples, n_stat_features)
```

---

### 4.3 模型訓練層 (Model Training Layer)

**檔案：** `src/model.py`

#### Random Forest 超參數

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `n_estimators` | `200` | 決策樹棵數 |
| `max_depth` | `None` | 最大樹深（自動） |
| `min_samples_split` | `5` | 節點分裂最小樣本數 |
| `min_samples_leaf` | `2` | 葉節點最小樣本數 |
| `max_features` | `"sqrt"` | 每次分裂考慮的特徵數 |
| `class_weight` | `"balanced"` | 處理類別不平衡 |
| `random_state` | `42` | 隨機種子 |
| `n_jobs` | `-1` | 使用全部 CPU 核心 |

#### 核心介面

```python
class PhishingDetectorModel:
    def build_pipeline(self) -> Pipeline
    def train_with_kfold(self, X: pd.Series, y: pd.Series, 
                          n_splits: int = 5) -> dict
    def save(self, filepath: str) -> None
    def load(self, filepath: str) -> None
```

---

### 4.4 評估層 (Evaluation Layer)

**檔案：** `src/evaluator.py`

#### 評估指標

| 指標 | 說明 |
|------|------|
| Accuracy | 整體預測準確率 |
| Precision | 精確率（釣魚郵件） |
| Recall | 召回率（釣魚郵件） |
| F1-Score | Precision 與 Recall 的調和平均 |
| AUC-ROC | ROC 曲線下面積 |
| Confusion Matrix | 混淆矩陣（TP/FP/TN/FN） |

#### 核心介面

```python
class Evaluator:
    def evaluate(self, y_true: np.ndarray, 
                 y_pred: np.ndarray, 
                 y_prob: np.ndarray) -> dict
    def plot_confusion_matrix(self, y_true, y_pred) -> None
    def plot_roc_curve(self, y_true, y_prob) -> None
```

---

### 4.5 推論層 (Inference Layer)

**檔案：** `src/predictor.py`

#### 職責
- 載入已序列化的 Pipeline 模型（`pipeline.pkl`）
- 接收使用者輸入的郵件文本
- 回傳預測標籤與信心分數

#### 核心介面

```python
class PhishingPredictor:
    def __init__(self, model_path: str = "model/pipeline.pkl")
    
    def predict(self, text: str) -> dict:
        """
        回傳格式：
        {
            "label": "phishing" | "legitimate",
            "confidence": float,  # 0.0 ~ 1.0
            "probability": {
                "legitimate": float,
                "phishing": float
            }
        }
        """
    
    def predict_batch(self, texts: list[str]) -> list[dict]
```

---

## 5. Pipeline 設計

### Pipeline 完整架構

```
輸入文本 (raw text)
        │
        ▼
┌───────────────────────────────────────────────────┐
│                   sklearn Pipeline                 │
│                                                   │
│  Step 1: TextPreprocessor                         │
│          清洗文本（小寫化、去除HTML、停用詞移除）    │
│                  │                                │
│                  ▼                                │
│  Step 2: FeatureUnion（特徵合併）                  │
│          ┌───────────────┬──────────────────┐     │
│          │               │                  │     │
│  TfidfVectorizer  StatisticalFeatures        │     │
│  (TF-IDF 詞頻)   (URL數/大寫比/感嘆號)       │     │
│          │               │                  │     │
│          └───────┬───────┘                  │     │
│                  │ scipy sparse matrix       │     │
│                  ▼                           │     │
│  Step 3: RandomForestClassifier              │     │
│          二元分類（0=正常 / 1=釣魚）          │     │
└──────────────────┬────────────────────────────┘
                   │
                   ▼
           預測標籤 + 機率分佈
```

### Pipeline 程式碼結構

```python
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier

pipeline = Pipeline([
    ("preprocessor", TextPreprocessor()),
    ("features", FeatureUnion([
        ("tfidf", TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            sublinear_tf=True
        )),
        ("stats", StatisticalFeatureExtractor()),
    ])),
    ("classifier", RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    ))
])
```

---

## 6. K-Fold 交叉驗證設計

### 採用 StratifiedKFold（k=5）

使用 `StratifiedKFold` 確保每個折疊（Fold）中，釣魚郵件與正常郵件的比例一致，避免類別不平衡造成的評估偏差。

### 訓練流程

```
全部訓練資料 (X_train, y_train)
               │
               ▼
    StratifiedKFold(n_splits=5)
               │
    ┌──────────┼──────────┐
    │          │          │
  Fold 1     Fold 2  ... Fold 5
    │
    ├── Train Set（80%）→ pipeline.fit()
    └── Val Set  （20%）→ pipeline.predict() → 計算指標
               │
               ▼
    收集 5 個 Fold 的評估指標
    計算平均值與標準差
               │
               ▼
    使用全部訓練資料重新訓練最終模型
    pipeline.fit(X_train, y_train)
               │
               ▼
    在測試集評估最終模型
    pipeline.predict(X_test)
```

### K-Fold 程式碼結構

```python
from sklearn.model_selection import StratifiedKFold, cross_validate

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

cv_results = cross_validate(
    pipeline,
    X_train,
    y_train,
    cv=skf,
    scoring=["accuracy", "f1", "roc_auc", "precision", "recall"],
    return_train_score=True,
    n_jobs=-1
)

# 輸出各 Fold 指標
for metric in ["accuracy", "f1", "roc_auc"]:
    scores = cv_results[f"test_{metric}"]
    print(f"{metric}: {scores.mean():.4f} ± {scores.std():.4f}")

# 最終訓練
pipeline.fit(X_train, y_train)
```

---

## 7. 介面設計 (Interface)

### 7.1 CLI 介面（命令列）

**訓練模式：**
```bash
python main.py train --data data/raw/emails.csv --kfolds 5
```

**預測模式（單筆）：**
```bash
python main.py predict --text "Your account has been suspended. Click here to verify."
```

**預測模式（檔案批次）：**
```bash
python main.py predict --file emails_to_check.csv --output results.csv
```

**CLI 輸出範例：**
```
========================================
  釣魚郵件檢測結果
========================================
  輸入文本 : "Your account has been suspended..."
  判斷結果 : ⚠️  釣魚郵件 (Phishing)
  信心分數 : 94.3%
  機率分佈 :
    - 正常郵件 : 5.7%
    - 釣魚郵件 : 94.3%
========================================
```

### 7.2 Python API 介面

```python
from src.predictor import PhishingPredictor

predictor = PhishingPredictor(model_path="model/pipeline.pkl")

# 單筆預測
result = predictor.predict(
    "Congratulations! You've won $1,000,000. Click here to claim your prize."
)
print(result)
# {
#     "label": "phishing",
#     "confidence": 0.96,
#     "probability": {
#         "legitimate": 0.04,
#         "phishing": 0.96
#     }
# }

# 批次預測
results = predictor.predict_batch([
    "Meeting reminder for tomorrow at 3pm.",
    "Urgent: Verify your banking details now!"
])
```

### 7.3 輸入 / 輸出規格

#### 輸入規格

| 項目 | 說明 | 範例 |
|------|------|------|
| 輸入型別 | `str` | 純文字字串 |
| 最小長度 | 10 字元 | — |
| 最大長度 | 50,000 字元 | — |
| 支援語言 | 英文（主要）| — |
| 格式 | 主旨 + 內文可合併傳入 | `"[SUBJECT] {subject}\n{body}"` |

#### 輸出規格

```json
{
  "label": "phishing",
  "confidence": 0.94,
  "probability": {
    "legitimate": 0.06,
    "phishing": 0.94
  },
  "warning_level": "HIGH"
}
```

| `warning_level` | `confidence` 範圍 | 說明 |
|-----------------|-------------------|------|
| `LOW` | < 0.50 | 可能為正常郵件 |
| `MEDIUM` | 0.50 – 0.75 | 疑似釣魚，建議人工複查 |
| `HIGH` | > 0.75 | 高度疑似釣魚郵件 |

---

## 8. 資料流程圖

```
【訓練流程】

原始資料 (emails.csv)
        │
        ▼
  DataLoader.load()
  └─ 讀取 CSV，確認欄位完整性
        │
        ▼
  DataLoader.split()
  └─ Stratified Train/Test Split (80/20)
        │
        ├──────────────────────────────────┐
        ▼                                  ▼
   X_train, y_train               X_test, y_test
        │
        ▼
  Pipeline.fit() + StratifiedKFold(k=5)
  └─ K 次訓練/驗證循環
  └─ 記錄每折指標
        │
        ▼
  印出 K-Fold 平均指標
        │
        ▼
  Pipeline.fit(X_train, y_train)  ← 使用全部訓練資料重新訓練
        │
        ▼
  Evaluator.evaluate(X_test, y_test)
  └─ 輸出最終測試指標、混淆矩陣、ROC 曲線
        │
        ▼
  joblib.dump(pipeline, "model/pipeline.pkl")
  └─ 序列化模型


【推論流程】

使用者輸入文本
        │
        ▼
  PhishingPredictor.predict(text)
        │
        ▼
  pipeline.predict_proba(text)
  └─ 內部自動執行：
     1. TextPreprocessor.transform()
     2. FeatureUnion.transform()
        ├─ TfidfVectorizer.transform()
        └─ StatisticalFeatureExtractor.transform()
     3. RandomForestClassifier.predict_proba()
        │
        ▼
  組裝輸出結果
  { label, confidence, probability, warning_level }
        │
        ▼
  回傳給使用者
```

---

## 9. 技術選型

| 元件 | 技術/套件 | 版本建議 | 說明 |
|------|-----------|----------|------|
| 程式語言 | Python | >= 3.10 | 主要開發語言 |
| 機器學習框架 | scikit-learn | >= 1.3 | Pipeline、RF、KFold |
| 數值運算 | NumPy | >= 1.24 | 矩陣運算 |
| 資料處理 | Pandas | >= 2.0 | CSV 讀寫與資料清洗 |
| 文本處理 | NLTK / spaCy | >= 3.7 | Tokenization、停用詞 |
| 稀疏矩陣 | SciPy | >= 1.11 | FeatureUnion 合併 |
| 模型序列化 | joblib | >= 1.3 | Pipeline 存檔 |
| 視覺化 | Matplotlib / Seaborn | >= 3.7 | ROC、混淆矩陣圖 |
| 測試框架 | pytest | >= 7.0 | 單元測試 |

### requirements.txt

```
scikit-learn>=1.3.0
numpy>=1.24.0
pandas>=2.0.0
nltk>=3.8.0
scipy>=1.11.0
joblib>=1.3.0
matplotlib>=3.7.0
seaborn>=0.12.0
pytest>=7.0.0
```

---

## 10. 錯誤處理策略

| 錯誤情境 | 處理方式 | 回傳結果 |
|----------|----------|----------|
| 輸入文本為空 | 拋出 `ValueError` | 錯誤訊息提示 |
| 輸入文本過短（< 10 字元） | 警告並降低信心分數 | `warning_level: LOW` |
| 模型檔案不存在 | 拋出 `FileNotFoundError` | 提示需先執行訓練 |
| 資料集欄位缺失 | 拋出 `KeyError` | 顯示缺失欄位名稱 |
| 記憶體不足 | 捕捉 `MemoryError` | 建議減少 `max_features` |

---

## 11. 擴充性設計

### 短期擴充（v1.1）
- 支援多語言輸入（繁體中文、日文）
- 加入寄件者信箱網域黑名單特徵
- 提供 REST API（FastAPI）服務

### 中期擴充（v2.0）
- 整合 BERT / DistilBERT 嵌入特徵以提升準確率
- 加入主動學習機制，持續收集錯誤分類樣本更新模型
- 支援模型版本管理（MLflow / DVC）

### 長期擴充（v3.0）
- 轉換為即時串流檢測架構（Apache Kafka + Spark Streaming）
- 多模型集成（Ensemble of RF + XGBoost + BERT）
- 提供組織層級的儀表板（Dashboard）呈現威脅統計

---

*本架構書由系統設計團隊維護，如有修訂請更新版本號並記錄變更原因。*
