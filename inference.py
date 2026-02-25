from typing import Dict, Union
from transformers import pipeline

# 初始化 Hugging Face pipeline，作為分類器
# 在初期 MVP 階段，我們先使用預設的情緒分析分類器來做格式測試
# 待第二週微調好模型後，將 "distilbert-base-uncased-finetuned-sst-2-english" 替換成我們的模型路徑即可
# 預設會在 CPU 執行，如果有裝好 torch 且有 GPU，可以設定 device=0 
try:
    classifier = pipeline(
        "text-classification", 
        model="distilbert-base-uncased-finetuned-sst-2-english", 
        device=-1 # 強制使用 CPU 避免初期環境問題
    )
except Exception as e:
    print(f"Error loading model: {e}")
    classifier = None

# MVP 階段標籤映射：將情緒分析模型的標籤轉換為架構書定義的 Phishing/Safe
# 待微調模型完成後，模型會直接輸出正確標籤，屆時可移除此映射
LABEL_MAP = {
    "NEGATIVE": "Phishing",
    "POSITIVE": "Safe",
}


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
    if not classifier:
        return {"error": "Classifier pipeline is not initialized."}

    if not cleaned_text or not cleaned_text.strip():
        return {"error": "Input text cannot be empty."}

    # 使用 pipeline 進行推論
    try:
        results = classifier(cleaned_text)
        # pipeline 對於 text-classification 回傳的格式為: [{'label': '...', 'score': 0....}]
        result = results[0]
        raw_label = result["label"]

        return {
            "label": LABEL_MAP.get(raw_label) or raw_label,
            "probability": round(result["score"], 4)
        }
    except Exception as e:
        return {"error": f"Inference failed: {e}"}

# Task 1.2 & 1.3 驗收執行區塊
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
