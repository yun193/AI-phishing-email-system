import re
import base64
import urllib.parse

class PhishingDecoder:
    """
    釣魚郵件解碼與清洗模組
    負責還原 URL 編碼、Base64 編碼，並清除 HTML 標籤與多餘空白。
    """
    def __init__(self):
        # 預先編譯正規表示式以提升效能
        # 尋找 URL 編碼 (例如 %20, %3D)
        self.url_enc_pattern = re.compile(r'(?:%[0-9a-fA-F]{2})+')
        
        # 尋找 Base64 特徵字串 (設定最少長度為 12，減少誤判一般英文單字)
        self.base64_pattern = re.compile(r'(?:[A-Za-z0-9+/]{4}){3,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?')
        
        # 尋找 HTML 標籤
        self.html_pattern = re.compile(r'<[^>]+>')

    def process_text(self, text: str) -> str:
        """
        主接口：執行完整的解碼與清洗流程
        """
        # 防呆機制：如果輸入不是字串 (例如 Pandas 中的 NaN)，直接回傳空字串
        if not isinstance(text, str):
            return ""
        
        # 依序執行架構書定義的 Pipeline
        text = self._decode_url(text)
        text = self._decode_base64(text)
        text = self._clean_html(text)
        text = self._normalize_spaces(text)
        
        return text

    def _decode_url(self, text: str) -> str:
        """[內部方法] 尋找並解碼 URL Encoding 字串"""
        def replace_url(match):
            # urllib.parse.unquote 負責將 %xx 轉回明文
            return urllib.parse.unquote(match.group(0))
        return self.url_enc_pattern.sub(replace_url, text)

    def _decode_base64(self, text: str) -> str:
        """[內部方法] 透過 Regex 尋找 Base64 特徵並嘗試解碼"""
        def replace_b64(match):
            b64_str = match.group(0)
            try:
                # 嘗試進行 Base64 解碼
                decoded_bytes = base64.b64decode(b64_str)
                # 確保解碼出來的是有效的 UTF-8 字串
                decoded_text = decoded_bytes.decode('utf-8')
                return decoded_text
            except Exception:
                # [邊界條件處理] 如果解碼失敗（假陽性），則保留原始字串不替換
                return b64_str
                
        return self.base64_pattern.sub(replace_b64, text)

    def _clean_html(self, text: str) -> str:
        """[內部方法] 移除所有 HTML 標籤"""
        # 將標籤替換為空白，避免標籤前後的文字黏在一起 (例如 <p>Hello</p>World -> Hello World)
        return self.html_pattern.sub(' ', text)

    def _normalize_spaces(self, text: str) -> str:
        """[內部方法] 移除多餘空白、換行，並執行 strip()"""
        # \s+ 會匹配一個或多個空白、換行符號 (\n) 或 Tab (\t)
        return re.sub(r'\s+', ' ', text).strip()

