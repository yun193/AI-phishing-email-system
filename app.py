import streamlit as st
import traceback
import pandas as pd
import re

def load_modules():
    """載入所需的模組，符合 PhishingPredictor 類別設計"""
    import os
    from src.predictor import PhishingPredictor
    from decoder import PhishingDecoder

    try:
        predictor = PhishingPredictor(model_path="models/pipeline.pkl")
        st.sidebar.success("✅ AI 模型運作中 (Model Active)")
        return PhishingDecoder, predictor
    except Exception as e:
        error_msg = f"無法載入模型或預測器: {str(e)}\n\n{traceback.format_exc()}"
        st.sidebar.error("❌ 模型載入失敗")
        st.error(error_msg)
        return None, None

def render_single_result(cleaned_text: str, prediction_result: dict, raw_payload: str):
    """渲染單筆推論結果與解碼日誌"""
    st.subheader("分析結果 (Analysis Results)")
    
    if "error" in prediction_result:
         st.error(f"推論過程發生錯誤: {prediction_result['error']}")
         return

    label = prediction_result.get("label", "Unknown").capitalize()
    probability = prediction_result.get("confidence", 0.0)
    
    # 呈現推論結果
    col1, col2 = st.columns(2)
    with col1:
        if label == "Phishing" or label == "Negative": 
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
    """剖析上傳的 .txt 檔案內容，提取測試樣本與預期標籤"""
    payloads = []
    # 模式：1. [標籤] 內容
    pattern = r'(\d+\.\s+\[(.*?)\](.*?)(?=\n\d+\.\s+\[|$))'
    matches = re.findall(pattern, file_content, re.DOTALL)
    
    for match in matches:
        full_match, label_str, content = match
        ground_truth = "Safe" if "正常" in label_str or "Safe" in label_str else "Phishing"
        payloads.append({
            "content": content.strip(),
            "ground_truth": ground_truth,
            "original_label": label_str
        })
            
    return payloads

def render_batch_report(payload_data: list, decoder, predictor):
    """執行批量分析並以 DataFrame 呈現結果，包含準確率統計"""
    st.subheader(f"批量測試報告 (共 {len(payload_data)} 筆)")
    
    results = []
    progress_bar = st.progress(0)
    correct_count = 0
    
    for idx, item in enumerate(payload_data, 1):
        payload = item["content"]
        ground_truth = item["ground_truth"]
        
        if len(payload) > 20000:
            results.append({
                "ID": idx,
                "Ground Truth": ground_truth,
                "Prediction": "Error (Length > 20000)",
                "Match": "❌",
                "Probability": "-",
            })
            continue
            
        try:
            cleaned_text = decoder.process_text(payload)
            prediction_result = predictor.predict(cleaned_text)
            
            if "error" in prediction_result:
                raise ValueError(prediction_result["error"])
                
            label = prediction_result.get("label", "Unknown").capitalize()
            if label == "Negative": label = "Phishing"
            elif label == "Positive" or label == "Safe": label = "Safe"
                
            prob = prediction_result.get("confidence", 0.0)
            is_match = label == ground_truth
            if is_match: correct_count += 1
            
            results.append({
                "ID": idx,
                "Ground Truth": ground_truth,
                "Prediction": label,
                "Match": "✅" if is_match else "❌",
                "Probability": f"{prob:.2%}",
                "Cleaned Snippet": cleaned_text[:50] + "..." if len(cleaned_text) > 50 else cleaned_text
            })
            
        except Exception as e:
            results.append({
                "ID": idx,
                "Ground Truth": ground_truth,
                "Prediction": f"Error ({str(e)})",
                "Match": "N/A",
                "Probability": "-",
                "Cleaned Snippet": "-"
            })
            
        progress_bar.progress(idx / len(payload_data))
        
    if results:
        # 顯示統計數據
        accuracy = correct_count / len(payload_data)
        st.metric("整體準確率 (Accuracy)", f"{accuracy:.2%}")
        
        df = pd.DataFrame(results)
        
        def highlight_match(row):
            if row['Match'] == '❌':
                return ['background-color: #ffcccc; color: #900'] * len(row)
            elif row['Match'] == '✅':
                return ['background-color: #ccffcc; color: #090'] * len(row)
            return [''] * len(row)
            
        styled_df = df.style.apply(highlight_match, axis=1)
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("無法從檔案中解析出任何有效內容。")

def main():
    st.set_page_config(page_title="AI 釣魚郵件偵測系統", page_icon="🛡️", layout="wide")
    
    st.title("🛡️ AI 釣魚郵件偵測與解碼系統")
    st.markdown("""
    本系統具備嚴格的邊界防護與零猜測原則。請選擇單筆輸入或上傳檔案進行批量測試：
    """)
    
    PhishingDecoder, predictor = load_modules()
    
    if PhishingDecoder is None or predictor is None:
        st.stop() # 模組載入失敗，阻斷執行
        
    decoder = PhishingDecoder()

    # 建立分頁標籤
    tab1, tab2 = st.tabs(["📝 單筆分析 (Single Analysis)", "📂 批量測試報告 (Batch Test)"])
    
    # --- Tab 1: 單筆分析 ---
    with tab1:
        payload = st.text_area("輸入郵件文本 (Raw Email Text)", height=250, 
                               help="請貼上包含可疑連結、Base64 或 HTML 標籤的內容。最大限制 20000 字元。")
        
        if st.button("🚀 開始分析 (Analyze)", type="primary"):
            if not payload or not payload.strip():
                st.warning("請輸入有效的郵件文本。")
            elif len(payload) > 20000:
                st.error(f"錯誤：輸入文本超過長度上限 (目前長度: {len(payload)} 字元，上限: 20000 字元)。系統已阻斷該請求。")
            else:
                with st.spinner("系統正在進行深度解碼與威脅推論..."):
                    try:
                        cleaned_text = decoder.process_text(payload)
                        if not cleaned_text:
                            st.warning("清洗後文本為空。無法進行後續推論。")
                        else:
                            prediction_result = predictor.predict(cleaned_text)
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
                            render_batch_report(payload_list, decoder, predictor)
                        else:
                            st.warning("檔案中找不到符合格式的測試樣本。")
                    except Exception as e:
                        st.error(f"處理檔案時發生錯誤: {str(e)}")

if __name__ == "__main__":
    main()
