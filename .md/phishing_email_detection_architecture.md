# 釣魚電子郵件檢測系統 — 架構書

**系統名稱：** Phishing Email Detector  
**模型演算法：** Random Forest (RF) + TF-IDF  
**訓練策略：** Pipeline + K-Fold Cross Validation  
**開發工具：** Python, Streamlit, Scikit-learn  
**版本：** v1.1  
**日期：** 2026-03-04  

---

## 目錄

1. [系統概述](#1-系統概述)
2. [系統架構總覽](#2-系統架構總覽)
3. [目錄結構](#3-目錄結構)
4. [模組說明](#4-模組說明)
   - 4.1 [前端與整合層 (yun193)](#41-前端與整合層-yun193)
   - 4.2 [資安前處理與特徵工程層 (Erichen0216)](#42-資安前處理與特徵工程層-erichen0216)
   - 4.3 [模型訓練與推論層 (ying0215)](#43-模型訓練與推論層-ying0215)
5. [詳細調用介面 (Detailed Interfaces)](#5-詳細調用介面-detailed-interfaces)
6. [Pipeline 與推論流程](#6-pipeline-與推論流程)
7. [技術選型](#7-技術選型)

---

## 1. 系統概述

本系統採用機器學習技術，結合深入的資安文本預處理，旨在自動識別釣魚郵件。系統分為預處理、特徵提取、以及基於隨機森林（Random Forest）的分類推論三大核心環節。

---

## 2. 系統架構總覽

```
┌─────────────────────────────────────────────────────────┐
│                      使用者介面層 (App)                   │
│                    Streamlit Web Interface              │
└──────────────────────┬──────────────────────────────────┘
                       │ (1) 原始郵件文本
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    資安前處理層 (Decoder)                 │
│         Base64/URL 反混淆、雜訊清洗、HTML 移除             │
└──────────────────────┬──────────────────────────────────┘
                       │ (2) 清洗後明文
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    推論與介面層 (Predictor)               │
│         (3) 特徵工程 (TF-IDF + 統計特徵)                   │
│         (4) 隨機森林模型分類 (Random Forest)              │
└──────────────────────┬──────────────────────────────────┘
                       │ (5) 預測標籤、信心分數、警告等級
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    結果展示層 (Display)                   │
│                單筆分析報告 / 批量測試報告                │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 目錄結構

```
AI-phishing-email-system/
├── models/                     # 模型儲存目錄
│   ├── pipeline.pkl           # 訓練完成的 Pipeline 模型 (TF-IDF + RF)
│   └── label_map.json         # 標籤映射表 ({"Safe": 0, "Phishing": 1})
├── src/                        # 核心源碼
│   ├── __init__.py            # 套件初始化
│   ├── predictor.py           # 推論介面與 Predictor 類別
│   ├── preprocessor.py        # 文本預處理 (TextPreprocessor)
│   └── feature_engineering.py  # 特徵工程 (StatisticalFeatureExtractor)
├── app.py                      # Streamlit 整合應用程式 (UI)
├── decoder.py                  # 解碼與清洗基礎類別
├── inference.py                # 推論輔助腳本
├── train.py                    # 模型訓練腳本
└── requirements.txt            # 環境需求
```

---

## 4. 模組說明

### 4.1 前端與整合層 (yun193)
- **檔案：** `app.py`
- **職責：** 
    - 建立 Streamlit Web UI。
    - 整合 `ying0215` 的模型與 `Erichen0216` 的解碼器。
    - 處理單筆輸入推論與批量檔案（.txt）解析。
    - 呈現視覺化的分析報告與指標。

### 4.2 資安前處理與特徵工程層 (Erichen0216)
- **檔案：** `decoder.py`, `src/preprocessor.py`, `src/feature_engineering.py`
- **職責：** 
    - **解碼：** Base64 還原、URL Decoding。
    - **清洗：** HTML 標籤移除、雜訊過濾。
    - **特徵：** 統計特徵提取（URL 數量、大寫比、緊迫詞彙、感嘆號等）。

### 4.3 模型訓練與推論層 (ying0215)
- **檔案：** `train.py`, `src/predictor.py`
- **職責：** 
    - **訓練：** 使用隨機森林（Random Forest）與 TF-IDF 進行模型訓練。
    - **推論：** 提供 `PhishingPredictor` 介面，封裝模型載入與預測邏輯。

---

## 5. 詳細調用介面 (Detailed Interfaces)

### 5.1 `PhishingDecoder` (資安清洗)
- **類別：** `decoder.PhishingDecoder`
- **方法：**
    - `process_text(text: str) -> str`: 執行完整的解碼、清洗與正規化。

### 5.2 `PhishingPredictor` (模型介面)
- **類別：** `src.predictor.PhishingPredictor`
- **初始化：** `__init__(model_path: str = "models/pipeline.pkl")`
- **方法：**
    - `predict(text: str) -> dict`: 執行單筆推論。
    - `predict_batch(texts: list[str]) -> list[dict]`: 執行批次推論。
- **回傳格式 (Return Schema):**
```json
{
    "label": "phishing" | "safe",
    "confidence": 0.9432,
    "probability": {
        "legitimate": 0.0568,
        "phishing": 0.9432
    },
    "warning_level": "HIGH" | "MEDIUM" | "LOW"
}
```

### 5.3 `TextPreprocessor` (Scikit-learn Transformer)
- **類別：** `src.preprocessor.TextPreprocessor`
- **繼承：** `BaseEstimator`, `TransformerMixin`
- **方法：** `transform(X: list[str]) -> list[str]`

### 5.4 `StatisticalFeatureExtractor` (Scikit-learn Transformer)
- **類別：** `src.feature_engineering.StatisticalFeatureExtractor`
- **繼承：** `BaseEstimator`, `TransformerMixin`
- **方法：** `transform(X: list[str]) -> np.ndarray` (特徵矩陣：(n, 4))

---

## 6. Pipeline 與推論流程

系統將所有處理步驟封裝於 `sklearn.Pipeline` 中，確保訓練與推論的一致性：

1. **TextPreprocessor**: 文本清洗與解碼。
2. **FeatureUnion**:
   - **TfidfVectorizer**: 提取詞頻特徵。
   - **StatisticalFeatureExtractor**: 提取 URL 數、緊迫詞數、大寫比、感嘆號。
3. **RandomForestClassifier**: 根據合併特徵進行二元分類。

---

## 7. 技術選型

- **機器學習：** Scikit-learn (RandomForestClassifier, TfidfVectorizer)
- **資安前處理：** Re, Base64, Urllib
- **前端框架：** Streamlit
- **資料處理：** Pandas, NumPy
- **模型儲存：** Joblib
