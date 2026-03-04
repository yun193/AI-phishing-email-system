"""
src/preprocessor.py - 文本預處理模組
"""
import re
from sklearn.base import BaseEstimator, TransformerMixin

class TextPreprocessor(BaseEstimator, TransformerMixin):
    def __init__(self):
        pass
        
    def fit(self, X, y=None):
        return self
        
    def transform(self, X):
        return [self._preprocess(text) for text in X]
        
    def _preprocess(self, text):
        if not isinstance(text, str):
            return ""
        # 1. 轉換為小寫
        text = text.lower()
        # 2. 移除 HTML 標籤
        text = re.sub(r'<[^>]+>', ' ', text)
        # 3. 移除特殊符號、多餘空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text
