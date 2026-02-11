import requests
import pandas as pd
import time
import urllib3

# 關閉討厭的 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_stock_data():
    stock_code = "2330"  # 台積電
    print(f"🚀 開始抓取 {stock_code} 過去 12 個月的股價...")
    
    # 自動產生過去 12 個月的日期 (每月 1 號)
    date_list = pd.date_range(end=pd.Timestamp.now(), periods=12, freq='MS')
    all_data = []

    for date_item in date_list:
        date_str = date_item.strftime("%Y%m%d")
        print(f"  -> 正在抓取: {date_str} ...")
        
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stock_code}"
        
        try:
            # 關鍵：verify=False 避開憑證錯誤
            res = requests.get(url, verify=False)
            data = res.json()
            
            if data['stat'] == 'OK':
                df = pd.DataFrame(data['data'], columns=data['fields'])
                # 簡單清洗：民國轉西元
                df['日期'] = df['日期'].apply(lambda x: str(int(x.split('/')[0]) + 1911) + '-' + x.split('/')[1] + '-' + x.split('/')[2])
                # 清洗：移除逗號
                for col in ['收盤價', '開盤價', '最高價', '最低價', '成交股數']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce')
                all_data.append(df)
            
            time.sleep(3) # 休息 3 秒，很重要！
            
        except Exception as e:
            print(f"  ⚠️ 錯誤: {e}")

    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        # 存檔！這就是 app.py 在找的檔案
        filename = f"stock_history_{stock_code}.csv"
        final_df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ 成功！檔案已建立: {filename}")
        print("👉 現在你可以重新整理你的網頁了！")
    else:
        print("❌ 抓取失敗，沒有資料。")

if __name__ == "__main__":
    get_stock_data()