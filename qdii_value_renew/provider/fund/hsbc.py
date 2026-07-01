import requests
from bs4 import BeautifulSoup
import re

__url = 'http://fundsresearch.investments.hsbc.com.cn/rbwm/Overview.aspx?code={}'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36'
}

# HSBC code 字段前缀 → 市场代码
ISIN_PREFIX_MARKET = {
    'CNE': 'CN', 'KYG': 'CN',
    'HK':  'HK',
    'TW':  'TW',
    'JP':  'JP',
    'KR':  'KR',
    'IN':  'IN',
    'SG':  'SG',
    'AU':  'AU',
    'US':  'US',
}


def market_from_code(code):
    """从 HSBC 的 code 字段（如 'KR7000'）推断市场。"""
    for prefix, market in ISIN_PREFIX_MARKET.items():
        if code.upper().startswith(prefix):
            return market
    return None


def clean_name(name):
    """清洗 HSBC 英文公司名，去掉股份类型、面值、SZHK 等后缀。

    示例：
      'KNOWLEDGE ATLAS TECHNOLOGY JSC LTD ORD CNY .1'
      → 'KNOWLEDGE ATLAS TECHNOLOGY'
      'ZHONGJI INNOLIGHT CO LTD SZHK ORD CNY1.000000000'
      → 'ZHONGJI INNOLIGHT'
    """
    s = name
    s = re.sub(r'\bSZHK\b', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\b(CNY|KRW|USD|JPY|TWD|SGD|AUD|HKD)\s*\d*\.?\d*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\b(ORD|SHS|NPV|JSC)\b', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\b(CO LTD|LTD|INC|CORP|CORPORATION|CO\.)\b\.?', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*-\s*[A-Z]{1,3}\s*', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s+[A-Z]$', '', s).strip()
    s = re.sub(r'\.+$', '', s).strip()
    return s


def lists(fund_id):
    r = requests.get(__url.format(str(fund_id)), headers=headers)
    s = BeautifulSoup(r.content, features='lxml')
    n = s.find(id=re.compile('lbFundNameText')).string
    if n.strip() == '-':
        return None
    d = s.find(id=re.compile('lbPortfolioText')).string
    d = re.search(r"\d{4}-\d{2}-\d{2}", d).group()
    p = s.find(id=re.compile('panelTop10')).find(class_='ms_table')
    if p is None:
        return None
    stock = s.find(id=re.compile('lbStockText')).string[:-1]

    def get_tr(tr):
        td = tr.find_all('td')
        raw_name = td[1].string
        return {
            'code': td[0].string,
            'name': raw_name,
            'cleaned_name': clean_name(raw_name),
            'market': market_from_code(td[0].string),
            'capital': td[2].string,
            'weight': td[3].string
        }
    return {
        "fund_name": n,
        "last_update": d,
        "equities": list(map(get_tr, p.table.find_all('tr')))[1:],
        "equities_percent": stock
    }
