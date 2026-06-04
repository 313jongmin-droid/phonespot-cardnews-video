# 코워크 이관 세팅 가이드

> 종민님 데스크톱에서 따라하시면 됩니다. 예상 소요시간: 30~40분

---

## 1단계: 이 패키지 압축 해제

다운받은 `cowork_migration.zip`을 다음 위치에 풀어주세요:

**Mac**: `~/Documents/phonespot_cardnews/`  
**Windows**: `C:\Users\[사용자명]\Documents\phonespot_cardnews\`

폴더 구조:
```
phonespot_cardnews/
├── PROJECT_INSTRUCTIONS.md    ← 코워크에 붙여넣을 지침
├── SETUP_GUIDE.md             ← 이 문서
├── logo.jpg                   ← 폰스팟 로고
├── scripts/
│   └── cardnews_renderer_v2.py  ← 렌더러 (최신 버전)
├── templates/
│   └── caption_template.md    ← SNS 캡션 템플릿
└── samples/
    └── ...                    ← 참고용 샘플
```

---

## 2단계: Claude Desktop 앱 확인

### Claude Desktop 앱 설치 (안 되어있으면)
1. https://claude.ai/download 접속
2. Mac용/Windows용 Desktop 앱 다운로드 → 설치
3. 실행 → 로그인 (Max 플랜 계정)

### Cowork 메뉴 확인
- 좌측 사이드바에서 **Chat / Code / Cowork** 탭 확인
- Cowork 탭 클릭 → 진입

---

## 3단계: 코워크 프로젝트 생성

1. Cowork 화면 좌측 하단 **"+ 프로젝트" 또는 "+Project"** 버튼 클릭
2. **"기존 폴더에서 가져오기" / "From existing folder"** 선택
3. 방금 압축 푼 `phonespot_cardnews/` 폴더 선택
4. 프로젝트 이름: `폰스팟 카드뉴스` 입력
5. **"생성"** 클릭

---

## 4단계: 프로젝트 지침(Instructions) 붙여넣기 ★ 가장 중요 ★

1. 프로젝트 생성 후 우측 또는 상단의 **"지침 / Instructions"** 버튼 클릭
2. `PROJECT_INSTRUCTIONS.md` 파일을 열어서 **"프로젝트 지침 (복사용)"** 섹션만 선택
   - 코드 블록 안의 내용만 (``` 로 감싸진 부분)
3. 해당 내용 전체 복사 (Ctrl/Cmd + A → C)
4. 코워크 Instructions 필드에 붙여넣기 (Ctrl/Cmd + V)
5. **"저장" / "Save"** 클릭

---

## 5단계: Pretendard 폰트 확인

카드뉴스 렌더링에 Pretendard 폰트가 필요합니다. 
코워크에 이 메시지를 보내세요:

```
Pretendard 폰트가 설치되어 있는지 확인하고, 없으면 설치해줘.
설치 후 scripts/ 폴더의 cardnews_renderer_v2.py를 
실행해서 작동 확인해줘.
```

Cowork가 자동으로:
- fontconfig 확인
- Pretendard 설치 (9종 OTF)
- 테스트 렌더링 실행

---

## 6단계: 첫 기사로 테스트

Cowork에 다음 메시지를 보내세요:

```
https://www.etnews.com/20260423000169
이 기사로 카드뉴스 만들어줘
```

Cowork가 자동으로:
1. 기사 본문 분석
2. 앵글 결정
3. 18장 PNG 렌더링 (3사이즈 × 6장)
4. captions.md 생성
5. `phonespot_cardnews/output/iphone18_spec_downgrade/` 폴더에 저장

---

## 7단계 (선택): 자동화 스케줄 설정

매일 아침 RSS로 자동 카드뉴스 생성하려면:

1. Cowork 좌측 **"예약 작업" / "Scheduled"** 클릭
2. **"새 작업"** 클릭
3. 프롬프트 입력:
```
디지털데일리, ZDNet, 뉴시스, 전자신문 RSS에서 
오늘자 스마트폰/통신 관련 신규 기사 중 
가장 화제성 있는 것 1개 골라서 카드뉴스 만들어줘.
결과는 output/ 폴더에 저장.
```
4. 주기 설정: 매일 오전 8시
5. 저장

⚠️ 주의: 노트북이 켜져 있어야 실행됩니다.

---

## 트러블슈팅

### 문제: Cowork 탭이 안 보여요
→ Settings > Cowork 에서 **활성화** 확인

### 문제: 폰트가 이상하게 나와요
→ Pretendard 재설치 요청:
```
/usr/share/fonts/pretendard/ 에 Pretendard 폰트 9종을 
GitHub에서 다운받아 설치하고 fc-cache -fv 실행해줘.
```

### 문제: 이미지가 저장 안 돼요
→ 폴더 접근 권한 확인:
```
Settings > Cowork > Connected folders 에 
phonespot_cardnews 폴더가 있는지 확인
```

### 문제: 이전에 작업한 파일 구조를 모르겠어요
→ `samples/` 폴더의 이전 결과물 참고하거나 이렇게 물어보세요:
```
samples/ 폴더의 이전 카드뉴스 구조를 분석해서 
같은 방식으로 만들어줘.
```

---

## 이관 후 Claude.ai 웹 대화는 어떻게?

- **대화 종료 가능**: 여기 대화는 끝내셔도 됩니다
- **메모리는 유지**: Claude의 기억(로고 위치, 기사체 포맷 등)은 
  Anthropic 계정 단위로 유지되므로 Cowork에서도 참고됩니다
- **다만** Cowork 프로젝트 지침이 최우선이므로 여기 지침을 
  꼼꼼히 붙여넣으시면 됩니다

---

## 체크리스트

이관 완료 기준:

- [ ] Claude Desktop 앱 설치 완료
- [ ] Cowork 탭 진입 가능
- [ ] 프로젝트 "폰스팟 카드뉴스" 생성됨
- [ ] PROJECT_INSTRUCTIONS 붙여넣기 완료
- [ ] Pretendard 폰트 설치 확인
- [ ] 첫 기사 테스트 성공
- [ ] output 폴더에 PNG·captions 확인됨

모두 체크되면 이관 성공입니다.
