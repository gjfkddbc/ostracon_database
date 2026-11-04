"""EA5634 영어 번역(영국박물관 소장품 페이지 PDF)을 결근 행으로 구조화한다."""
import re, subprocess, sys, json
from collections import Counter
PDF=sys.argv[1]
raw=subprocess.run(['pdftotext','-layout',PDF,'-'],capture_output=True,text=True).stdout
lines=[l for l in raw.splitlines() if not re.search(r'britishmuseum\.org/collection|오후 \d|^\f',l)]
text=' '.join(l.strip() for l in lines)
parts=re.findall(r'Inscription translation:(.*?)Inscription note:',text)
assert len(parts)==2
# 계절명은 번역 표기(Spring=아케트, Winter=페레트, Summer=쉐무)를 그대로 쓴다.
SEASON={'Spring':'Spring','Winter':'Winter','Summer':'Summer'}
tok=re.compile(r"""\s*(?:(?P<month>month\s+(?P<m>\d|…)(?P<mq>\(\?\))?\s+of\s+(?P<s>Spring|Winter|Summer))
 |(?P<day>day\s*(?P<d>\d+|…)(?P<dq>\(\?\))?)
 |(?P<name>(?:[A-Z][a-z]+(?:\ [A-Z][a-z]+)?|…\.?):)
 |(?P<bare>(?P<b>\d+)(?P<bq>\(\?\))?)
 |(?P<open>\()
 |(?P<stray>Year\ 40|Nakhtamun|[,.…]+))""",re.X)
rows=[];log=[];names=[]
def run(t,side):
    i=0;w=None;mo=None;last=None;prev_reason=None
    # last: 마지막으로 만든 행 또는 'nodate'
    while i<len(t):
        m=tok.match(t,i)
        if not m:
            if not t[i:].strip(): break
            raise SystemExit('parse fail: '+t[i:i+60])
        i=m.end()
        if m['name']:
            n=m['name'][:-1]
            w='(이름 파손)' if n.startswith('…') else n
            if w not in names: names.append(w)
            mo=None;last=None;prev_reason=None
        elif m['month']:
            mo=None if m['m']=='…' else (SEASON[m['s']],int(m['m']),bool(m['mq']))
            last='monthonly'
        elif m['day'] or m['bare']:
            d=m['d'] or m['b']; q=bool(m['dq'] or m['bq'])
            if d=='…' or mo is None:
                last='nodate'; log.append((w,'날짜 판독 불가',m.group(0).strip())); continue
            r=dict(worker=w,side=side,season=mo[0],month=mo[1],day=int(d),uncertain=q or mo[2],raw=None,reason=None)
            rows.append(r); last=r
        elif m['open']:
            depth=1;j=i
            while depth:
                depth+= {'(':1,')':-1}.get(t[j],0); j+=1
            body=' '.join(t[i:j-1].split()); i=j
            if body in('…','?'): continue
            body=body.replace('OFFFERING','OFFERING')
            norm=body
            if body=='DITTO': norm=prev_reason
            norm=norm.replace(' DITTO','') if norm else norm
            if isinstance(last,dict) and last['raw'] is None:
                last['raw']=body; last['reason']=norm
            else:
                log.append((w,'날짜 없는 사유',body))
            prev_reason=norm
        # stray는 무시한다. 번역 끝의 'day 21 Nakhtamun (WITH HIS BOSS)'처럼 콜론 없는
        # 이름은 새 항목으로 보지 않고, 뒤의 사유를 직전 날짜에 붙인다. 필자의 판단이다.
for side,p in zip(('front','back'),parts): run(p,side)
json.dump(dict(rows=rows,names=names,log=log),open('register.json','w'),ensure_ascii=False,indent=0)
# 원문 토큰 대조
joined=' '.join(parts)
print('names',len(names),names)
print('rows',len(rows),'by side',Counter(r['side'] for r in rows))
print('raw day tokens',len(re.findall(r'\bday\s*\d+',joined)),'raw day …',len(re.findall(r'day\s*…',joined)),'bare numbers parsed',sum(1 for _ in re.finditer(r',\s*\d+(\(\?\))?\s*[,(]',joined)))
print('raw (ILL) tokens',len(re.findall(r'\(ILL\)',joined)),'parsed raw ILL',sum(r['raw']=='ILL' for r in rows))
print('raw DITTO',joined.count('(DITTO)'),'parsed',sum(r['raw']=='DITTO' for r in rows))
print('log',log)
print('no reason',sum(r['raw'] is None for r in rows))
print('unresolved ditto',[r for r in rows if r['raw']=='DITTO' and not r['reason']])
print(Counter(r['reason'] for r in rows).most_common())
