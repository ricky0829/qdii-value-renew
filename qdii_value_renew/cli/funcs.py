import sys
import os
import inquirer
from rich import box
from rich.console import Console
from rich.table import Table
import csv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import processing
from provider.equity import *
from provider.fund import *
from confs import Config


# 地区名称 -> 旗帜 emoji 映射
REGION_EMOJI = {
    # 亚洲
    '中国': '🇨🇳', '中国大陆': '🇨🇳', '中國': '🇨🇳', 'China': '🇨🇳',
    '香港': '🇭🇰', 'Hong Kong': '🇭🇰', 'HK': '🇭🇰',
    '台湾': '🇹🇼', '台灣': '🇹🇼', 'Taiwan': '🇹🇼', 'TW': '🇹🇼',
    '日本': '🇯🇵', 'Japan': '🇯🇵', 'JP': '🇯🇵',
    '韩国': '🇰🇷', '南韓': '🇰🇷', 'Korea': '🇰🇷', 'South Korea': '🇰🇷', 'KR': '🇰🇷',
    '印度': '🇮🇳', 'India': '🇮🇳', 'IN': '🇮🇳',
    '新加坡': '🇸🇬', 'Singapore': '🇸🇬', 'SG': '🇸🇬',
    '泰国': '🇹🇭', 'Thailand': '🇹🇭', 'TH': '🇹🇭',
    '马来西亚': '🇲🇾', 'Malaysia': '🇲🇾', 'MY': '🇲🇾',
    '越南': '🇻🇳', 'Vietnam': '🇻🇳', 'VN': '🇻🇳',
    '印尼': '🇮🇩', '印度尼西亚': '🇮🇩', 'Indonesia': '🇮🇩', 'ID': '🇮🇩',
    '菲律宾': '🇵🇭', 'Philippines': '🇵🇭', 'PH': '🇵🇭',
    # 欧洲
    '英国': '🇬🇧', 'United Kingdom': '🇬🇧', 'UK': '🇬🇧', 'GB': '🇬🇧',
    '法国': '🇫🇷', 'France': '🇫🇷', 'FR': '🇫🇷',
    '德国': '🇩🇪', 'Germany': '🇩🇪', 'DE': '🇩🇪',
    '瑞士': '🇨🇭', 'Switzerland': '🇨🇭', 'CH': '🇨🇭',
    '荷兰': '🇳🇱', 'Netherlands': '🇳🇱', 'NL': '🇳🇱',
    '瑞典': '🇸🇪', 'Sweden': '🇸🇪', 'SE': '🇸🇪',
    '丹麦': '🇩🇰', 'Denmark': '🇩🇰', 'DK': '🇩🇰',
    '挪威': '🇳🇴', 'Norway': '🇳🇴', 'NO': '🇳🇴',
    '芬兰': '🇫🇮', 'Finland': '🇫🇮', 'FI': '🇫🇮',
    '西班牙': '🇪🇸', 'Spain': '🇪🇸', 'ES': '🇪🇸',
    '意大利': '🇮🇹', 'Italy': '🇮🇹', 'IT': '🇮🇹',
    '爱尔兰': '🇮🇪', 'Ireland': '🇮🇪', 'IE': '🇮🇪',
    '比利时': '🇧🇪', 'Belgium': '🇧🇪', 'BE': '🇧🇪',
    '奥地利': '🇦🇹', 'Austria': '🇦🇹', 'AT': '🇦🇹',
    '葡萄牙': '🇵🇹', 'Portugal': '🇵🇹', 'PT': '🇵🇹',
    '波兰': '🇵🇱', 'Poland': '🇵🇱', 'PL': '🇵🇱',
    # 美洲
    '美国': '🇺🇸', 'United States': '🇺🇸', 'US': '🇺🇸', 'USA': '🇺🇸',
    '加拿大': '🇨🇦', 'Canada': '🇨🇦', 'CA': '🇨🇦',
    '墨西哥': '🇲🇽', 'Mexico': '🇲🇽', 'MX': '🇲🇽',
    '巴西': '🇧🇷', 'Brazil': '🇧🇷', 'BR': '🇧🇷',
    # 大洋洲
    '澳大利亚': '🇦🇺', 'Australia': '🇦🇺', 'AU': '🇦🇺',
    '新西兰': '🇳🇿', 'New Zealand': '🇳🇿', 'NZ': '🇳🇿',
    # 中东/非洲
    '以色列': '🇮🇱', 'Israel': '🇮🇱', 'IL': '🇮🇱',
    '南非': '🇿🇦', 'South Africa': '🇿🇦', 'ZA': '🇿🇦',
    '沙特': '🇸🇦', '沙特阿拉伯': '🇸🇦', 'Saudi Arabia': '🇸🇦', 'SA': '🇸🇦',
    '阿联酋': '🇦🇪', 'UAE': '🇦🇪', 'AE': '🇦🇪',
    # 其他
    '俄罗斯': '🇷🇺', 'Russia': '🇷🇺', 'RU': '🇷🇺',
    '土耳其': '🇹🇷', 'Turkey': '🇹🇷', 'TR': '🇹🇷',
}


# 交易所后缀 -> 旗帜 emoji 映射
# 格式支持： gfinance 的 CODE:EXCHANGE, yahootw 的 CODE.SUFFIX
EXCHANGE_EMOJI = {
    # 香港
    'HKG': '🇭🇰', 'HKE': '🇭🇰', 'HKSE': '🇭🇰',
    # 日本
    'TYO': '🇯🇵', 'JPX': '🇯🇵', 'TSE': '🇯🇵', 'OSA': '🇯🇵',
    # 韩国
    'KRX': '🇰🇷', 'KSC': '🇰🇷', 'KOE': '🇰🇷', 'KOSDAQ': '🇰🇷',
    # 台湾
    'TPE': '🇹🇼', 'TWSE': '🇹🇼', 'TWO': '🇹🇼',
    # 中国大陆
    'SHA': '🇨🇳', 'SHE': '🇨🇳', 'SHG': '🇨🇳',
    # 美国
    'NASDAQ': '🇺🇸', 'NYSE': '🇺🇸', 'AMEX': '🇺🇸', 'NYSEARCA': '🇺🇸',
    'BATS': '🇺🇸', 'OTCMKTS': '🇺🇸', 'NYSEAMERICAN': '🇺🇸',
    # 英国
    'LON': '🇬🇧', 'LSE': '🇬🇧',
    # 德国
    'ETR': '🇩🇪', 'FRA': '🇩🇪', 'XETRA': '🇩🇪',
    # 法国
    'EPA': '🇫🇷', 'PAR': '🇫🇷',
    # 瑞士
    'SWX': '🇨🇭', 'VTX': '🇨🇭',
    # 荷兰
    'AMS': '🇳🇱', 'EBR': '🇳🇱',
    # 瑞典
    'STO': '🇸🇪',
    # 丹麦
    'CPH': '🇩🇰',
    # 挪威
    'OSL': '🇳🇴',
    # 芬兰
    'HEL': '🇫🇮',
    # 西班牙
    'BME': '🇪🇸',
    # 意大利
    'BIT': '🇮🇹', 'MIL': '🇮🇹',
    # 澳大利亚
    'ASX': '🇦🇺',
    # 加拿大
    'TSX': '🇨🇦', 'CVE': '🇨🇦', 'CNQ': '🇨🇦',
    # 印度
    'NSE': '🇮🇳', 'BSE': '🇮🇳',
    # 新加坡
    'SGX': '🇸🇬',
    # 南非
    'JSE': '🇿🇦',
    # 巴西
    'BVMF': '🇧🇷', 'SAO': '🇧🇷',
    # 以色列
    'TLV': '🇮🇱',
    # 沙特
    'SAU': '🇸🇦', 'TADAWUL': '🇸🇦',
    # 阿联酋
    'DFM': '🇦🇪', 'ADX': '🇦🇪',
    # 泰国
    'SET': '🇹🇭', 'BKK': '🇹🇭',
    # 马来西亚
    'KLSE': '🇲🇾', 'KLS': '🇲🇾',
    # 印尼
    'IDX': '🇮🇩', 'JKT': '🇮🇩',
    # 越南
    'HOSE': '🇻🇳', 'HNX': '🇻🇳',
}


def _get_emoji_from_source_id(source_id):
    """从 source_id 推断地区 emoji，支持 CODE:EXCHANGE 和 CODE.SUFFIX 格式"""
    if not source_id:
        return None
    # gfinance 格式: CODE:EXCHANGE
    if ':' in source_id:
        exchange = source_id.split(':')[-1].upper()
        return EXCHANGE_EMOJI.get(exchange)
    # yahootw/yahoo 格式: CODE.SUFFIX
    if '.' in source_id:
        suffix = source_id.split('.')[-1].upper()
        # Yahoo 常见后缀到交易所映射
        yahoo_suffix_map = {
            'HK': 'HKG', 'T': 'TYO', 'KS': 'KRX', 'KQ': 'KRX',
            'TW': 'TPE', 'TWO': 'TWO', 'SS': 'SHA', 'SZ': 'SHE',
            'L': 'LON', 'DE': 'ETR', 'PA': 'EPA', 'SW': 'SWX',
            'AS': 'AMS', 'ST': 'STO', 'CO': 'CPH', 'OL': 'OSL',
            'HE': 'HEL', 'MC': 'BME', 'MI': 'BIT', 'AX': 'ASX',
            'TO': 'TSX', 'V': 'CVE', 'NS': 'NSE', 'BO': 'BSE',
            'SI': 'SGX', 'JO': 'JSE', 'SA': 'SAO', 'TA': 'TLV',
            'BK': 'BKK', 'KL': 'KLSE', 'JK': 'IDX', 'VN': 'HOSE',
        }
        exchange = yahoo_suffix_map.get(suffix)
        return EXCHANGE_EMOJI.get(exchange) if exchange else None
    return None


def add_region_emoji(equities):
    """为持仓列表中每个条目在 name 前添加地区旗帜 emoji。
    优先级： location 字段 > source_id 交易所推断
    """
    for e in equities:
        # 已有 emoji 则幂等跳过（判断条目名称首个字符是否为旗帜 emoji 区间）
        if e.get('name') and ord(e['name'][0]) >= 0x1F1E0:
            continue
        emoji = None
        # 1. 优先从 location 字段匹配
        location = e.get('location', '').strip()
        if location:
            emoji = REGION_EMOJI.get(location)
        # 2. 备用：从 source_id 交易所推断
        if not emoji:
            emoji = _get_emoji_from_source_id(e.get('source_id', ''))
        if emoji:
            e['name'] = emoji + e['name']
    return equities


CUR_EQ_PROVIDER = EQUITY_PROVIDER[0]
INQUIRER_THEME = inquirer.themes.load_theme_from_dict({
    "List": {
        "selection_color": "black_on_white",
    }
})
INQUIRER_RENDER = inquirer.render.console.ConsoleRender(theme=INQUIRER_THEME)


def clear_line():
    sys.stdout.write('\x1b[1A')
    sys.stdout.write('\x1b[2K')


def read_conf(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return Config(obj=f.read())
    else:
        return None


def create_conf(obj, _id):
    c = Config(_id=_id)
    c.data.update(obj)
    return c


def get_fund_provider(provider=None):
    global FUND_PROVIDER
    if provider:
        f = list(filter(lambda p: p['id'] == provider, FUND_PROVIDER))
        return f[0] if len(f) == 1 else None
    else:
        options = [(i['name'], i) for i in FUND_PROVIDER]
        options.append(('手动添加', False))
        ret = inquirer.list_input('上下键选择基金信息源', choices=options, render=INQUIRER_RENDER)
        [clear_line() for o in range(len(options) + 1)]
        return ret


def get_fund(_id, provider):
    try:
        ret = provider['object'].lists(_id)
        if ret and len(ret["equities"]) > 0:
            return ret
        print(f"在「{provider['name']}」中找不到基金信息.")
    except Exception as e:
        #Console().print_exception(show_locals=True)
        print(f'查询时出现故障: {e}')
    return None


def search_equity(default_query=None):
    global EQUITY_PROVIDER, CUR_EQ_PROVIDER
    data = None
    while data is None:
        default_info = f', 默认: {default_query}' if default_query else ''
        query = input(f'搜索 (p 跳过, q 切换源{default_info}): ') or default_query
        clear_line()
        if query == 'p':
            print('已跳过.')
            return None
        elif query == 'q':
            options = [(p['name'], p) for p in EQUITY_PROVIDER]
            CUR_EQ_PROVIDER = inquirer.list_input('上下键选择行情信息源', choices=options, render=INQUIRER_RENDER)
            [clear_line() for o in range(len(options) + 1)]
            continue
        else:
            try:
                search_res = CUR_EQ_PROVIDER['object'].search(query)
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print('错误: ', exc_value)
                continue
            if search_res is None or len(search_res) == 0:
                print('未搜索到结果.')
                continue
            options = [(f"{r['type']} | {r['name']} ({r['code']})", r) for r in search_res[:10]]
            options.append(('重新搜索', None))
            data = inquirer.list_input('上下键选择对应的项目', choices=options, default=0, render=INQUIRER_RENDER)
            [clear_line() for o in range(len(options) + 1)]
    return {'source': CUR_EQ_PROVIDER['id'], 'source_id': data['source_id'], 'name': strQ2B(data['name']), 'code': data['code']}


def custom_equities():
    equities = []
    print('添加持仓信息：')
    while True:
        ret = search_equity()
        if ret:
            ret['weight'] = input('权重(百分比, 不加%): ') or '0'
            try:
                float(ret['weight'])
            except:
                print('不是合法的数字, 请重试.\n')
                continue
            equities.append(ret)
            print()
        else:
            break
    return equities


def remove_col_suffix(table, col, suffix):
    filtered_len = len(list(filter(lambda a: a[col].endswith(suffix), table)))
    if filtered_len == len(table):
        for row in table:
            row[col] = row[col][:-len(suffix)]


def strQ2B(ustring):
    rstring = ""
    for uchar in ustring:
        inside_code=ord(uchar)
        if inside_code == 12288:
            inside_code = 32 
        elif (inside_code >= 65281 and inside_code <= 65374):
            inside_code -= 65248

        rstring += chr(inside_code)
    return rstring


def remove_suffix_words(s, suffixes):
    words = s.split(' ')
    ret_words = []
    for w in words:
        if w in suffixes:
            return ' '.join(ret_words)
        ret_words.append(w)
    return ' '.join(ret_words)


def red_green(num, fmt):
    if num > 0:
        return '[bright_red]' + fmt.format(num) + '[/bright_red]'
    elif num < 0:
        return '[bright_green]' + fmt.format(num) + '[/bright_green]'
    else:
        return fmt.format(num)


def fetch_data(conf):
    equities, summary = processing.fetch(conf.data['equities'], conf.data['equities_percent'])
    reference = processing.single_fetch(
        conf.data['reference']) if conf.data['reference'] else None
    return equities, summary, reference


def get_table(conf, equities, summary, reference):
    last_update_f = summary['last_update'].strftime('%Y-%m-%d %H:%M:%S')
    caption = '(报价截至 {}, 持仓截至 {})\n'.format(last_update_f, conf.data['last_update'])
    table = Table(title=conf.data['fund_name'], 
                  title_style="",
                  caption=caption, caption_style='white', caption_justify='right',
                  box=box.ROUNDED, show_footer=True)

    footer_name = '总计'
    footer_weight = '{:.2f}%'.format(summary['total_weight'])
    footer_current = ''
    footer_change = ''
    footer_precent = red_green(summary['total_percent'], '{:+.2f}%')
    if summary['today_weight'] > 0 and summary['today_weight'] != summary['total_weight']:
        footer_name += '\n今日交易'
        footer_weight += '\n' + '{:.2f}%'.format(summary['today_weight'])
        footer_current += '\n'
        footer_change += '\n'
        footer_precent += '\n' + red_green(summary['today_percent'], '{:+.2f}%')
    if reference:
        footer_name += '\n' + reference['name']
        footer_weight += '\n'
        footer_current += '\n' + '{:.2f}'.format(reference['last'])
        footer_change += '\n' + red_green(reference['change'], '{:+.2f}')
        footer_precent += '\n' + red_green(reference['change_percent'], '{:+.2f}%')

    table.add_column("代码", justify="right", no_wrap=True)
    table.add_column("名称", justify="left",  no_wrap=False, footer=footer_name)
    table.add_column("权重", justify="right", no_wrap=True,  footer=footer_weight)
    table.add_column("当前", justify="right", no_wrap=True,  footer=footer_current)
    table.add_column("涨跌", justify="right", no_wrap=True,  footer=footer_change)
    table.add_column("幅度", justify="right", no_wrap=True,  footer=footer_precent)

    def parse_name(i):
        if i['is_open']:
            return '\U0001F551' + i['name']
        elif i['is_past']:
            return '\U0001F311' + i['name']
        elif i['is_today']:
            return '\U0001F3AF' + i['name']
        else:
            return '\U0001F313' + i['name']

    rows = []
    for i in equities[:10]:
        rows.append([
            i['code'],
            parse_name(i),
            '{:.2f}%'.format(i['weight']),
            '{:.2f}'.format(i['last']),
            red_green(i['change'], '{:+.2f}'),
            red_green(i['change_percent'], '{:+.2f}%'),
        ])
        if 'after_hour_percent' in i.keys():
            rows.append(['', '', '延时', '{:.2f}'.format(i['after_hour_price']),
                         red_green(i['after_hour_change'], '{:+.2f}'), red_green(i['after_hour_percent'], '{:+.2f}%')])

    remove_col_suffix(rows, 3, '.00')
    remove_col_suffix(rows, 4, '.00')
    [table.add_row(*row) for row in rows]
    return table


def output_csv(path, equities, summary, reference):
    with open(path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[
                                'code', 'name', 'weight', 'last', 'change', 'change_percent'], extrasaction='ignore')
        writer.writeheader()
        writer.writerows(equities)
        writer.writerow({'code': '总计', 'name': '', 'weight': summary['total_weight'],
                         'last': '', 'change': '', 'change_percent': summary['total_percent']})
        if summary['today_weight'] > 0 and summary['today_weight'] != summary['total_weight']:
            writer.writerow({'code': '本交易日', 'name': '', 'weight': summary['today_weight'],
                             'last': '', 'change': '', 'change_percent': summary['today_percent']})
        if reference:
            writer.writerow({'code': reference['name'], 'name': '', 'weight': '', 'last': reference['last'],
                             'change': reference['change'], 'change_percent': reference['change_percent']})
        print('已保存至 ' + path + '.')


def history_csv(path, conf, limit):
    hs = processing.fetch_history(conf.data['equities'], limit=limit)
    r = {}
    for equity in hs:
        for i in range(len(equity['history']) - 1):
            cur, las = equity['history'][i + 1], equity['history'][i]
            if cur['date'] not in r.keys():
                r[cur['date']] = {}
            r[cur['date']][equity['name']] = (cur['close'] / las['close'] - 1)
    t = []
    for date, data in r.items():
        i = data.copy()
        i['date'] = date
        t.append(i)
    with open(path, 'w', newline='') as csvfile:
        fieldnames = ['date'] + [equity['name'] for equity in hs]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(t)
        print('已保存至 ' + path + '.')
