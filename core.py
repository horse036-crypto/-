import requests
import pandas as pd
import time
import os
import urllib3 # 1. 匯入這個模組

# 2. 關閉「不安全連線」的警告訊息，讓輸出畫面比較乾淨
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 工具與爬蟲函式
# ==========================================

def convert_date(date_str):
    try:
        if '/' not in date_str: return date_str
        year, month, day = date_str.split('/')
        return f"{int(year) + 1911}-{month}-{day}"
    except:
        return date_str

def get_stock_price_monthly(stock_no, date):
    print(f"正在抓取 {stock_no} 在 {date} 的月股價資訊...")
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date}&stockNo={stock_no}"
    try:
        time.sleep(3)
        # 3. 這裡加入了 verify=False
        res = requests.get(url, verify=False)
        data = res.json()
        
        if data['stat'] == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            df['日期'] = df['日期'].apply(convert_date)
            cols_to_fix = ['成交股數', '成交金額', '開盤價', '最高價', '最低價', '收盤價']
            for col in cols_to_fix:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce')
            return df
        return None
    except Exception as e:
        print(f"錯誤: {e}")
        return None

def get_market_fundamentals(date):
    print(f"正在抓取 {date} 全市場基本面數據...")
    url = f"https://www.twse.com.tw/exchangeReport/BWIBBU_d?response=json&date={date}&selectType=ALL"
    try:
        time.sleep(3)
        # 4. 這裡也加入了 verify=False
        res = requests.get(url, verify=False)
        data = res.json()
        
        if data['stat'] == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            return df
        return None
    except Exception as e:
        print(f"錯誤: {e}")
        return None

# ==========================================
# 主程式執行區
# ==========================================

if __name__ == "__main__":
    stock_code = "2330"      
    month_date = "20240201" 
    day_date = "20240205"   

    output_folder = "stock_data"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"建立資料夾: {output_folder}")

    # --- 1. 抓取並儲存個股股價 ---
    df_price = get_stock_price_monthly(stock_code, month_date)
    
    if df_price is not None:
        filename = f"{output_folder}/stock_price_{stock_code}_{month_date[:6]}.csv"
        df_price.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✅ [成功] 股價資料已存檔至: {filename}")
    else:
        print("❌ 股價資料抓取失敗")

    # --- 2. 抓取並儲存全市場基本面 ---
    df_fund = get_market_fundamentals(day_date)
    
    if df_fund is not None:
        filename = f"{output_folder}/market_fundamentals_{day_date}.csv"
        df_fund.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✅ [成功] 基本面資料已存檔至: {filename}")
    else:
        print("❌ 基本面資料抓取失敗")

    print("\n執行完畢！請檢查您的資料夾。")