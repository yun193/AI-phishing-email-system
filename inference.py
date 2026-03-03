"""
inference.py - AI 釣魚郵件偵測系統：AI 推論模組

功能：接收標準化明文，透過已訓練的 TF-IDF + Random Forest 模型進行推論，
回傳分類標籤與信心機率。

使用方式：
    from inference import predict
    result = predict("Please verify your account at [EVIL_URL]")
    # Output: {"label": "Phishing", "probability": 0.985}
"""

import json
import os
from typing import Dict, Union

import joblib
import numpy as np

# ─── 模型路徑設定 ───────────────────────────────────────────────
# 預設模型路徑，可透過環境變數 MODEL_DIR 覆蓋
MODEL_DIR = os.environ.get("MODEL_DIR", "./models")
MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")
LABEL_MAP_PATH = os.path.join(MODEL_DIR, "label_map.json")

# ─── 載入模型 ───────────────────────────────────────────────────
classifier = None
label_map: Dict[str, int] = {}
id2label: Dict[int, str] = {}

try:
    if os.path.exists(MODEL_PATH):
        classifier = joblib.load(MODEL_PATH)
        print(f"✅ 模型已載入：{MODEL_PATH}")

        # 載入標籤映射
        if os.path.exists(LABEL_MAP_PATH):
            with open(LABEL_MAP_PATH, "r", encoding="utf-8") as f:
                label_map = json.load(f)
            id2label = {v: k for k, v in label_map.items()}
            print(f"🏷️  標籤映射：{label_map}")
        else:
            # 預設映射
            id2label = {0: "Safe", 1: "Phishing"}
            print(f"⚠️  未找到標籤映射檔，使用預設：{id2label}")
    else:
        print(f"⚠️  模型檔案不存在：{MODEL_PATH}")
        print(f"   請先執行 train.py 訓練模型。")
except Exception as e:
    print(f"❌ 載入模型失敗：{e}")
    classifier = None


def predict(cleaned_text: str) -> Dict[str, Union[str, float]]:
    """
    接收已經過 decoder.py 清洗處理後的標準化明文，透過本地模型進行推論，
    回傳分類標籤與信心機率。

    Args:
        cleaned_text (str): 經過 decoder.py 清洗後的標準化明文
                            (可能帶有 [EVIL_URL] 等特徵 Token)

    Returns:
        Dict[str, Union[str, float]]: 包含 'label' 與 'probability' 的字典。
            例如: {"label": "Phishing", "probability": 0.985}
    """
    if classifier is None:
        return {"error": "Classifier is not initialized. Run train.py first."}

    if not cleaned_text or not cleaned_text.strip():
        return {"error": "Input text cannot be empty."}

    try:
        # 使用 Pipeline 進行預測
        prediction = classifier.predict([cleaned_text])[0]
        probabilities = classifier.predict_proba([cleaned_text])[0]

        # 取得預測類別的信心機率
        confidence: float = float(np.max(probabilities))

        # 取得標籤名稱
        label_name = id2label.get(int(prediction), str(prediction))

        # 統一標籤格式（首字大寫）
        label_name = label_name.capitalize()

        return {
            "label": label_name,
            "probability": round(confidence, 4),
        }
    except Exception as e:
        return {"error": f"Inference failed: {e}"}


# ─── 測試入口 ───────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Testing Inference Module ===")

    # 測試正常信件情境 (模擬)
    test_text_normal = "Hi team, please review the attached meeting minutes."
    print(f"Input: {test_text_normal}")
    result_normal = predict(test_text_normal)
    print(f"Prediction: {result_normal}\n")

    # 測試可疑/惡意信件情境 (模擬)
    test_text_phishing = "URGENT: Your account will be suspended in 24 hours. Click here to verify."
    print(f"Input: {test_text_phishing}")
    result_phishing = predict(test_text_phishing)
    print(f"Prediction: {result_phishing}\n")

    print("=== Inference Module Ready ===")
