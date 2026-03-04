"""
src/predictor.py - AI 釣魚郵件偵測系統：推論介面模組

本模組實作了 PhishingPredictor 類別，負責載入已訓練的 Pipeline 模型並執行預測。
符合 phishing_email_detection_architecture.md 中的 4.5 節定義。
"""

import os
import joblib
import numpy as np
from typing import Dict, List, Union

# 必須匯入這些類別，以便 joblib 載入 pipeline.pkl 時能找到定義
from src.preprocessor import TextPreprocessor
from src.feature_engineering import StatisticalFeatureExtractor

class PhishingPredictor:
    def __init__(self, model_path: str = "models/pipeline.pkl"):
        """
        初始化預測器並載入模型。
        
        Args:
            model_path (str): 模型檔案路徑。
        """
        # 取得專案根目錄路徑
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.absolute_model_path = os.path.join(self.base_dir, model_path)
        
        # 備選模型路徑 (model.pkl)
        self.fallback_path = os.path.join(self.base_dir, "models/model.pkl")
        
        self.classifier = self._load_model(self.absolute_model_path)
        if self.classifier is None:
            print(f"🔄 正在嘗試回退至備選模型：{self.fallback_path}")
            self.classifier = self._load_model(self.fallback_path)
            
        if self.classifier is None:
            raise FileNotFoundError(f"無法載入模型檔案：{self.absolute_model_path} 或 {self.fallback_path}")

        # 載入標籤映射 (預設 0=Safe, 1=Phishing)
        self.id2label = {0: "Safe", 1: "Phishing"}
        
    def _load_model(self, path: str):
        if os.path.exists(path):
            try:
                model = joblib.load(path)
                print(f"✅ 模型成功載入：{path}")
                return model
            except Exception as e:
                print(f"⚠️ 載入模型失敗 ({path}): {e}")
                return None
        return None

    def predict(self, text: str) -> Dict[str, Union[str, float, Dict[str, float]]]:
        """
        接收單筆文本，回傳預測結果。
        
        Args:
            text (str): 郵件文本。
            
        Returns:
            Dict: 預測結果字典。
        """
        if not text or not text.strip():
            return {"error": "Input text cannot be empty."}

        try:
            # 使用 Pipeline 進行預測
            prediction = self.classifier.predict([text])[0]
            probabilities = self.classifier.predict_proba([text])[0]

            # 信心分數 (最大機率)
            confidence = float(np.max(probabilities))
            
            # 各類別機率
            prob_dict = {
                "legitimate": round(float(probabilities[0]), 4),
                "phishing": round(float(probabilities[1]), 4)
            }
            
            label_name = self.id2label.get(int(prediction), str(prediction))
            
            # 判斷警告等級 (依據架構書 7.3)
            warning_level = "LOW"
            if label_name == "Phishing":
                if confidence > 0.75:
                    warning_level = "HIGH"
                elif confidence > 0.50:
                    warning_level = "MEDIUM"

            return {
                "label": label_name.lower(), # phishing | safe (architecture says "phishing" | "legitimate" but label_map says "Safe")
                "confidence": round(confidence, 4),
                "probability": prob_dict,
                "warning_level": warning_level
            }
        except Exception as e:
            return {"error": f"Inference failed: {e}"}

    def predict_batch(self, texts: List[str]) -> List[Dict]:
        """
        接收多筆文本，回傳預測結果列表。
        """
        return [self.predict(t) for t in texts]

if __name__ == "__main__":
    # 簡單測試
    try:
        predictor = PhishingPredictor()
        print(predictor.predict("URGENT: Verify your account!"))
    except Exception as e:
        print(e)
