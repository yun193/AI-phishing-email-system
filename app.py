import streamlit as st
import traceback
import pandas as pd
import re

def load_modules():
    """載入所需的模組，並將錯誤捕獲以符合安全與不猜測原則"""
    try:
        from decoder import PhishingDecoder
        from inference import predict
        return PhishingDecoder, predict
    except Exception as e:
        error_msg = f"無法載入核心模組: {str(e)}\n\n{traceback.format_exc()}"
        st.error(error_msg)
        return None, None

def render_single_result(cleaned_text: str, prediction_result: dict, raw_payload: str):
    """渲染單筆推論結果與解碼日誌"""
    st.subheader("分析結果 (Analysis Results)")
    
    if "error" in prediction_result:
         st.error(f"推論過程發生錯誤: {prediction_result['error']}")
         return

    label = prediction_result.get("label", "Unknown")
    probability = prediction_result.get("probability", 0.0)
    
    # 呈現推論結果
    col1, col2 = st.columns(2)
    with col1:
        if label == "Phishing" or label == "NEGATIVE": 
            st.error(f"⚠️ 威脅判定: 釣魚郵件 (Phishing)")
        else:
            st.success(f"✅ 威脅判定: 安全 (Safe)")
            
    with col2:
        st.info(f"📊 信心機率: {probability:.2%}")
        
    st.markdown("---")
    
    # 呈現解碼日誌對比
    st.subheader("解碼與清洗日誌 (Decoding & Cleaning Trace)")
    st.write("系統不對解析失敗的特徵進行猜測，以下為真實還原結果：")
    
    log_col1, log_col2 = st.columns(2)
    with log_col1:
        st.markdown("**原始輸入 (Raw Payload)**")
        st.code(raw_payload, language="text")
        
    with log_col2:
        st.markdown("**清洗後明文 (Cleaned Text)**")
        st.code(cleaned_text, language="text")

def parse_batch_file(file_content: str) -> list:
    """剖析上傳的 .txt 檔案內容，提取測試樣本"""
    payloads = []
    # 利用正則切開如 "1. [正常]...", "2. [釣魚..." 這樣的結構
    sections = re.split(r'\n\d+\.\s+\[.*?\]', file_content)
    
    for section in sections:
        payload_text = section.strip()
        if payload_text:
            payloads.append(payload_text)
            
    return payloads

def render_batch_report(payloads: list, decoder, predict):
    """執行批量分析並以 DataFrame 呈現結果"""
    st.subheader(f"批量測試報告 (共 {len(payloads)} 筆)")
    
    results = []
    progress_bar = st.progress(0)
    
    for idx, payload in enumerate(payloads, 1):
        # 防護：超過 5000 字元
        if len(payload) > 5000:
            results.append({
                "ID": idx,
                "Prediction": "Error (Length > 5000)",
                "Probability": "-",
                "Raw Snippet": payload[:50] + "...",
                "Cleaned Snippet": "-"
            })
            continue
            
        try:
            cleaned_text = decoder.process_text(payload)
            if not cleaned_text:
                raise ValueError("清洗後文本為空")
                
            prediction_result = predict(cleaned_text)
            
            if "error" in prediction_result:
                raise ValueError(prediction_result["error"])
                
            label = prediction_result.get("label", "Unknown")
            # 兼容 MVP
            if label == "NEGATIVE": label = "Phishing"
            elif label == "POSITIVE": label = "Safe"
                
            prob = prediction_result.get("probability", 0.0)
            
            results.append({
                "ID": idx,
                "Prediction": label,
                "Probability": f"{prob:.2%}",
                "Raw Snippet": payload[:50] + "..." if len(payload) > 50 else payload,
                "Cleaned Snippet": cleaned_text[:50] + "..." if len(cleaned_text) > 50 else cleaned_text
            })
            
        except Exception as e:
            results.append({
                "ID": idx,
                "Prediction": f"Error ({str(e)})",
                "Probability": "-",
                "Raw Snippet": payload[:50] + "...",
                "Cleaned Snippet": "-"
            })
            
        # 更新進度條
        progress_bar.progress(idx / len(payloads))
        
    # 呈現對應的 DataFrame
    if results:
        df = pd.DataFrame(results)
        
        # 套用簡單的顏色樣式 (給 Phishing 標上警告色)
        def highlight_phishing(row):
            if row['Prediction'] == 'Phishing':
                return ['background-color: #ffcccc; color: #900'] * len(row)
            elif row['Prediction'] == 'Safe':
                return ['background-color: #ccffcc; color: #090'] * len(row)
            return [''] * len(row)
            
        styled_df = df.style.apply(highlight_phishing, axis=1)
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("無法從檔案中解析出任何有效內容。")

def main():
    st.set_page_config(page_title="AI 釣魚郵件偵測系統", page_icon="🛡️", layout="wide")
    
    st.title("🛡️ AI 釣魚郵件偵測與解碼系統")
    st.markdown("""
    本系統具備嚴格的邊界防護與零猜測原則。請選擇單筆輸入或上傳檔案進行批量測試：
    """)
    
    PhishingDecoder, predict = load_modules()
    
    if PhishingDecoder is None or predict is None:
        st.stop() # 模組載入失敗，阻斷執行
        
    decoder = PhishingDecoder()

    # 建立分頁標籤
    tab1, tab2 = st.tabs(["📝 單筆分析 (Single Analysis)", "📂 批量測試報告 (Batch Test)"])
    
    # --- Tab 1: 單筆分析 ---
    with tab1:
        payload = st.text_area("輸入郵件文本 (Raw Email Text)", height=250, 
                               help="請貼上包含可疑連結、Base64 或 HTML 標籤的內容。最大限制 5000 字元。")
        
        if st.button("🚀 開始分析 (Analyze)", type="primary"):
            if not payload or not payload.strip():
                st.warning("請輸入有效的郵件文本。")
            elif len(payload) > 5000:
                st.error(f"錯誤：輸入文本超過長度上限 (目前長度: {len(payload)} 字元，上限: 5000 字元)。系統已阻斷該請求。")
            else:
                with st.spinner("系統正在進行深度解碼與威脅推論..."):
                    try:
                        cleaned_text = decoder.process_text(payload)
                        if not cleaned_text:
                            st.warning("清洗後文本為空。無法進行後續推論。")
                        else:
                            prediction_result = predict(cleaned_text)
                            render_single_result(cleaned_text, prediction_result, payload)
                    except Exception as e:
                        error_msg = f"系統處理過程中發生未預期例外: {str(e)}\n\n{traceback.format_exc()}"
                        st.error(error_msg)

    # --- Tab 2: 批量分析 ---
    with tab2:
        st.markdown("上傳包含多筆測試樣本的文字檔 (如 `test_payloads.txt`)，系統將自動套用防護邊界進行批量檢測。")
        uploaded_file = st.file_uploader("上傳測試樣本檔案", type=['txt'])
        
        if uploaded_file is not None:
            if st.button("📊 生成批量測試報告", type="primary"):
                with st.spinner("正在解析檔案與執行批量推論..."):
                    try:
                        # 讀取 bytes 並轉為 string
                        string_data = uploaded_file.getvalue().decode("utf-8")
                        payload_list = parse_batch_file(string_data)
                        
                        if payload_list:
                            render_batch_report(payload_list, decoder, predict)
                        else:
                            st.warning("檔案中找不到符合格式的測試樣本。")
                    except Exception as e:
                        st.error(f"處理檔案時發生錯誤: {str(e)}")

if __name__ == "__main__":
    main()
