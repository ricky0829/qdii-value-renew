"""东方财富 equity 接口

直连 push2.eastmoney.com 的行情接口和 searchapi.eastmoney.com 的搜索接口。
覆盖沪深 A 股、港股、美股、英股、基金、债券、期货等几乎所有市场。

source_id 编码：使用 eastmoney 的 QuoteID 形态 "<MktNum>.<Code>"，如
  - 沪 A：    "1.600183"
  - 深 A：    "0.300308"
  - 港股：    "116.09638"
  - 美股：    "105.AAPL"
  - 英股：    "155.BC94"
"""
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import requests

_logger = logging.getLogger(__name__)

SEARCH_API = 'http://searchapi.eastmoney.com/api/suggest/get'
REALTIME_API = 'http://push2.eastmoney.com/api/qt/stock/get'
TOKEN = 'D43BF722C8E33BDC906FB84D85A3F12D'  # 公共 token，网页端写死

HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://www.eastmoney.com/',
}

# 5 分钟内视为盘中
tz_sh = timezone(timedelta(hours=8))

# eastmoney 返回字段映射：
# f43  -> 最新价（fltt=2 时已是浮点数）
# f57  -> 代码
# f58  -> 名称
# f86  -> Unix 时间戳（秒），数据更新时间
# f127 -> 行业板块
# f169 -> 涨跌额
# f170 -> 涨跌幅（%）
# f171 -> 换手率（%）
# f47  -> 成交量
# f60  -> 昨收
DEFAULT_FIELDS = 'f43,f57,f58,f86,f169,f170,f171,f47,f60'


def _to_float(v):
    if v is None or v == '-':
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_em_time(t):
    """eastmoney 时间字段 f86 是 Unix 时间戳（秒）。"""
    if t is None or t == '-' or t == 0:
        return None
    try:
        return datetime.fromtimestamp(int(t), tz=tz_sh)
    except (TypeError, ValueError, OSError):
        return None


def _is_em_id(source_id):
    """eastmoney 的 source_id 形如 '116.09638'，含 '.' 且前半是数字市场代码。"""
    if not isinstance(source_id, str) or '.' not in source_id:
        return False
    parts = source_id.split('.')
    return len(parts) == 2 and parts[0].isdigit()


def search(kw, _type=None):
    """搜索股票/基金/债券等。

    _type 参数兼容 sina/msn 接口的 _type 形态，但 eastmoney 用自己的 SecurityType 体系，
    这里不限制，让上层按 name/code 筛选。
    """
    if not kw:
        return None
    try:
        r = requests.get(
            SEARCH_API,
            params={
                'input': kw,
                'type': '14',  # 14 = 全部
                'token': TOKEN,
                'count': '15',
            },
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        _logger.warning('eastmoney search 失败: %s', e)
        return None
    items = (data.get('QuotationCodeTable') or {}).get('Data') or []
    if not items:
        return None
    out = []
    for it in items:
        try:
            quote_id = it.get('QuoteID')
            if not quote_id:
                # 没有 QuoteID 的（如债券）用 MktNum.Code 拼
                quote_id = f"{it.get('MktNum')}.{it.get('Code')}"
            # 过滤掉非股票类（如基金、债券、指数、ETF），让上层决定
            # 但保留所有，让上层打分
            out.append({
                'source_id': quote_id,
                'code': (it.get('Code') or '').upper(),
                'name': it.get('Name') or '',
                # SecurityTypeName: 沪A/深A/港股/美股/英股/基金/债券/指数 ...
                'type': it.get('SecurityTypeName', ''),
            })
        except Exception:
            continue
    return out if out else None


def _batch_realtime(quote_ids):
    """eastmoney 的 stock/get 接口一次只能查一只，但 clist/get 可以批量。
    不过 clist 需要按市场分组。这里采用循环单查的方式，简单但可靠。
    """
    out = []
    for qid in quote_ids:
        try:
            r = requests.get(
                REALTIME_API,
                params={
                    'secid': qid,
                    'fields': DEFAULT_FIELDS,
                    'fltt': '2',  # 价格按真实小数位返回（不×10^digits）
                },
                headers=HEADERS,
                timeout=10,
            )
            r.raise_for_status()
            data = r.json().get('data')
            if not data:
                continue
            # fltt=2 时价格字段已是浮点数，不需再除
            last = _to_float(data.get('f43'))
            if last is None or last == 0:
                # 价格为 0 视为无行情
                continue
            change = _to_float(data.get('f169'))
            change_pct = _to_float(data.get('f170'))
            volume = _to_float(data.get('f47'))
            t = _parse_em_time(data.get('f86'))
            now = datetime.now(tz_sh)
            is_open = t is not None and (now - t) < timedelta(minutes=15)
            out.append({
                'source_id': qid,
                'source_name': data.get('f58'),
                'last': last,
                'change': change if change is not None else 0,
                'change_percent': change_pct if change_pct is not None else 0,
                'volume': volume,
                'time': t,
                'is_open': is_open,
            })
        except Exception as e:
            _logger.warning('eastmoney realtime %s 失败: %s', qid, e)
            continue
    return out


def realtime(ids):
    if not ids:
        return []
    em_ids = [i for i in ids if _is_em_id(i)]
    if not em_ids:
        return []
    return _batch_realtime(em_ids)


def history(_id, limit=21):
    """东方财富 K 线接口：kline Push2HisAPI2
    secid=1.600183&klt=101&fqt=1&end=20500101&lmt=21
    klt: 101=日K, 102=周, 103=月
    fqt: 0=不复权, 1=前复权, 2=后复权
    """
    if not _is_em_id(_id):
        return []
    try:
        r = requests.get(
            'http://push2his.eastmoney.com/api/qt/stock/kline/get',
            params={
                'secid': _id,
                'klt': '101',
                'fqt': '1',
                'end': '20500101',
                'lmt': str(limit),
                'fields1': 'f1,f2,f3',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57',
            },
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json().get('data')
        if not data:
            return []
        klines = data.get('klines') or []
        out = []
        for line in klines:
            # 形如 "2026-06-30,30.50,30.80,30.20,30.60,123456,234,1.23"
            parts = line.split(',')
            if len(parts) < 7:
                continue
            try:
                dt = datetime.strptime(parts[0], '%Y-%m-%d').replace(tzinfo=tz_sh)
                out.append({
                    'date': dt,
                    'open': Decimal(parts[1]),
                    'close': Decimal(parts[2]),
                    'high': Decimal(parts[3]),
                    'low': Decimal(parts[4]),
                    'volume': int(parts[5]) if parts[5].isdigit() else None,
                })
            except (ValueError, IndexError):
                continue
        # 计算涨跌
        for idx, item in enumerate(out):
            if idx == 0:
                continue
            prev = out[idx - 1]['close']
            if prev:
                item['change'] = item['close'] - prev
                item['change_percent'] = item['change'] / prev
        return out[-limit:]
    except Exception as e:
        _logger.warning('eastmoney history %s 失败: %s', _id, e)
        return []
