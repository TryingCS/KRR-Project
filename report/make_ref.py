"""Build ref_compact.docx from pandoc's default reference.docx with compact
typography suitable for a 6-page technical report."""
import zipfile, re

zin = zipfile.ZipFile('ref.docx')
names = zin.namelist()
data = {n: zin.read(n) for n in names}
zin.close()
st = data['word/styles.xml'].decode('utf-8')

def style_block(xml, sid):
    m = re.search(r'(<w:style [^>]*w:styleId="%s".*?</w:style>)' % re.escape(sid), xml, re.S)
    return m

def set_rpr(xml, sid, sz):
    m = style_block(xml, sid)
    if not m: return xml
    b = m.group(1)
    if '<w:sz ' in b:
        b = re.sub(r'<w:sz w:val="\d+"/>', '<w:sz w:val="%d"/>' % sz, b)
        b = re.sub(r'<w:szCs w:val="\d+"/>', '<w:szCs w:val="%d"/>' % sz, b)
    elif '<w:rPr>' in b:
        b = b.replace('<w:rPr>', '<w:rPr><w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (sz, sz), 1)
    else:
        b = b.replace('</w:style>', '<w:rPr><w:sz w:val="%d"/><w:szCs w:val="%d"/></w:rPr></w:style>' % (sz, sz), 1)
    return xml[:m.start()] + b + xml[m.end():]

def set_ppr_spacing(xml, sid, before, after, line=None):
    m = style_block(xml, sid)
    if not m: return xml
    b = m.group(1)
    sp = '<w:spacing w:before="%d" w:after="%d"%s/>' % (
        before, after, ' w:line="%d" w:lineRule="auto"' % line if line else '')
    if '<w:pPr>' in b:
        if '<w:spacing' in b:
            b = re.sub(r'<w:spacing[^>]*/>', sp, b, count=1)
        else:
            b = b.replace('<w:pPr>', '<w:pPr>' + sp, 1)
    else:
        b = b.replace('<w:rPr>', '<w:pPr>' + sp + '</w:pPr><w:rPr>', 1) if '<w:rPr>' in b \
            else b.replace('</w:style>', '<w:pPr>' + sp + '</w:pPr></w:style>', 1)
    return xml[:m.start()] + b + xml[m.end():]

# global default 12pt -> 9pt
st = re.sub(r'(<w:docDefaults>.*?<w:sz w:val=")24(".*?<w:szCs w:val=")24(")',
            r'\g<1>18\g<2>18\g<3>', st, flags=re.S)

for sid, sz in [('Normal', 18), ('Compact', 15), ('BodyText', 18), ('FirstParagraph', 18),
                ('Heading1', 24), ('Heading2', 20), ('Heading3', 18),
                ('Title', 28), ('Subtitle', 20), ('Author', 17)]:
    st = set_rpr(st, sid, sz)

st = set_ppr_spacing(st, 'Normal', 0, 60, 252)
st = set_ppr_spacing(st, 'Compact', 0, 0, 228)
st = set_ppr_spacing(st, 'BodyText', 0, 60, 252)
st = set_ppr_spacing(st, 'FirstParagraph', 0, 60, 252)
st = set_ppr_spacing(st, 'Heading1', 140, 50)
st = set_ppr_spacing(st, 'Heading2', 110, 35)
st = set_ppr_spacing(st, 'Title', 0, 20)
st = set_ppr_spacing(st, 'Subtitle', 0, 10)
st = set_ppr_spacing(st, 'Author', 0, 10)

doc = data['word/document.xml'].decode('utf-8')
doc = re.sub(r'<w:pgMar[^>]*/>',
             '<w:pgMar w:top="750" w:right="850" w:bottom="750" w:left="850" '
             'w:header="708" w:footer="708" w:gutter="0"/>', doc)
data['word/styles.xml'] = st.encode('utf-8')
data['word/document.xml'] = doc.encode('utf-8')
zout = zipfile.ZipFile('ref_compact.docx', 'w', zipfile.ZIP_DEFLATED)
for n in names:
    zout.writestr(n, data[n])
zout.close()
print('ref_compact.docx rebuilt')
