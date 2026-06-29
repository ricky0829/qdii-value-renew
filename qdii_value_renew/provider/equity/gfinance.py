import requests
import json
import random
import datetime

__base_path = 'https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute?'
__session = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko)',
}
proxies = None
timeout = 10.


dump_json = lambda o: json.dumps(o, separators=(',', ':'))
rand_num_str = lambda l: str(int(random.random() * (10 ** l)))
out_array = lambda a: a if len(a) != 1 else (out_array(a[0]) if isinstance(a[0], list) and len(a[0]) > 0 else a)

def __batch_exec(envelopes):
    envs = envelopes if isinstance(envelopes, list) else [envelopes]
    rpcids = '%2C'.join(list(dict.fromkeys([e['id'] for e in envs])))
    if (len(envs) == 0):
        return
    elif (len(envs) == 1):
        payload = dump_json([[[envs[0]['id'], dump_json(envs[0]['data']), None, 'generic']]])
    else:
        payload = dump_json([[[e['id'], dump_json(e['data']), None, str(i + 1)] for i, e in enumerate(envs)]])
    path = f'rpcids={rpcids}&f.sid=-{rand_num_str(19)}&bl=boq_finance-ui_20211101.11_p0&hl=en&_reqid={rand_num_str(8)}'
    rsp = __session.post(__base_path + path,  params={'f.req': payload}, headers=headers, proxies=proxies, timeout=timeout)
    if rsp.status_code != 200:
        raise Exception('网络错误: {}'.format(rsp.status_code))
    rsps = json.loads(rsp.text.split('\n')[2])
    datas = []
    for r in rsps:
        if r[0] == 'er': 
            raise Exception('请求错误: {}'.format(r[5]))
        elif r[0] == 'wrb.fr':
            cur = json.loads(r[2])
            datas.insert(int(r[6] if r[6] != 'generic' else 1) - 1, cur if len(cur) > 0 else [])
    return datas if len(datas) > 1 else datas[0]


def parse_trading(i):
    if i is None:
        return None
    return {
        'last': i[0],
        'change': i[1],
        'change_percent': i[2],
    }


def parse_datetime(i):
    arr = []
    for item in i:
        if isinstance(item, int):
            arr.append(item)
        elif item is None:
            arr.append(0)
        elif isinstance(item, list):
            arr.append(datetime.timezone(datetime.timedelta(seconds=0 if len(item) == 0 else item[0])))
    return datetime.datetime(*arr)


def _safe_get(lst, idx, default=None):
    return lst[idx] if idx < len(lst) else default


def parse_detail(i):
    if i is None or len(i) < 5 or i[4] is None:
        return None
    trading = parse_trading(_safe_get(i, 5))
    extended_trading = parse_trading(_safe_get(i, 16))
    update_ts = _safe_get(i, 11)
    last_ts = _safe_get(i, 17)
    extended_ts = _safe_get(i, 18)
    trading_window = _safe_get(i, 19)
    return {
        'inner_id': i[0],
        'code': i[1][0],
        'market': i[1][1] if len(i[1]) > 1 else None,
        'name': i[2],
        'currency': i[4],
        'trading': trading,
        'last_close': _safe_get(i, 7),
        'region': _safe_get(i, 9),
        # 10?
        'update_timestamp': update_ts[0] if update_ts else None,
        'timezone': _safe_get(i, 12),
        'timezone_offset': _safe_get(i, 13),
        'extended_trading': extended_trading,
        'last_timestamp': last_ts[0] if last_ts else None,
        'extended_timestamp': None if extended_ts is None else extended_ts[0],
        'start_trading_dt': None if trading_window is None else parse_datetime(trading_window[0][1]),
        'end_trading_dt': None if trading_window is None else parse_datetime(trading_window[0][2]),
        'full_ticker': _safe_get(i, 21) or (i[1][1] + ':' + i[1][0] if len(i[1]) > 1 else i[1][0])
    }


def search(kw):
    rsp = __batch_exec({'id': 'mKsvE', 'data': [kw, [], True, True]})
    list = [parse_detail(e[3]) for e in rsp[0]] if len(rsp) > 0 else []
    return filter(lambda i: i is not None, list)


def lists_detail(ids):
    # xh8wxf endpoint is deprecated, use mKsvE (search) instead
    envelopes = [{'id': 'mKsvE', 'data': [ticker_id, [], True, True]} for ticker_id in ids]
    rsp = __batch_exec(envelopes)

    # Single id: response is [search_results, ...], not a list of responses
    if len(ids) == 1:
        rsp = [rsp]

    results = []
    for idx, r in enumerate(rsp):
        target_id = ids[idx]
        # Each search response format: [[result1, result2, ...], null, null, ...]
        search_list = r[0] if isinstance(r, list) and len(r) > 0 and isinstance(r[0], list) else []
        # Find exact match by full_ticker (e[21] == 'CODE:MARKET')
        found = None
        for e in search_list:
            if isinstance(e, list) and len(e) > 3 and isinstance(e[3], list):
                if _safe_get(e[3], 21) == target_id:
                    found = e[3]
                    break
        # Fallback to first result if no exact match
        if found is None and len(search_list) > 0:
            first = search_list[0]
            if isinstance(first, list) and len(first) > 3 and isinstance(first[3], list):
                found = first[3]
        results.append(parse_detail(found))
    return results


def lists_simple(ids):
    rsp = __batch_exec({'id': 'Ba1tad', 'data': [[[i] for i in ids]]})
    return [{
        'currency': e[0],
        'trading': parse_trading(e[1]),
        'update_timestamp': e[2][0],
        'inner_id': e[3],
        'has_extended': e[5],
        'extended_trading': parse_trading(e[6]),
        'extended_timestamp': None if e[7] is None else e[7][0],
    } for e in rsp]


# range: 1: 1d(/min), 2: 5d(/30min), 3: 1m(/day), 4: 6m(/day), 5: ytd(/day), 6: 1y(/day), 7: 5y(/week), 8:max
def history(_id, _range):
    rsp = __batch_exec({'id': 'AiCwsd', 'data': [[[None, _id.split(':')]], _range]})
    return [{
        'datetime': parse_datetime(i[0]),
        'trading': parse_trading(i[1]),
        'volume': i[2]
    } for i in out_array(rsp)[3][0][1]]
