"""
src/feature_engineering.py - 統計特徵提取模組
"""
import re
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

class StatisticalFeatureExtractor(BaseEstimator, TransformerMixin):
    def __init__(self):
        pass
        
    def fit(self, X, y=None):
        return self
        
    def transform(self, X):
        features = []
        for text in X:
            features.append(self._extract_features(text))
        return np.array(features)
        
    def _extract_features(self, text):
        if not isinstance(text, str):
            return [0, 0, 0, 0]
        
        # 1. URL 數量
        urls = len(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F]{2}))+', text))
        
        # 2. 緊迫詞彙數
        urgent_words = len(re.findall(r'\b(urgent|verify|account|suspend|limited|security|update)\b', text.lower()))
        
        # 3. 大寫字比率
        caps = sum(1 for c in text if c.isupper())
        total = len(text)
        cap_ratio = caps / total if total > 0 else 0
        
        # 4. 感嘆號數量
        exclamations = text.count('!')
        
        return [urls, urgent_words, cap_ratio, exclamations]
