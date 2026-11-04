"""register.json을 SQLite에 넣고, 박물관·함부르크대 설명을 쿼리로 검증한다."""
import json, sqlite3, re
D=json.load(open('register.json'))
S={'Spring':1,'Winter':2,'Summer':3}
def dn(s,m,d): return 120*(S[s]-1)+30*(m-1)+d
START=dn('Spring',3,1)
def cat(r):
    """번역 표현을 기준으로 분류한다. 행위를 추론하지 않는다."""
    if r is None: return None
    if r in('ILL','SUFFERING WITH HIS EYE','THE SCORPION BIT HIM'): return 'own_illness'
    if r=='ILL: erased': return 'own_illness_erased'
    if r=='WITH HIS BOSS': return 'with_boss'
    if r in('WITH THE SCRIBE','OFF ABSENT WITH THE SCRIBE'): return 'scribe_related'
    if r.startswith('FETCHING'): return 'fetching_stone'
    if r in('WITH AAPEHTI','WITH HOREMWIA'): return 'colleague_related'
    if r.startswith(('WITH KHONS MAKING','MAKING REMEDIES')): return 'remedies'
    if 'BLEEDING' in r or r=='HIS MOTHER WAS ILL': return 'family_bleeding_illness'
    if r.startswith(('WRAPPING','EMBALMING','LIBATING','MOURNING')): return 'funeral_memorial'
    if r=='BREWING BEER': return 'brewing'
    if r.startswith(('OFFERING','WITH HIS GOD','HIS FEAST','DRINKING','BURYING THE GOD')): return 'religion_festival_drinking'
    if r.startswith(('BUILDING','STRENGTHENING')): return 'private'
    if r=='OFF ABSENT': return 'unspecified'
    raise ValueError(r)
c=sqlite3.connect('absence.db'); c.execute('PRAGMA foreign_keys=ON')
c.executescript("""
DROP TABLE IF EXISTS reading;DROP TABLE IF EXISTS absence;DROP TABLE IF EXISTS worker_alias;DROP TABLE IF EXISTS worker;DROP TABLE IF EXISTS source;
CREATE TABLE source(source_id INTEGER PRIMARY KEY, title TEXT NOT NULL);
CREATE TABLE worker(worker_id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE worker_alias(alias TEXT PRIMARY KEY, worker_id INTEGER NOT NULL REFERENCES worker(worker_id));
CREATE TABLE absence(absence_id INTEGER PRIMARY KEY, worker_id INTEGER NOT NULL REFERENCES worker(worker_id),
 side TEXT NOT NULL CHECK(side IN('front','back')),
 season TEXT NOT NULL CHECK(season IN('Spring','Winter','Summer')), month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 4), day INTEGER NOT NULL CHECK(day BETWEEN 1 AND 30),
 day_no INTEGER NOT NULL, seq_no INTEGER NOT NULL, uncertain INTEGER NOT NULL DEFAULT 0,
 UNIQUE(worker_id, day_no));
CREATE TABLE reading(reading_id INTEGER PRIMARY KEY, absence_id INTEGER NOT NULL REFERENCES absence(absence_id),
 source_id INTEGER NOT NULL REFERENCES source(source_id), raw_text TEXT, reason TEXT, category TEXT,
 mentions_worker_id INTEGER REFERENCES worker(worker_id),
 UNIQUE(absence_id, source_id));
INSERT INTO source VALUES(1,'British Museum translation'),(2,'Hamburg CSMC'),(3,'The History of Egypt Podcast'),(4,'Janssen 1980');
""")
wid={n:c.execute('INSERT INTO worker(name) VALUES(?)',(n,)).lastrowid for n in D['names']}
dup=[]
for r in D['rows']:
    d=dn(r['season'],r['month'],r['day'])
    try:
        i=c.execute('INSERT INTO absence(worker_id,side,season,month,day,day_no,seq_no,uncertain) VALUES(?,?,?,?,?,?,?,?)',(wid[r['worker']],r['side'],r['season'],r['month'],r['day'],d,(d-START)%360,int(r['uncertain']))).lastrowid
    except sqlite3.IntegrityError: dup.append(r); continue
    c.execute('INSERT INTO reading(absence_id,source_id,raw_text,reason,category) VALUES(?,?,?,?,?)',(i,1,r['raw'],r['reason'],cat(r['reason'])))
print('duplicates rejected',dup)
for a,b in [('Khons','Khonsu'),('Aapehti','Apehty'),('Penduauu','Pendua')]:
    c.execute('INSERT INTO worker_alias VALUES(?,?)',(b,wid[a]))
def add(w,s,m,d,src,txt,k):
    i=c.execute('SELECT absence_id FROM absence WHERE worker_id=? AND day_no=?',(wid[w],dn(s,m,d))).fetchone()[0]
    c.execute('INSERT INTO reading(absence_id,source_id,raw_text,reason,category) VALUES(?,?,?,?,?)',(i,src,txt,txt,k))
add('Neferabu','Spring',4,15,2,'daughter in menstruation (lit. purification)','family_care')
add('Neferabu','Spring',4,15,3,'daughter sick','family_care')
# 얀선(1980)의 판독: 142쪽(정화), 137쪽(약 만들기만 적힘)
add('Neferabu','Spring',4,15,4,'his daughter was purified','family_care')
add('Paherypedjet','Summer',3,3,4,'making medicine','remedies')
def men(r):
    """사유 표현 속 이름. 어떤 사람인지는 worker_alias로 해소한다."""
    if r is None: return None
    if r=='WITH AAPEHTI': return 'Aapehti'
    if r=='WITH HOREMWIA': return 'Horemwia'
    if r.startswith('WITH KHONS'): return 'Khons'
    if r=='DRINKING WITH KHONSU': return 'Khonsu'
def resolve(n):
    x=c.execute('SELECT worker_id FROM worker WHERE name=? UNION SELECT worker_id FROM worker_alias WHERE alias=?',(n,n)).fetchone()
    return x[0] if x else None
def link():
    c.execute('UPDATE reading SET mentions_worker_id=NULL')
    for rid,reason in c.execute('SELECT reading_id,reason FROM reading WHERE source_id=1').fetchall():
        n=men(reason)
        if n: c.execute('UPDATE reading SET mentions_worker_id=? WHERE reading_id=?',(resolve(n),rid))
link()
c.commit()
q=lambda s,*a:c.execute(s,a).fetchall()
print('total',q('SELECT COUNT(*),COUNT(DISTINCT worker_id),COUNT(DISTINCT day_no) FROM absence'))
print('per worker',q('SELECT w.name,COUNT(a.absence_id) n FROM worker w LEFT JOIN absence a USING(worker_id) GROUP BY 1 ORDER BY n DESC,1'))
print('category',q("SELECT COALESCE(category,'(none)'),COUNT(*) FROM reading WHERE source_id=1 GROUP BY 1 ORDER BY 2 DESC"))
print('ILL exact',q("SELECT COUNT(*) FROM reading WHERE source_id=1 AND reason='ILL'"))
print('uncertain',q('SELECT COUNT(*) FROM absence WHERE uncertain=1'))
# 빈칸 분석: 같은 사람의 직전 행이 병
print('blank after own illness',q("""WITH o AS (SELECT a.worker_id,a.absence_id,r.category,LAG(r.category) OVER(PARTITION BY a.worker_id ORDER BY a.absence_id) p FROM absence a JOIN reading r USING(absence_id) WHERE r.source_id=1)
 SELECT COUNT(*) FROM o WHERE category IS NULL AND p LIKE 'own_illness%'"""))
print('blank by prev',q("""WITH o AS (SELECT a.worker_id,a.absence_id,r.reason,LAG(r.reason) OVER(PARTITION BY a.worker_id ORDER BY a.absence_id) p FROM absence a JOIN reading r USING(absence_id) WHERE r.source_id=1)
 SELECT p,COUNT(*) FROM o WHERE reason IS NULL GROUP BY 1 ORDER BY 2 DESC"""))
# 순서
print('order violations',q("""WITH o AS (SELECT w.name,a.absence_id,a.season,a.month,a.day,a.seq_no,LAG(a.seq_no) OVER(PARTITION BY a.worker_id ORDER BY a.absence_id) p FROM absence a JOIN worker w USING(worker_id))
 SELECT name,season,month,day FROM o WHERE seq_no<p"""))
print('span',q('SELECT MIN(seq_no),MAX(seq_no) FROM absence'))
print('first/last',q('SELECT season,month,day FROM absence ORDER BY seq_no LIMIT 1'),q('SELECT season,month,day FROM absence ORDER BY seq_no DESC LIMIT 1'))
# 교차 검증
print('cross WITH X',q("""SELECT w.name,r.reason,a.season,a.month,a.day,x.absence_id IS NOT NULL,rx.reason FROM reading r JOIN absence a USING(absence_id) JOIN worker w USING(worker_id)
 LEFT JOIN worker_alias al ON al.alias=(CASE WHEN r.reason LIKE 'WITH AAPEHTI' THEN 'Aapehti' WHEN r.reason LIKE 'WITH KHONS%' THEN 'Khons' END)
 LEFT JOIN worker tw ON tw.worker_id=al.worker_id OR tw.name=(CASE WHEN r.reason='WITH HOREMWIA' THEN 'Horemwia' WHEN r.reason LIKE 'WITH AAPEHTI' THEN 'Aapehti' WHEN r.reason LIKE 'WITH KHONS%' THEN 'Khons' END)
 LEFT JOIN absence x ON x.worker_id=tw.worker_id AND x.day_no=a.day_no LEFT JOIN reading rx ON rx.absence_id=x.absence_id AND rx.source_id=1
 WHERE r.source_id=1 AND (r.reason IN('WITH AAPEHTI','WITH HOREMWIA') OR r.reason LIKE 'WITH KHONS%') ORDER BY w.name,a.seq_no"""))
print('busiest',q("SELECT season,month,day,COUNT(*) n FROM absence GROUP BY day_no ORDER BY n DESC,seq_no LIMIT 8"))
print('pairs same day',q('SELECT COUNT(*) FROM absence a JOIN absence b ON a.day_no=b.day_no AND a.worker_id<b.worker_id'))
print('brewing dates',q("SELECT season,month,day,COUNT(*) FROM absence a JOIN reading r USING(absence_id) WHERE r.reason='BREWING BEER' GROUP BY day_no ORDER BY MIN(seq_no)"))
print('Penduauu-Khons',q("""SELECT a.season,a.month,a.day,wa.name,ra.reason,wb.name,rb.reason FROM absence a JOIN absence b ON a.day_no=b.day_no AND a.worker_id<b.worker_id JOIN worker wa ON wa.worker_id=a.worker_id JOIN worker wb ON wb.worker_id=b.worker_id
 LEFT JOIN reading ra ON ra.absence_id=a.absence_id AND ra.source_id=1 LEFT JOIN reading rb ON rb.absence_id=b.absence_id AND rb.source_id=1
 WHERE wa.name IN('Penduauu','Khons') AND wb.name IN('Penduauu','Khons') OR (a.season='Summer' AND a.month=2 AND a.day IN(7,8) AND (wa.name IN('Neferabu','Hehnekhu') AND wb.name IN('Neferabu','Hehnekhu')))"""))
print('conflict',q("SELECT s.title,r.reason FROM reading r JOIN source s USING(source_id) WHERE r.absence_id IN(SELECT absence_id FROM reading GROUP BY absence_id HAVING COUNT(*)>1)"))

CR="""SELECT COUNT(*), SUM(x.absence_id IS NOT NULL)
FROM reading r
JOIN absence a ON a.absence_id = r.absence_id
LEFT JOIN absence x
  ON x.worker_id = r.mentions_worker_id AND x.day_no = a.day_no
WHERE r.source_id = 1 AND r.mentions_worker_id IS NOT NULL"""
print('crossref',q(CR))
print('crossref misses',q("""SELECT w.name,r.reason,a.season,a.month,a.day FROM reading r JOIN absence a USING(absence_id) JOIN worker w USING(worker_id) LEFT JOIN absence x ON x.worker_id=r.mentions_worker_id AND x.day_no=a.day_no WHERE r.source_id=1 AND r.mentions_worker_id IS NOT NULL AND x.absence_id IS NULL"""))
print('cat query',q("SELECT category,COUNT(*) n FROM reading WHERE source_id=1 GROUP BY category ORDER BY n DESC"))
print('alt order violations I Spring first',q("""WITH o AS (SELECT a.day_no,LAG(a.day_no) OVER(PARTITION BY a.worker_id ORDER BY a.absence_id) p FROM absence a) SELECT COUNT(*) FROM o WHERE day_no<p"""))
print('density',270/(40*280),270/(40*76),'reason share',228/270)
print('zero',q('SELECT w.name FROM worker w LEFT JOIN absence a USING(worker_id) WHERE a.absence_id IS NULL'))
print('reject test',end=' ')
try: c.execute("INSERT INTO absence(worker_id,side,season,month,day,day_no,seq_no) VALUES(1,'front','Autumn',1,1,1,1)")
except Exception as e: print(e)

print('crossref same person',q(CR))
c.execute("DELETE FROM worker_alias WHERE alias='Khonsu'"); link()
print('crossref separate persons',q(CR))
c.execute("INSERT INTO worker_alias VALUES('Khonsu',?)",(wid['Khons'],)); link(); c.commit()
print('all categories',q("SELECT COALESCE(category,'(none)'),COUNT(*) FROM reading WHERE source_id=1 GROUP BY 1 ORDER BY 2 DESC"))
rows=c.execute('SELECT worker_id,absence_id,day_no FROM absence ORDER BY worker_id,absence_id').fetchall()
for m in range(12):
    st=30*m+1; v=0; pw=pv=None
    for w,_,d in rows:
        x=(d-st)%360
        if w==pw and x<pv: v+=1
        pw,pv=w,x
    sn=('Spring','Winter','Summer')[m//4]
    print('start',sn,m%4+1,'violations',v)
print('Nakhtamun III Summer 21',q("SELECT r.raw_text,r.reason FROM absence a JOIN worker w USING(worker_id) JOIN reading r USING(absence_id) WHERE w.name='Nakhtamun' AND a.season='Summer' AND a.month=3 AND a.day=21 AND r.source_id=1"))
print('dead rows check',q('SELECT COUNT(*) FROM reading WHERE source_id=1 AND mentions_worker_id IS NOT NULL'))
