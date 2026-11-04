# EA5634 결근 기록 데이터베이스

보고서 「무엇을, 어떤 순서로 적을 것인가: 고대 이집트의 결근 기록과 데이터베이스」(컴퓨터소프트웨어학부 이강유)에서 사용한 코드와 데이터입니다.

영국박물관이 소장한 결근 기록 도편 EA5634의 영어 번역을 SQLite 데이터베이스로 옮기고, 보고서에 나오는 집계와 검증 쿼리를 실행합니다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `parse_register.py` | 영국박물관 소장품 페이지(PDF 저장본)의 앞·뒷면 영어 번역을 읽어 결근 270행과 이름 40개를 `register.json`으로 저장한다. |
| `register.json` | `parse_register.py`의 결과. PDF가 없어도 이 파일로 `build_db.py`를 실행할 수 있다. |
| `build_db.py` | `register.json`으로 `absence.db`를 만들고, 보고서의 모든 집계와 검증 쿼리를 실행한다. |
| `results.txt` | 기준 실행 결과. 보고서의 수치는 모두 이 파일에서 나왔다. |

## 실행

Python 3.12와 Python에 내장된 SQLite를 사용했습니다. PDF에서 다시 추출하려면 `pdftotext`(Poppler 25.07)가 필요합니다.

```
python build_db.py > results.new.txt
```

`results.new.txt`가 `results.txt`와 같으면 재현된 것입니다. PDF에서부터 다시 만들려면 먼저 아래 명령을 실행합니다.

```
python parse_register.py data/EA5634_British_Museum.pdf
```

Windows에서는 한글 인코딩 오류를 막기 위해 환경 변수 `PYTHONUTF8=1`을 설정하고 실행합니다. PowerShell의 `>` 리다이렉트는 파일 앞에 BOM을 붙이고 줄바꿈을 CRLF로 바꾸므로, `results.txt`와는 글자 내용으로 비교해야 합니다.

## 입력 자료

- 입력 자료는 영국박물관 소장품 페이지(https://www.britishmuseum.org/collection/object/Y_EA5634)를 2026년 11월 3일에 PDF로 저장한 것입니다. 저작권 때문에 이 저장소에는 넣지 않았습니다. 보고서에 쓴 파일의 SHA-256은 `d8dfeecbcf69c1bb845fb3a32d240a7f6c3e7f23f18a84bb5e237e49e37906ca`입니다. 페이지가 바뀌었거나 다른 방식으로 저장하면 추출 결과가 달라질 수 있습니다.
- `register.json`의 번역 표현은 영국박물관 기록에서 온 것입니다.
- `build_db.py`에 넣은 함부르크대 해설, 얀선(Janssen, 1980)의 논문, 팟캐스트의 표현은 각 자료에서 짧게 인용한 것이며, 출처는 보고서의 참고문헌에 있습니다.
