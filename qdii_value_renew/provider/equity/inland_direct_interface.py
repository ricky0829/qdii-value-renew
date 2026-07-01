"""内陆直通源

组合源：新浪港股 + 东方财富全市场 + MSN 全球。
三者都支持直连，无需代理。

设计要点：
- search(kw)：同时查询三个源，合并去重后返回，让上层手动挑选。
  当东方财富搜英文名无结果时，会用 MSN 返回的中文名再搜一次东方财富，
  以覆盖 A 股/港股等需要中文名搜索的场景。
- realtime(ids) / history(_id, ...)：根据 source_id 形态分发——
  * 含 '#' 的为 sina 港股 id（形如 '31#00700'）
  * 含 '.' 且前半为数字的为 eastmoney id（形如 '116.02513'）
  * 其他为 msn SecId（如 'anb9sm'）
"""
from . import sina_interface, msn_interface, eastmoney_interface

# sina 港股的 type code
_SINA_HK_TYPE = ['31']


def _is_sina_id(source_id):
    """sina 的 source_id 形如 '31#00700'，含 '#'。"""
    return isinstance(source_id, str) and '#' in source_id


def _is_em_id(source_id):
    """eastmoney 的 source_id 形如 '116.02513'，前半是数字市场代码。"""
    if not isinstance(source_id, str) or '.' not in source_id:
        return False
    parts = source_id.split('.')
    return len(parts) == 2 and parts[0].isdigit()


def _has_chinese(s):
    """字符串是否含中文字符。"""
    return any('\u4e00' <= c <= '\u9fff' for c in (s or ''))


def search(kw, _type=None):
    """搜索股票。同时查询三个源，合并去重后返回候选列表。

    当东方财富搜英文名无结果时，会用 MSN 返回的中文名再搜一次东方财富，
    以覆盖 A 股/港股等需要中文名搜索的场景。
    """
    # 同时查询三个源
    sina_res = None
    try:
        sina_res = sina_interface.search(kw, _type=_SINA_HK_TYPE)
    except Exception:
        pass
    # sina 港股搜索是模糊匹配，会对英文/拼音词产生大量误匹配。
    # 过滤：如果查询含英文，港股名称的英文字母必须与查询有重叠。
    kw_upper = (kw or '').upper()
    kw_letters = ''.join(c for c in kw_upper if c.isalpha())
    filtered_sina = []
    for r in (sina_res or []):
        name = (r.get('name') or '').upper()
        name_letters = ''.join(c for c in name if c.isalpha())
        if len(kw_letters) >= 3 and kw_letters[:3] not in name_letters:
            continue
        filtered_sina.append(r)

    em_res = None
    try:
        em_res = eastmoney_interface.search(kw, _type=_type)
    except Exception:
        pass

    msn_res = None
    try:
        msn_res = msn_interface.search(kw, _type=_type)
    except Exception:
        pass

    # 去重合并（eastmoney 优先；然后 sina 港股；最后 msn）
    out = []
    seen = set()
    for r in (em_res or []) + filtered_sina + (msn_res or []):
        sid = r.get('source_id')
        if sid in seen:
            continue
        seen.add(sid)
        out.append(r)

    # 补充：如果东方财富搜英文名无结果，用 MSN 返回的中文名再搜一次
    # （A 股/港股在东方财富需要中文名才能搜到）
    has_em_result = any(_is_em_id(r['source_id']) for r in out)
    if not has_em_result:
        for r in out:
            name = r.get('name') or ''
            if _has_chinese(name):
                try:
                    em_extra = eastmoney_interface.search(name, _type=_type)
                    if em_extra:
                        for er in em_extra:
                            esid = er.get('source_id')
                            if esid and esid not in seen and _is_em_id(esid):
                                seen.add(esid)
                                out.append(er)
                except Exception:
                    pass
                break  # 只用第一个含中文的结果去搜

    return out if out else None


def realtime(ids):
    if not ids:
        return []
    sina_ids = [i for i in ids if _is_sina_id(i)]
    em_ids = [i for i in ids if _is_em_id(i)]
    msn_ids = [i for i in ids if not _is_sina_id(i) and not _is_em_id(i)]
    out = []
    if sina_ids:
        try:
            out.extend(sina_interface.realtime(sina_ids))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning('sina realtime 失败: %s', e)
    if em_ids:
        try:
            r = eastmoney_interface.realtime(em_ids)
            if r:
                out.extend(r)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning('eastmoney realtime 失败: %s', e)
    if msn_ids:
        try:
            r = msn_interface.realtime(msn_ids)
            if r:
                out.extend(r)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning('msn realtime 失败: %s', e)
    return out


def history(_id, limit=21):
    if _is_sina_id(_id):
        return sina_interface.history(_id, limit=limit)
    if _is_em_id(_id):
        return eastmoney_interface.history(_id, limit=limit)
    return msn_interface.history(_id, limit=limit)
