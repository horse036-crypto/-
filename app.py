import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import yfinance as yf
import time
import urllib3
from deep_translator import GoogleTranslator

# 忽略 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. 設定網頁
# ==========================================
st.set_page_config(page_title="超級財報狗 (複刻版)", layout="wide")
st.title("🐶 超級財報狗 - 個股全方位分析")

# ==========================================
# 2. 功能 A: 抓取公司基本資料 (含翻譯)
# ==========================================
@st.cache_data(ttl=86400)
def get_company_profile_data():
    url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
    try:
        res = requests.get(url, verify=False)
        data = res.json()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        return None

def display_company_info(stock_code, df_all):
    company = df_all[df_all['公司代號'] == stock_code]
    info = {} 
    if not company.empty:
        info = company.iloc[0].to_dict()

    yf_ticker = yf.Ticker(f"{stock_code}.TW")
    try:
        yf_info = yf_ticker.info
    except:
        yf_info = {}

    summary = yf_info.get('longBusinessSummary', '暫無詳細描述')
    if summary != '暫無詳細描述' and len(summary) > 10:
        try:
            summary_to_translate = summary[:4500] 
            translated_text = GoogleTranslator(source='auto', target='zh-TW').translate(summary_to_translate)
            summary = translated_text
        except:
            pass

    with st.expander(f"🏢 {info.get('公司名稱', stock_code)} - 公司基本資料", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**董事長**：{info.get('董事長', 'N/A')}")
            st.write(f"**總經理**：{info.get('總經理', 'N/A')}")
            st.write(f"**發言人**：{info.get('發言人', 'N/A')}")
        with col2:
            st.write(f"**成立日期**：{info.get('成立日期', 'N/A')}")
            st.write(f"**上市日期**：{info.get('上市日期', 'N/A')}")
            cap = info.get('實收資本額', '0')
            st.write(f"**實收資本額**：{int(cap):,} 元" if cap.isdigit() else cap)
        with col3:
            st.write(f"**產業類別**：{info.get('產業別', yf_info.get('sector', 'N/A'))}")
            st.write(f"**網址**：[{info.get('網址', '#')}]({info.get('網址', '#')})")

        st.markdown("---")
        st.write(f"**📝 公司簡介 (自動翻譯)**：")
        st.info(summary)

# ==========================================
# 3. 功能 B: 抓股價
# ==========================================
@st.cache_data(ttl=3600)
def fetch_stock_history(stock_code):
    all_data = []
    date_list = pd.date_range(end=pd.Timestamp.now(), periods=3, freq='MS')
    for i, date_item in enumerate(date_list):
        date_str = date_item.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stock_code}"
        try:
            res = requests.get(url, verify=False)
            data = res.json()
            if data['stat'] == 'OK':
                df = pd.DataFrame(data['data'], columns=data['fields'])
                df['日期'] = df['日期'].apply(lambda x: str(int(x.split('/')[0]) + 1911) + '-' + x.split('/')[1] + '-' + x.split('/')[2])
                for col in ['收盤價', '開盤價', '最高價', '最低價', '成交股數']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce')
                all_data.append(df)
            time.sleep(0.5)
        except:
            pass
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return None

# ==========================================
# 4. 功能 C: 抓財報指標 + 歷史趨勢 (新功能!)
# ==========================================
def get_financial_analysis(stock_code):
    ticker = yf.Ticker(f"{stock_code}.TW")
    try:
        # 取得年度財報
        fin = ticker.financials
        bs = ticker.balance_sheet
        cf = ticker.cashflow
        
        if fin.empty: return None, None

        # --- 1. 計算最新指標 (跟之前一樣) ---
        last_fin = fin.iloc[:, 0]
        last_bs = bs.iloc[:, 0]
        last_cf = cf.iloc[:, 0]
        
        revenue = last_fin.get('Total Revenue', 0)
        net_income = last_fin.get('Net Income', 0)
        total_assets = last_bs.get('Total Assets', 0)
        total_liab = last_bs.get('Total Liabilities Net Minority Interest', 0)
        curr_assets = last_bs.get('Current Assets', 0)
        curr_liab = last_bs.get('Current Liabilities', 0)
        ocf = last_cf.get('Operating Cash Flow', 0)
        
        ratios = {}
        ratios['毛利率'] = (last_fin.get('Gross Profit', 0) / revenue * 100) if revenue else 0
        ratios['營業利益率'] = (last_fin.get('Operating Income', 0) / revenue * 100) if revenue else 0
        ratios['淨利率'] = (net_income / revenue * 100) if revenue else 0
        ratios['ROE'] = (net_income / (total_assets - total_liab) * 100) if (total_assets - total_liab) else 0
        ratios['流動比率'] = (curr_assets / curr_liab * 100) if curr_liab else 0
        ratios['負債比率'] = (total_liab / total_assets * 100) if total_assets else 0
        ratios['ROA'] = (net_income / total_assets * 100) if total_assets else 0
        ratios['現金流對淨利比'] = (ocf / net_income * 100) if net_income else 0

        # --- 2. 整理歷史趨勢數據 (為了畫圖) ---
        # 我們要把 DataFrame 轉置 (Transpose)，變成：年份在 X 軸，數值在 Y 軸
        # 抓取最近 4 年
        years = fin.columns[:4] 
        trend_data = []
        
        for date in years:
            year_str = str(date.year)
            rev = fin.loc['Total Revenue', date] if 'Total Revenue' in fin.index else 0
            # 嘗試抓取 EPS，如果沒有就抓淨利
            eps = fin.loc['Basic EPS', date] if 'Basic EPS' in fin.index else 0
            
            trend_data.append({
                '年份': year_str,
                '營收': rev,
                'EPS': eps
            })
            
        # 將 List 轉回 DataFrame 並按年份排序 (舊 -> 新)
        df_trend = pd.DataFrame(trend_data).sort_values('年份')
        
        return ratios, df_trend

    except Exception as e:
        print(f"Error: {e}")
        return None, None

# ==========================================
# 5. 主介面邏輯
# ==========================================
with st.sidebar:
    st.header("🔍 股票搜尋")
    stock_id = st.text_input("輸入股票代號", value="2330")
    st.caption("資料來源：台灣證交所 & Yahoo Finance")

if stock_id:
    with st.spinner('正在分析大數據...'):
        df_company_list = get_company_profile_data()
        ratios, df_trend = get_financial_analysis(stock_id) # 呼叫新函式
        df_price = fetch_stock_history(stock_id)

    # --- 1. 公司基本資料 ---
    if df_company_list is not None:
        display_company_info(stock_id, df_company_list)

    # --- 2. 股價走勢 ---
    if df_price is not None:
        df_price['日期'] = pd.to_datetime(df_price['日期'])
        df_price = df_price.sort_values('日期')
        st.subheader("📈 短期股價走勢")
        st.plotly_chart(px.line(df_price, x='日期', y='收盤價'), use_container_width=True)

    # --- 3. 關鍵指標與歷史趨勢 (重頭戲) ---
    st.subheader("📊 財務體質分析")
    
    if ratios:
        # 顯示最新指標
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("毛利率", f"{ratios['毛利率']:.2f}%")
        c2.metric("營業利益率", f"{ratios['營業利益率']:.2f}%")
        c3.metric("淨利率", f"{ratios['淨利率']:.2f}%")
        c4.metric("ROE (股東權益報酬率)", f"{ratios['ROE']:.2f}%")
        
        c5, c6, c7 = st.columns(3)
        c5.metric("流動比率", f"{ratios['流動比率']:.2f}%")
        c6.metric("負債比率", f"{ratios['負債比率']:.2f}%")
        c7.metric("現金流/淨利", f"{ratios['現金流對淨利比']:.2f}%")
        
        st.markdown("---")
        
        # 顯示歷史趨勢圖 (左右兩張圖)
        st.subheader("📅 歷史營運趨勢 (近4年)")
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("##### 💰 年度營收趨勢")
            # 畫長條圖
            fig_rev = px.bar(df_trend, x='年份', y='營收', text_auto='.2s', color='營收')
            st.plotly_chart(fig_rev, use_container_width=True)
            
        with col_chart2:
            st.markdown("##### 💵 年度 EPS (每股盈餘) 趨勢")
            # 畫折線圖 + 標記點
            fig_eps = px.line(df_trend, x='年份', y='EPS', markers=True)
            # 讓線條區域有顏色填充，看起來更專業
            fig_eps.update_traces(fill='tozeroy') 
            st.plotly_chart(fig_eps, use_container_width=True)
            
