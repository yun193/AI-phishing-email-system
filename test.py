import zipfile, pandas as pd, os

dataset_dir = './Dataset'
files = sorted([f for f in os.listdir(dataset_dir) if f.endswith('.csv.zip')])

total_sub = 0
for f in files:
    path = os.path.join(dataset_dir, f)
    with zipfile.ZipFile(path, 'r') as z:
        csv_name = [x for x in z.namelist() if x.endswith('.csv')][0]
        df = pd.read_csv(z.open(csv_name))
        print(f"{f:<45} {len(df):>8} 筆  欄位: {list(df.columns)}")
        if f != 'all_phishing_email_dataset.csv.zip':
            total_sub += len(df)

print(f"\n6 個子資料集合計: {total_sub} 筆")
