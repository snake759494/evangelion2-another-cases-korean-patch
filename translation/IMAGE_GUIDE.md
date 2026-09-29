# 이미지 한글화 지침

도구: `tools/imgko.py` (읽어 볼 것). 게임 텍스처(HGPT)에서 지정한 영역의 일본어를 지우고 한국어를 원본 색·테두리·글로를 흉내 내어 다시 그린 뒤 원래 팔레트로 양자화한다.

## 규격 파일
`translation/images/<그룹>.json` = `{"<멤버경로>#<블록번호>": [영역, ...]}`
- 멤버경로: `work/unp/` 기준 (예: `game/title.har/menu    .hpt` — 이름 뒤 공백까지 그대로, `im/im003551.zpt.dec`)
- 블록번호: 보통 0 (`tools/hgpt.py`의 `blocks()` 순서)
- 영역: `{"box":[x0,y0,x1,y1], "ko":"한국어(\n 줄바꿈 가능)", "font":"serif|serifB|serifM|gothic|gothicH|gothicB|gothicR", "align":"center|left|right", "bg":"auto|clear|keep", "fit":0.8, "size":픽셀, "sx":1.0, "fill":[r,g,b,a], "edge":[r,g,b,a]}`
  - box 안의 원래 글자를 지운다(투명 배경이면 투명으로, 불투명이면 좌우 끝 열 색으로 행별 채움). `bg:"keep"`은 지우지 않고 위에 그림.
  - `ko`가 빈 문자열이면 지우기만 한다.
  - font: 명조풍(세리프) 원본 → `serif`(서울한강 EB)/`serifB`, 고딕풍 원본 → `gothic`(나눔스퀘어네오 ExtraBold)/`gothicH`(Heavy)/`gothicB`(Bold). 원본 굵기에 가장 가까운 것을 고른다.
  - `fit`: 글자 높이 / 영역 높이 비율(기본 0.8). 원본 글자 크기에 맞게 조정.
  - 글자색·테두리·글로는 자동 추출. 자동 결과가 이상하면 `fill`, `edge`로 직접 지정.
- 스프라이트 시트는 `python -c "import sys;sys.path.insert(0,'tools');import imgko;print(imgko.frames('<멤버경로>'))"`로 프레임 (x,y,w,h) 목록을 얻을 수 있다. 프레임 하나가 라벨 하나인 경우가 많다. 단, 글자만 바꾸고 아이콘·장식선·영문 부제(ENGLISH)는 영역에서 빼서 보존한다.

## 미리보기·검증
`python tools/imgko.py translation/images/<그룹>.json` → `work/imgprev/*.png` (왼쪽 원본, 오른쪽 결과, 2배). 반드시 열어서 확인하고, 글자 잘림·겹침·색 이상·장식 훼손이 없을 때까지 box/fit/font를 고친다.
원본 전체 모양은 `work/img/*.png`, 목록은 `work/img_text_catalog.json`(nidx 필드 = work/img_index_game_btl_free_im.json 인덱스, 거기 png 경로).

## 번역 원칙
- 용어는 `translation/GUIDE.md` 용어집을 따른다 (시나리오 선택, 데이터 로드, 옵션, 사도, 에바, 초호기 …).
- 공간이 좁으면 짧게. 가로 폭이 모자라면 sx로 장평을 줄이는 것은 0.75까지만, 그 이상이면 표현을 줄인다.
- 글자 조각 모음(atlas: 零/初/弐/号機/第 같은 한 글자 단위 조각을 게임이 조합하는 것)은 조합 결과가 자연스럽도록 각 조각을 한국어 조각으로 바꾼다(예: 号機→호기, 第→제, 使徒→사도, 零→영, 初→초, 弐→2, 参→3, 四→4).
- 인명: 碇シンジ 이카리 신지 등 용어집 기준.
