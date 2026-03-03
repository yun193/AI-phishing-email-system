"""
train.py - AI 釣魚郵件偵測系統：模型訓練模組

功能：載入已清洗的 CSV 資料集（支援 .csv.zip）、切分訓練/驗證集、
使用 TF-IDF + Logistic Regression 進行訓練，產出混淆矩陣視覺化圖表、
效能評估報告，並將模型匯出為 .pkl 檔案。

使用方式 (CLI)：
    python train.py --data_path ./Dataset/all_phishing_email_dataset.csv.zip \
                    --text_col text_combined --label_col label

使用方式 (Python 匯入)：
    from train import train_model, evaluate_model
    pipeline_model, label2id = train_model(data_path="./Dataset/all_phishing_email_dataset.csv.zip")
    metrics = evaluate_model(pipeline_model, X_test, y_test, label2id)
"""

import argparse
import json
import os
import random
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import matplotlib
matplotlib.use("Agg")  # 無 GUI 環境下使用非互動式後端
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

# ─── 常數定義 ───────────────────────────────────────────────────
SEED = 42
DEFAULT_OUTPUT_DIR = "./models"

# 標籤對應
LABEL2ID = {"safe": 0, "phishing": 1}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}

# 數值標籤的預設顯示名稱（當資料集標籤為 0/1 數值時自動套用）
NUMERIC_LABEL_DISPLAY = {0: "Safe", 1: "Phishing"}


def set_seed(seed: int = SEED) -> None:
    """設定隨機種子以確保可重現性"""
    random.seed(seed)
    np.random.seed(seed)


def load_and_split_data(
    data_path: str,
    text_col: str = "text",
    label_col: str = "label",
    test_size: float = 0.2,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, Dict[str, int]]:
    """
    載入 CSV 資料集（支援 .csv.zip）並按比例切分為訓練集與驗證集。

    Args:
        data_path: CSV 檔案路徑（支援 .csv 或 .csv.zip）
        text_col: 文本欄位名稱
        label_col: 標籤欄位名稱
        test_size: 驗證集佔比（預設 0.2，即 8:2 切分）

    Returns:
        (X_train, X_test, y_train, y_test, label2id_mapping)
    """
    print(f"📂 載入資料集：{data_path}")

    # 支援 .csv.zip 格式
    if data_path.endswith(".zip"):
        with zipfile.ZipFile(data_path, "r") as z:
            csv_files = [f for f in z.namelist() if f.endswith(".csv")]
            if not csv_files:
                raise ValueError(f"ZIP 檔案中找不到 CSV 檔案：{z.namelist()}")
            csv_name = csv_files[0]
            print(f"  📦 從 ZIP 中讀取：{csv_name}")
            with z.open(csv_name) as csv_file:
                df = pd.read_csv(csv_file)
    else:
        df = pd.read_csv(data_path)

    print(f"  ├── 總筆數：{len(df)}")
    print(f"  ├── 文本欄位：{text_col}")
    print(f"  └── 標籤欄位：{label_col}")

    # 確認欄位存在
    if text_col not in df.columns:
        raise ValueError(f"找不到文本欄位 '{text_col}'，可用欄位：{list(df.columns)}")
    if label_col not in df.columns:
        # 嘗試自動偵測常見的標籤欄位名稱
        candidates = ["label", "Label", "is_phishing", "class", "Class", "target", "spam"]
        found: str = ""
        for c in candidates:
            if c in df.columns:
                found = c
                break
        if found:
            print(f"  ⚠️  找不到 '{label_col}'，自動使用偵測到的欄位：'{found}'")
            label_col = found
        else:
            raise ValueError(f"找不到標籤欄位 '{label_col}'，可用欄位：{list(df.columns)}")

    # 移除空值
    original_len = len(df)
    df = df.dropna(subset=[text_col, label_col])
    # 確保文本欄位為字串類型
    df[text_col] = df[text_col].astype(str)
    if len(df) < original_len:
        print(f"  ⚠️  移除了 {original_len - len(df)} 筆含空值的資料")

    # 標籤處理：自動偵測標籤類型並轉換為數值
    unique_labels = sorted(df[label_col].unique())
    print(f"  📊 標籤分佈：{dict(df[label_col].value_counts())}")

    if df[label_col].dtype == object:
        # 文字標籤 → 數值映射
        label2id = {label: idx for idx, label in enumerate(unique_labels)}
        print(f"  🏷️  標籤映射：{label2id}")
        df["label_id"] = df[label_col].map(label2id)
    else:
        # 已經是數值標籤 → 套用可讀名稱（0→Safe, 1→Phishing）
        label2id = {
            NUMERIC_LABEL_DISPLAY.get(int(label), str(int(label))): int(label)
            for label in unique_labels
        }
        print(f"  🏷️  標籤映射：{label2id}")
        df["label_id"] = df[label_col].astype(int)

    X = df[text_col]
    y = df["label_id"]

    # 8:2 切分
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=SEED, stratify=y
    )
    print(f"  ✂️  切分結果：訓練集 {len(X_train)} 筆 / 驗證集 {len(X_test)} 筆")

    return X_train, X_test, y_train, y_test, label2id


def build_pipeline(max_features: int = 50000, C: float = 1.0) -> Pipeline:
    """
    建立 TF-IDF + Logistic Regression 的 sklearn Pipeline。

    Args:
        max_features: TF-IDF 最大特徵數
        C: Logistic Regression 正則化參數

    Returns:
        sklearn Pipeline 物件
    """
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),      # Unigram + Bigram
            stop_words="english",
            sublinear_tf=True,       # 使用 log(tf) 降低高頻詞影響
            min_df=2,                # 至少出現 2 次
            max_df=0.95,             # 排除出現在 95% 以上文件中的詞
        )),
        ("classifier", LogisticRegression(
            C=C,
            max_iter=1000,
            random_state=SEED,
            solver="lbfgs",
            n_jobs=-1,               # 使用所有 CPU 核心
        )),
    ])
    return pipeline


def train_model(
    data_path: str,
    text_col: str = "text",
    label_col: str = "label",
    output_dir: str = DEFAULT_OUTPUT_DIR,
    test_size: float = 0.2,
    max_features: int = 50000,
    C: float = 1.0,
) -> Tuple[Pipeline, pd.Series, pd.Series, Dict[str, int]]:
    """
    執行完整的模型訓練流程。

    Args:
        data_path: CSV 資料集路徑（支援 .csv 或 .csv.zip）
        text_col: 文本欄位名稱
        label_col: 標籤欄位名稱
        output_dir: 模型輸出目錄
        test_size: 驗證集佔比
        max_features: TF-IDF 最大特徵數
        C: Logistic Regression 正則化參數

    Returns:
        (pipeline, X_test, y_test, label2id) - 可供後續評估使用
    """
    set_seed(SEED)

    # 1. 資料載入與切分
    X_train, X_test, y_train, y_test, label2id = load_and_split_data(
        data_path, text_col, label_col, test_size
    )

    # 2. 建立並訓練 Pipeline
    print(f"\n🤖 建立模型：TF-IDF + Logistic Regression")
    print(f"  ├── TF-IDF max_features: {max_features}")
    print(f"  └── LogisticRegression C: {C}")

    pipeline = build_pipeline(max_features=max_features, C=C)

    print(f"\n🚀 開始訓練...")
    print("=" * 60)
    pipeline.fit(X_train, y_train)
    print("=" * 60)
    print("✅ 訓練完成！")

    # 3. 儲存模型為 .pkl
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    model_path = os.path.join(output_dir, "model.pkl")
    joblib.dump(pipeline, model_path)
    print(f"💾 模型已儲存至：{model_path}")

    # 同時儲存 label2id 映射
    label_map_path = os.path.join(output_dir, "label_map.json")
    with open(label_map_path, "w", encoding="utf-8") as f:
        json.dump(label2id, f, indent=2, ensure_ascii=False)
    print(f"🏷️  標籤映射已儲存至：{label_map_path}")

    return pipeline, X_test, y_test, label2id


def evaluate_model(
    pipeline: Pipeline,
    X_test: pd.Series,
    y_test: pd.Series,
    label2id: Dict[str, int],
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Any]:
    """
    對驗證集執行評估，產出完整的效能報告與混淆矩陣視覺化。

    Args:
        pipeline: 已訓練完成的 Pipeline 物件
        X_test: 測試集文本
        y_test: 測試集標籤
        label2id: 標籤映射字典
        output_dir: 報告輸出目錄

    Returns:
        包含 F1, Precision, Recall, FPR, Confusion Matrix 的字典
    """
    print("\n📊 執行模型評估...")

    # 取得預測結果
    predictions = pipeline.predict(X_test)
    labels = y_test.values

    # 判斷是否為二分類
    is_binary = len(label2id) == 2
    average = "binary" if is_binary else "weighted"
    pos_label = 1 if is_binary else None

    # 計算指標
    f1 = round(f1_score(labels, predictions, average=average, zero_division=0), 4)
    precision = round(precision_score(labels, predictions, average=average, zero_division=0), 4)
    recall = round(recall_score(labels, predictions, average=average, zero_division=0), 4)

    # 計算 Confusion Matrix
    id2label = {v: k for k, v in label2id.items()}
    display_labels = [id2label[i] for i in sorted(id2label.keys())]
    cm = confusion_matrix(labels, predictions)

    # 計算 FPR（僅二分類）
    if is_binary and cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        fpr = round(fp / (fp + tn), 4) if (fp + tn) > 0 else 0.0
    else:
        tn = fp = fn = tp = 0
        fpr = 0.0

    # ─── 混淆矩陣視覺化 ───────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=display_labels)
    disp.plot(ax=ax, cmap="Blues", values_format="d")
    ax.set_title("Confusion Matrix - Phishing Email Detection", fontsize=14, fontweight="bold")
    ax.set_xlabel("Predicted Label", fontsize=12)
    ax.set_ylabel("True Label", fontsize=12)
    plt.tight_layout()

    # 儲存混淆矩陣圖
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    cm_path = os.path.join(output_dir, "confusion_matrix.png")
    fig.savefig(cm_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"📊 混淆矩陣圖已儲存至：{cm_path}")

    # 組裝報告
    report = {
        "f1": f1,
        "precision": precision,
        "recall": recall,
        "fpr": fpr,
        "confusion_matrix": cm.tolist(),
        "display_labels": display_labels,
        "eval_samples": len(labels),
        "model_type": "TF-IDF + Logistic Regression",
    }

    if is_binary:
        report["confusion_matrix_labels"] = {
            "TN": int(tn), "FP": int(fp),
            "FN": int(fn), "TP": int(tp),
        }

    # 列印報告
    print("\n" + "=" * 50)
    print("📋 效能評估報告 (Evaluation Report)")
    print("=" * 50)
    print(f"  模型類型   : TF-IDF + Logistic Regression")
    print(f"  F1-Score   : {f1}")
    print(f"  Precision  : {precision}")
    print(f"  Recall     : {recall}")
    if is_binary:
        print(f"  FPR        : {fpr}")
    print(f"  驗證樣本數 : {len(labels)}")
    print(f"\n  Confusion Matrix:")
    if is_binary:
        print(f"    TN={tn}  FP={fp}")
        print(f"    FN={fn}  TP={tp}")
    else:
        print(f"    {cm}")

    # 印出完整分類報告
    print(f"\n  Classification Report:")
    print(classification_report(labels, predictions, target_names=display_labels, zero_division=0))
    print("=" * 50)

    # 儲存為 JSON
    report_path = os.path.join(output_dir, "eval_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"📄 報告已儲存至：{report_path}")

    return report


def parse_args() -> argparse.Namespace:
    """解析命令列參數"""
    parser = argparse.ArgumentParser(
        description="AI 釣魚郵件偵測系統 - 模型訓練腳本（TF-IDF + Logistic Regression）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data_path", type=str, required=True,
        help="已清洗的 CSV 資料集路徑（支援 .csv 或 .csv.zip）",
    )
    parser.add_argument(
        "--text_col", type=str, default="text",
        help="CSV 中文本欄位的名稱",
    )
    parser.add_argument(
        "--label_col", type=str, default="label",
        help="CSV 中標籤欄位的名稱",
    )
    parser.add_argument(
        "--output_dir", type=str, default=DEFAULT_OUTPUT_DIR,
        help="模型與報告的儲存目錄",
    )
    parser.add_argument(
        "--test_size", type=float, default=0.2,
        help="驗證集佔比 (8:2 切分)",
    )
    parser.add_argument(
        "--max_features", type=int, default=50000,
        help="TF-IDF 最大特徵數",
    )
    parser.add_argument(
        "--C", type=float, default=1.0,
        help="Logistic Regression 正則化參數（值越大正則化越弱）",
    )
    return parser.parse_args()


# ─── 主程式入口 ─────────────────────────────────────────────────
if __name__ == "__main__":
    args = parse_args()

    print("🛡️  AI 釣魚郵件偵測系統 - 模型訓練")
    print("=" * 60)
    print(f"  模型架構   : TF-IDF + Logistic Regression")
    print(f"  資料集     : {args.data_path}")
    print(f"  輸出目錄   : {args.output_dir}")
    print(f"  Max Features: {args.max_features}")
    print(f"  C (正則化)  : {args.C}")
    print(f"  Test Size   : {args.test_size}")
    print("=" * 60)

    # 執行訓練
    pipeline, X_test, y_test, label2id = train_model(
        data_path=args.data_path,
        text_col=args.text_col,
        label_col=args.label_col,
        output_dir=args.output_dir,
        test_size=args.test_size,
        max_features=args.max_features,
        C=args.C,
    )

    # 執行評估
    metrics = evaluate_model(
        pipeline, X_test, y_test, label2id,
        output_dir=args.output_dir,
    )

    print("\n🎉 全部完成！模型已準備就緒。")
    print(f"   模型檔案   : {args.output_dir}/model.pkl")
    print(f"   混淆矩陣圖 : {args.output_dir}/confusion_matrix.png")
    print(f"   評估報告   : {args.output_dir}/eval_report.json")
    print(f"   標籤映射   : {args.output_dir}/label_map.json")
    print(f"\n   下一步：將 inference.py 中的模型路徑指向 '{args.output_dir}/model.pkl' 即可使用。")
