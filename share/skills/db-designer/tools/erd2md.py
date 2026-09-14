#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""erd2md: 由 ERD Editor v3 .erd.json 生成同名数据字典 Markdown。

用法:
    python erd2md.py <file.erd.json> [-o out.md] [--no-relations]

- 读取 UTF-8(带/不带 BOM) 的 v3 .erd.json
- 默认在源文件同目录输出同名 .md
- 域分组取自画布左上角 memo（格式: 域名（X色）｜ 表1, 表2, ...），无 memo 时按表颜色聚类
- FK 由关系实体推导: 含主键列(PK)一侧视为父表, 另一侧为子表外键
"""
import argparse
import json
import os
import sys
from datetime import datetime

COLOR_CN = {
    '#ffa2a2': '红', '#ff8a80': '红', '#e57373': '红', '#f28b82': '红',
    '#a8e6a3': '绿', '#81c784': '绿', '#a5d6a7': '绿', '#66bb6a': '绿',
    '#ffe08a': '黄', '#ffd54f': '黄', '#fff59d': '黄',
    '#8ec8ff': '蓝', '#64b5f6': '蓝', '#4fc3f7': '蓝', '#90caf9': '蓝',
    '#c9a9f0': '紫', '#ba68c8': '紫', '#b39ddb': '紫', '#ce93d8': '紫',
    '#ffcc80': '橙', '#ffb74d': '橙',
    '#80deea': '青', '#4dd0e1': '青',
    '#a1887f': '棕', '#e0e0e0': '灰', '#eeeeee': '灰', '#e2e2e2': '灰',
}


def load(path):
    raw = open(path, 'rb').read()
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    return json.loads(raw.decode('utf-8'))


def key_map(entities):
    if isinstance(entities, dict):
        return entities
    return {e['id']: e for e in entities}


def option_flags(opts):
    f = []
    if opts & 1:
        f.append('AI')
    if opts & 4:
        f.append('UK')
    if opts & 8:
        f.append('NN')
    if opts & 2:
        f.append('PK')
    return f


def collect(data):
    col = data['collections']['tableColumnEntities']
    tab = data['collections']['tableEntities']
    rel = data['collections']['relationshipEntities']
    idx = data['collections']['indexEntities']
    ic = data['collections']['indexColumnEntities']
    memo = data['collections']['memoEntities']
    doc = data['doc']
    return col, tab, rel, idx, ic, memo, doc


def parse_domains(tab, memo, doc):
    """从 memo 还原域分组; 无 memo 时按颜色聚类。"""
    by_name = {t['name']: t for t in tab.values()}
    domains = []  # list of dict(name, color, tables[])
    used = set()
    for mid in doc.get('memoIds', []):
        e = memo[mid]
        v = (e.get('value') or '').strip()
        color = e.get('ui', {}).get('color') or ''
        if not v:
            continue
        # 拆分 "名（色）｜ t1, t2"
        head, _, rest = v.partition('｜')
        if not rest:
            head, _, rest = v.partition('|')
        name = head.strip()
        tnames = [x.strip() for x in rest.replace('，', ',').split(',') if x.strip()]
        tnames = [t for t in tnames if t in by_name]
        if not tnames:
            continue
        for t in tnames:
            used.add(t)
        domains.append({'name': name, 'color': color, 'tables': tnames})
    if not domains:
        # 按颜色聚类
        by_color = {}
        for t in tab.values():
            c = t.get('ui', {}).get('color') or ''
            by_color.setdefault(c, []).append(t['name'])
        for c, names in by_color.items():
            domains.append({'name': COLOR_CN.get(c, '?'), 'color': c, 'tables': sorted(names)})
            used.update(names)
    leftover = [t['name'] for t in tab.values() if t['name'] not in used]
    if leftover:
        domains.append({'name': '未分组', 'color': '', 'tables': sorted(leftover)})
    return domains


def resolve_fk(rel_entities, col):
    """对每列找 {父表, 父列}; 关系含 PK 的一侧视为父。"""
    fk = {}  # colId -> (parentTableId, parentColId)
    for r in rel_entities.values():
        s, e = r['start'], r['end']
        for a, b in ((s, e), (e, s)):
            if len(a['columnIds']) == 1 and len(b['columnIds']) == 1:
                acol, bcol = col[a['columnIds'][0]], col[b['columnIds'][0]]
                if acol['options'] & 2:  # 此列是 PK -> 为父
                    fk[b['columnIds'][0]] = (a['tableId'], a['columnIds'][0])
    return fk


def table_cols(t, col):
    rows = []
    for cid in t.get('seqColumnIds') or t.get('columnIds') or []:
        rows.append(col[cid])
    return rows


def esc(x):
    return (x or '').replace('|', '\\|').replace('\n', ' ').strip()


def render_column_table(col, fk_txt=''):
    flags = option_flags(col['options'])
    default = col.get('default') or ''
    if default == '':
        default = '—'
    comment = esc(col['comment'])
    if fk_txt:
        comment = f"{comment}（外键：{fk_txt}）" if comment else f"外键：{fk_txt}"
    return (f"| `{esc(col['name'])}` | {esc(col['dataType'])} | {' '.join(flags)} | "
            f"{esc(default)} | {comment} |")


def build(args, data):
    col, tab, rel, idx, ic, memo, doc = collect(data)
    col_by_id = key_map(col)
    tab_by_id = key_map(tab)
    tab_by_name = {t['name']: t for t in tab.values()}
    name_of_tab = {tid: t['name'] for tid, t in tab.items()}
    name_of_col = {cid: col_by_id[cid]['name'] for cid in col_by_id}
    fk_map = resolve_fk(rel, col_by_id)
    domains = parse_domains(tab, memo, doc)

    L = []
    src = os.path.basename(args.erd)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    n_tab, n_col = len(tab), len(col)
    n_rel, n_idx = len(rel), len(idx)
    n_fk = len(fk_map)

    L.append(f"# {os.path.splitext(src)[0]} · 数据字典")
    L.append('')
    L.append(f"> 由 `{src}`（ERD Editor v3）自动生成，**请勿手改**；改动请回到 `.erd.json` 后重新运行 `erd2md`。")
    L.append('')
    L.append('## 元信息')
    L.append('')
    L.append(f"- 源文件：`{src}`")
    L.append(f"- 生成时间：{ts}")
    L.append(f"- 规模：{n_tab} 表 · {n_col} 列 · {n_rel} 关系（{n_fk} 外键） · {n_idx} 索引")
    L.append('')
    L.append('## 图例')
    L.append('')
    L.append('- 列键标记：`PK` 主键 · `AI` 自增 · `UK` 唯一 · `NN` 非空；主键列隐含 NN。')
    L.append('- 外键：在列定义中以 `→ 父表.父列` 标注；`FK` 关系在文末附录逐条列出。')
    L.append('- 默认值：`CURRENT_TIMESTAMP` 为数据库当前时间；`—` 表示无默认。')
    L.append('')
    L.append('## 域与表概览')
    L.append('')
    L.append('| 域 | 颜色 | 表 |')
    L.append('|---|---|---|')
    for dom in domains:
        cn = COLOR_CN.get(dom['color'], '')
        color_txt = f"{cn} `{dom['color']}`" if dom['color'] else '—'
        L.append(f"| {esc(dom['name'])} | {color_txt} | " + ' · '.join(f'`{t}`' for t in dom['tables']) + ' |')
    L.append('')
    L.append('## 表定义')
    L.append('')

    for dom in domains:
        L.append(f"### {esc(dom['name'])}")
        L.append('')
        for tname in dom['tables']:
            t = tab_by_name[tname]
            L.append(f"#### `{tname}` — {esc(t.get('comment'))}")
            L.append('')
            L.append('| 列 | 类型 | 键 | 默认 | 注释 |')
            L.append('|---|---|---|---|---|')
            for cid in t.get('seqColumnIds') or t.get('columnIds') or []:
                c = col_by_id[cid]
                fk_txt = ''
                if cid in fk_map:
                    p_tid, p_cid = fk_map[cid]
                    fk_txt = f"`{name_of_tab[p_tid]}.{name_of_col[p_cid]}`"
                L.append(render_column_table(c, fk_txt))
            L.append('')
            # 索引
            tid = t['id']
            tidx = [ix for ix in idx.values() if ix['tableId'] == tid]
            if tidx:
                L.append('索引：')
                for ix in tidx:
                    seq = ix.get('seqIndexColumnIds') or ix.get('indexColumnIds') or []
                    icols = [name_of_col[ic[ccid]['columnId']] for ccid in seq]
                    uniq = 'UNIQUE ' if ix.get('unique') else ''
                    L.append(f"- {uniq}`{esc(ix['name'])}` ({', '.join(f'`{c}`' for c in icols)})")
                L.append('')
    # 附录：关系清单
    if not args.no_relations:
        L.append('## 附录 · 关系清单')
        L.append('')
        L.append('| 子表.列（FK） | → | 父表.列 |')
        L.append('|---|---|---|')
        seen = set()
        for r in rel.values():
            s, e = r['start'], r['end']
            # 父侧含 PK
            parent, child = None, None
            for a, b in ((s, e), (e, s)):
                if len(a['columnIds']) == 1 and len(b['columnIds']) == 1:
                    if col_by_id[a['columnIds'][0]]['options'] & 2:
                        parent, child = a, b
                        break
            if parent and child:
                key = (child['tableId'], child['columnIds'][0], parent['tableId'])
                if key in seen:
                    continue
                seen.add(key)
                L.append(f"| `{name_of_tab[child['tableId']]}.{name_of_col[child['columnIds'][0]]}` "
                         f"| → | `{name_of_tab[parent['tableId']]}.{name_of_col[parent['columnIds'][0]]}` |")
        L.append('')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description='ERD Editor v3 .erd.json → 数据字典 .md')
    ap.add_argument('erd', help='输入 .erd.json 路径')
    ap.add_argument('-o', '--out', help='输出 .md 路径（默认与 erd 同名同目录）')
    ap.add_argument('--no-relations', action='store_true', help='不输出文末关系清单')
    args = ap.parse_args()

    if not os.path.isfile(args.erd):
        sys.exit(f'文件不存在: {args.erd}')
    out = args.out
    if not out:
        base = os.path.basename(args.erd)
        for ext in ('.erd.json', '.vuerd.json'):
            if base.endswith(ext):
                base = base[: -len(ext)]
        base = os.path.splitext(base)[0]
        out = os.path.join(os.path.dirname(args.erd), base + '.md')
    md = build(args, load(args.erd))
    with open(out, 'wb') as f:
        f.write(md.encode('utf-8'))
    print(f'written {out}')


if __name__ == '__main__':
    main()
