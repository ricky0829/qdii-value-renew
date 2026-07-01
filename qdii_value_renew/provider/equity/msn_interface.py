from . import msn
import json
from decimal import Decimal
import dateparser
from datetime import datetime, timedelta
from dateutil import tz


tz_sh = tz.gettz('Asia/Shanghai')
DATEPARSER_SETTINGS = {'TIMEZONE': 'Asia/Shanghai',
                       'RETURN_AS_TIMEZONE_AWARE': True}
TYPE_MAP = {'ST': '股票', 'FO': '基金', 'FE': 'ETF', 'XI': '指数'}


def parse_utc_str(string):
    return dateparser.parse(string, settings=DATEPARSER_SETTINGS)


def search(kw, _type=None):
    res = msn.search(kw)
    if res is None or len(res) == 0:
        return None
    return [
        {
            'source_id': i['SecId'],
            'code': i['FullInstrument'].split('.')[2] if len(i['FullInstrument'].split('.')) > 2 else i['FullInstrument'],
            'name': i['OS0LN'],
            'type': TYPE_MAP['FO'] if i['OS010'] == 'FO' else '{} - {}'.format(TYPE_MAP[i['OS010']], i['AC040'])
        } for i in map(lambda j: json.loads(j), res)
    ]


def realtime(ids):
    global tz_sh
    if len(ids) == 0:
        return []
    res = msn.lists(ids)
    if res is None or len(res) == 0:
        return None
    res = res if len(res) > 1 else [res]
    out = []
    for i in res:
        # 某些返回项可能缺少字段（如 instrumentId/price），跳过无效项
        try:
            item = i[0]
            if 'instrumentId' not in item or 'price' not in item:
                continue
            out.append({
                'source_id': item['instrumentId'],
                'source_name': getattr(getattr(item, 'localizedAttributes', None), 'zh-cn', item)['displayName'],
                'last': item['price'],
                'change': item['priceChange'],
                'change_percent': item['priceChangePercent'],
                'volume': getattr(item, 'accumulatedVolume', None),
                'is_open': (parse_utc_str(item['timeLastUpdated']) + timedelta(minutes=5)) > datetime.now(tz_sh),
                'time': parse_utc_str(item['timeLastTraded'])
            })
        except (KeyError, TypeError, IndexError):
            continue
    return out


def history(_id, limit=21):
    data = msn.history(_id)[0]['series']
    resp = [{
        'date': parse_utc_str(ts),
        'open': data['openPrices'][idx], 
        'close': data['prices'][idx],
        'high': data['pricesHigh'][idx],
        'low': data['pricesLow'][idx],
        'volume': data['volumes'][idx],
    } for idx, ts in enumerate(data['timeStamps'])]
    for idx, i in enumerate(resp):
        if idx == 0:
            continue
        i['change'] = Decimal(i['close']) - Decimal(resp[idx - 1]['close'])
        i['change_percent'] = Decimal(i['change']) / Decimal(i['close'])
    return resp[-limit:]

