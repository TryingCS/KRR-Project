"""Post-process a pandoc-generated DOCX so tables get fixed, proportional
column widths (LibreOffice/Word auto-layout collapses pandoc tables into
unreadable narrow columns). Pure stdlib, string-level surgery on
word/document.xml (pandoc never emits nested tables, which keeps the
parsing simple and safe).
"""
import re
import sys
import zipfile

W_TBL = 10100  # usable width in twips for A4 with 900-twip side margins


def cell_text(tc: str) -> str:
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tc))


def fix_table(m) -> str:
    tbl = m.group(0)
    rows = re.findall(r"<w:tr\b.*?</w:tr>", tbl, re.S)
    if not rows:
        return tbl
    parsed = []
    for tr in rows:
        cells = re.findall(r"<w:tc\b.*?</w:tc>", tr, re.S)
        parsed.append([cell_text(tc) for tc in cells])
    ncols = max(len(r) for r in parsed)
    # proportional widths from the longest cell text per column
    lens = []
    for c in range(ncols):
        lens.append(max((len(r[c]) for r in parsed if len(r) > c), default=4))
    weights = [max(17.0, min(46.0, (l + 3) ** 0.85)) for l in lens]
    total = sum(weights)
    widths = [int(W_TBL * w / total) for w in weights]
    widths[-1] += W_TBL - sum(widths)

    # --- tblPr: fixed layout + total width -------------------------------
    def fix_tblpr(m):
        block = m.group(0)
        block = re.sub(r"<w:tblW[^>]*/>", "", block)
        block = re.sub(r"<w:tblLayout[^>]*/>", "", block)
        block = block.replace(
            "</w:tblPr>",
            '<w:tblW w:w="%d" w:type="dxa"/><w:tblLayout w:type="fixed"/></w:tblPr>' % W_TBL,
            1,
        )
        return block

    tbl = re.sub(r"<w:tblPr>.*?</w:tblPr>", fix_tblpr, tbl, count=1, flags=re.S)

    # --- tblGrid -----------------------------------------------------------
    grid = "<w:tblGrid>" + "".join('<w:gridCol w:w="%d"/>' % w for w in widths) + "</w:tblGrid>"
    tbl = re.sub(r"<w:tblGrid>.*?</w:tblGrid>", grid, tbl, count=1, flags=re.S)

    # --- per-cell tcW -------------------------------------------------------
    def fix_row(m) -> str:
        tr = m.group(0)
        cells = re.findall(r"<w:tc\b.*?</w:tc>", tr, re.S)
        out = tr
        for i, tc in enumerate(cells):
            w = widths[i] if i < len(widths) else widths[-1]
            if re.search(r"<w:tcPr\s*/>", tc):
                new_tc = re.sub(r"<w:tcW[^>]*/>", "", tc, count=1)
                new_tc = re.sub(r"<w:tcPr\s*/>",
                                '<w:tcPr><w:tcW w:w="%d" w:type="dxa"/></w:tcPr>' % w,
                                new_tc, count=1)
            elif re.search(r"<w:tcPr[ >]", tc):
                new_tc = re.sub(r"<w:tcW[^>]*/>", "", tc, count=1)
                new_tc = re.sub(r"<w:tcPr([ >])", lambda mm: "<w:tcPr" + mm.group(1) + '<w:tcW w:w="%d" w:type="dxa"/>' % w, new_tc, count=1)
            else:
                new_tc = tc.replace("<w:tc>", '<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/></w:tcPr>' % w, 1)
            out = out.replace(tc, new_tc, 1)
        return out

    tbl = re.sub(r"<w:tr\b.*?</w:tr>", fix_row, tbl, flags=re.S)
    return tbl


def main(path: str):
    zin = zipfile.ZipFile(path)
    names = zin.namelist()
    data = {n: zin.read(n) for n in names}
    zin.close()
    doc = data["word/document.xml"].decode("utf-8")
    doc = re.sub(r"<w:tbl>.*?</w:tbl>", fix_table, doc, flags=re.S)
    data["word/document.xml"] = doc.encode("utf-8")
    zout = zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED)
    for n in names:
        zout.writestr(n, data[n])
    zout.close()
    n_tbl = doc.count("<w:tbl>")
    print(f"fixed {n_tbl} tables in {path}")


if __name__ == "__main__":
    main(sys.argv[1])
