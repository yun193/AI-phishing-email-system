import re
import base64
import urllib.parse

class PhishingDecoder:
    """
    資料前處理與邏輯解碼層 (Data Processing & Decoding Layer)
    具備遞迴解碼、特徵提取 (Tokenization) 與詳細日誌記錄功能。
    """
    def __init__(self):
        # 匹配 URL Encoding (例如 %20, %3D)
        self.url_enc_pattern = re.compile(r'(?:%[0-9a-fA-F]{2})+')
        
        # 匹配 Base64 (長度至少 12，結尾可能有 =)
        self.base64_pattern = re.compile(r'(?:[A-Za-z0-9+/]{4}){3,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?')
        
        # 匹配 <script> 標籤及其內容 (忽略大小寫)
        self.script_pattern = re.compile(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', re.IGNORECASE)
        
        # 匹配基礎 HTML 標籤
        self.html_pattern = re.compile(r'<[^>]+>')
        
        # 匹配 IPv4 格式
        self.ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        
        # 匹配一般網址 (用於檢查長度)
        self.url_pattern = re.compile(r'(https?://[^\s<>"]+|www\.[^\s<>"]+)')

    def process_text(self, text: str) -> tuple[str, list]:
        """
        輸入原始文本，輸出 (清理後的文本, 解碼日誌)
        """
        log = []
        if not isinstance(text, str):
            return "", ["Error: 輸入非字串格式。"]

        log.append("=== 開始處理郵件文本 ===")

        # 1. 移除腳本代碼 (通常直接包含惡意 payload，需優先清除)
        if self.script_pattern.search(text):
            text = self.script_pattern.sub(' ', text)
            log.append("[清理] 已移除 <script> 標籤與內部代碼。")

        # 2. 遞迴解碼 (Recursive Decoding)
        max_depth = 10  # 設定最大深度，防止惡意無限迴圈
        depth = 0
        
        while depth < max_depth:
            original_text = text
            
            # 執行 URL 解碼
            text, url_decoded = self._decode_url(text)
            if url_decoded:
                log.append(f"[解碼] 深度 depth+1: 成功還原 URL Encoding。")
            
            # 執行 Base64 解碼
            text, b64_decoded = self._decode_base64(text)
            if b64_decoded:
                log.append(f"[解碼] 深度 depth+1: 成功還原 Base64 字串。")

            # 若此輪解碼後字串無變化，代表已完全解碼，跳出迴圈
            if text == original_text:
                if depth > 0:
                    log.append(f"[狀態] 遞迴解碼完成，總深度: {depth}。")
                break
            
            depth += 1

        if depth == max_depth:
            log.append("[警告] 達到最大解碼深度 (10層)，可能存在防禦性迴圈混淆。")

        # 3. 基礎清洗：移除 HTML 標籤
        if self.html_pattern.search(text):
            text = self.html_pattern.sub(' ', text)
            log.append("[清理] 已移除基礎 HTML 標籤。")

        # 4. 惡意特徵提取 (Tokenization)
        text, token_log = self._tokenize_features(text)
        log.extend(token_log)

        # 5. 空白字元正規化
        text = self._normalize_spaces(text)
        log.append("[清理] 完成多餘空白字元與換行正規化。")
        log.append("=== 處理結束 ===")

        return text, log

    def _decode_url(self, text: str) -> tuple[str, bool]:
        """執行 URL 解碼並回傳是否發生變動"""
        has_decoded = False
        def replace_url(match):
            nonlocal has_decoded
            original = match.group(0)
            unquoted = urllib.parse.unquote(original)
            if unquoted != original:
                has_decoded = True
            return unquoted
            
        new_text = self.url_enc_pattern.sub(replace_url, text)
        return new_text, has_decoded

    def _decode_base64(self, text: str) -> tuple[str, bool]:
        """執行 Base64 解碼並回傳是否發生變動"""
        has_decoded = False
        def replace_b64(match):
            nonlocal has_decoded
            b64_str = match.group(0)
            try:
                decoded_bytes = base64.b64decode(b64_str)
                decoded_text = decoded_bytes.decode('utf-8')
                # 確保解碼出來的是可讀字元且具備一定長度，避免假陽性
                if decoded_text.isprintable() and len(decoded_text) > 2:
                    has_decoded = True
                    return decoded_text
            except Exception:
                pass
            return b64_str
            
        new_text = self.base64_pattern.sub(replace_b64, text)
        return new_text, has_decoded

    def _tokenize_features(self, text: str) -> tuple[str, list]:
        """特徵提取：替換 IP 與異常網址為 Token"""
        log = []
        
        # 替換直接使用 IP 的情況
        def replace_ip(match):
            log.append(f"[特徵] 偵測並替換直接 IP 地址: {match.group(0)} -> [SUSPICIOUS_IP]")
            return "[SUSPICIOUS_IP]"
        text = self.ip_pattern.sub(replace_ip, text)

        # 替換異常長度的網址
        def replace_url(match):
            url = match.group(0)
            # 判定邏輯：網址長度超過 60 字元即視為異常 (可依需求調整)
            if len(url) > 60:
                log.append(f"[特徵] 偵測並替換異常超長網址 (長度 {len(url)}) -> [EVIL_URL]")
                return "[EVIL_URL]"
            return url
        text = self.url_pattern.sub(replace_url, text)
        
        return text, log

    def _normalize_spaces(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()


# ==========================================
# 測試區塊
# ==========================================
if __name__ == "__main__":
    decoder = PhishingDecoder()
    
    # 測試案例：包含雙層編碼 (Base64 裡面包著 URL Encoding)、Script 與 IP 網址
    sample_raw = """
    <html>
        <body>
            <p>Urgent Action Required!</p>
            <script>window.location.href="http://bad.com";</script>
            Hidden Link: Q2xpY2s6ICU2OCU3NCU3NCU3MCUzQSUyRiUyRiUzMSUzOSUzMiUyRSUzMSUzNiUzOCUyRSUzMSUyRSUzMSUzMCUzMCUyRiU3NiU2NSU3MiU3OSU1RiU2QyU2RiU2RSU2NyU1RiU2RCU2MSU2QyU2OSU2MyU2OSU2RiU3NSU3MyU1RiU3MCU2MSU3OSU2QyU2RiU2MSU2NCU1RiU3NCU2OCU2MSU3NCU1RiU2MiU3OSU3MCU2MSU3MyU3MyU2NSU3MyU1RiU2NiU2OSU2QyU3NCU2NSU3MiU3Mw==
        </body>
    </html>
    """
    
    clean_text, process_log = decoder.process_text(sample_raw)
    
    print("\n【原始文本】")
    print(sample_raw.strip())
    
    print("\n【處理日誌】")
    for entry in process_log:
        print(f" > {entry}")
        
    print("\n【最終輸出 (Cleaned Text)】")
    print(clean_text)