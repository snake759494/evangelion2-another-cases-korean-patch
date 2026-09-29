# 기술 메모

## 준비
1. `python tools/extract_iso.py 원본.iso work/iso`
2. EBOOT 복호화: 키(C0CB167C)가 `eboot_decrypt.exe`에 없어 PPSSPP의 `DumpDecryptedEboots`로 얻은 `ULJS00064_USER_MAIN.BIN`을 `work/eboot_plain.bin`으로 쓴다. 재배치형 ELF(seg0 vaddr 0 → 파일 +0x80, seg1 vaddr 0x1daa00 → 파일 0x1daa80).
3. `python tools/unpack_all.py` — 모든 `.har`/`.zpt`를 `work/unp/`로 해제
4. `python tools/extract.py` → `translation/unique_ja.json`, `translation/batches/bNNN.json`
5. `python tools/ebootstr.py` → EBOOT 문자열(재배치로 참조되는 것만) → `translation/batches/eNNN.json`

## 빌드
`python tools/build.py 출력.iso`

## 아카이브
- `.har` (`tools/har.py`): `HGAR`, u16 ver, u16 개수, u32 오프셋[개수], 엔트리 = 이름 12바이트 + u32 플래그 + u32 크기 + 데이터(4바이트 정렬). 플래그 최상위 비트 = 압축.
- 압축(`.zpt`, har 압축 멤버): u32 원본 크기 + raw deflate.
- `BIND` (`tools/bind.py`, imtext.bin): 헤더(0x2000) 안에 블록 크기 표, 블록은 0x800 정렬.
- 게임은 파일을 `disc0:/sce_lbn0x%x_size0x%x`로 연다. 부팅 시 스레드가 디렉터리를 읽어 LBN 표를 만들기 때문에 파일이 커져 ISO 끝으로 옮겨져도 된다.

## 텍스트
- 인코딩은 SJIS. `TEXT` 블록(`tools/textfmt.py`): `TEXT`, n, 표 오프셋, 데이터 오프셋, (키, 오프셋)×n, 레코드 = u32, u32, 문자열 NUL, 4바이트 정렬. imtext.bin(대사 24,576개), free/f2info·f2tuto.
- `.evs` 스크립트(`tools/evs.py`): `.EVS`, n, 라벨 오프셋[n], 명령 = u16 op, u16 길이, 본문(4바이트 정렬). op 0x01 = 대사(u32 화자, u32 플래그, u32 id, 문자열), op 0x95 = 선택지(`／` 구분). 명령 안에 절대 주소가 없어 라벨 표만 다시 계산하면 된다.
- 제어 코드: `$m` `$n` `$x` `$d` `$f` `$a` `$b` `$o` `$p`(이름 변수), `%1i`(버튼), `▽`(대기).
- EBOOT 문자열은 제자리 덮어쓰기(다음 비0 바이트 전까지). 다른 문자열이 꼬리를 공유하는 73개와 바이너리 오인식 5개는 원문 유지.

## 폰트
- 게임은 libfont(sceFont)로 시스템 폰트 jpn0.pgf를 연다. EBOOT 0x652c0~에서 `sceFontFindOptimumFont`/`sceFontOpen` 대신 `sceFontOpenUserFile(lib, 경로)`를 부르도록 바꿨다(NID 0xA834319D → 0x57FCB733, 경로는 `bal`로 PC 상대 계산 → 재배치 불필요, 없앤 `jal`의 R_MIPS_26 재배치는 타입 0으로).
- 경로 문자열은 디버그용 `host0:../../cdimg/` 버퍼(0x2534c4)에 넣는다. 일반 경로는 PPSSPP에서 열리지 않아 LBN 경로(`disc0:/sce_lbn…`)를 쓴다.
- `USRDIR/kfont.pgf` (`tools/pgf.py`, `tools/mkfont.py`): 리비전 2 PGF. 한글은 **나눔스퀘어네오 Bold** 17px(원본 FTT-NewRodin Pro DB와 획 굵기·크기 비교), 진행폭 18px(원본 전각과 동일). 기호·가나는 jpn0 글리프 복사.
- 게임이 GetFontInfo의 maxGlyphWidth/Height로 글리프 캐시 버퍼를 잡으므로 헤더의 두 값은 jpn0 값(19×20)을 유지해야 한다(작으면 글자가 깨짐).
- 한글 코드: SJIS 한자 자리(0x889F~)에 사용된 한글 음절을 배정하고, EBOOT의 SJIS→유니코드 표(데이터 세그먼트 +0x51160, 구간표 +0x5485c)의 해당 항목을 한글 유니코드로 바꾼다. 번역되지 않고 남는 문자열에 쓰인 한자 코드는 배정에서 뺀다.
- 표의 0x7E는 U+203E(윗줄)이므로 번역문의 `~`는 `～`(대사) 또는 `-`(EBOOT)로 바꾼다.

## 이미지
- `HGPT` (`tools/hgpt.py`): 프레임 표(0x10: 개수, 형식, 이름 8바이트, (x,y,w,h)…) + `ppd` 블록(형식 0x13 8bpp / 0x14 4bpp, 폭·높이, 버퍼 폭·높이, 크기) + 픽셀(항상 PSP 스위즐) + `ppc` 16바이트 헤더 + RGBA 팔레트(알파 0x80 = 불투명).
- `tools/imgko.py` + `translation/images/*.json`: 영역별로 원본 글자를 지우고 원본의 글자색(행별)·테두리·글로를 추출해 한글을 그린 뒤 원래 팔레트로 양자화. 명조풍은 서울한강체, 고딕풍은 나눔스퀘어네오.

## 테스트
PPSSPP 원격 디버거(`tools/ppsspp_rpc.py`, `tools/shot.py`), `tools/goscn.sh ISO 이름`(부팅→시나리오 선택). 에뮬레이터는 다른 세션과 `D:/psp/ppsspp_win/LOCK.txt`로 번갈아 쓰고 끝나면 `tools/emu_release.sh`.
