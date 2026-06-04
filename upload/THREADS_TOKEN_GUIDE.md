# 스레드 (Threads) 토큰 발급 단계별 가이드

> 출처:
> - https://developers.facebook.com/docs/threads/get-started
> - https://developers.facebook.com/docs/threads/overview
>
> 본 가이드는 2025년 5월 시점 지식 기준입니다. Meta 정책은 자주 바뀌므로
> 화면 구성이 다르면 위 공식 문서를 우선 참고하세요.

---

## 0. 사전 조건 (먼저 확인)

- [ ] **폰스팟 광교점 인스타그램 계정이 이미 있다.** 스레드는 인스타 위에 만들어진 서비스이므로 IG 계정이 선행 조건.
- [ ] **그 인스타 계정으로 스레드도 가입돼 있다.** 안 되어 있으면 https://www.threads.net 에 인스타 계정으로 로그인해 스레드 프로필을 한 번 만들어 두세요.
- [ ] **Meta(페이스북) 개발자 계정.** 페이스북 일반 계정이 있으면 즉시 개발자로 전환 가능 (무료).

세 가지 다 되어 있어야 다음 단계 진행 가능.

---

## 1. Meta 앱 생성 (5분)

1. https://developers.facebook.com/apps/ 접속 → 우상단 **Create App** 클릭
2. **Use case 선택**: "Access the Threads API" 를 선택
   - 안 보이면 "Other" → 다음 단계에서 "Threads API" 권한을 추가하는 방식으로 진행 가능
3. **앱 이름**: `phonespot-uploader` 또는 식별 가능한 이름
4. **앱 연락 이메일**: 313jongmin@gmail.com (또는 본인 이메일)
5. **비즈니스 포트폴리오**: 없으면 "No business portfolio selected" 로 진행 가능
6. **Create App** → 비밀번호 재입력

생성되면 앱 대시보드로 이동.

---

## 2. Threads API 권한 추가

1. 좌측 메뉴 **App settings** → **Basic**
2. 다음 두 값을 메모해 두세요 (나중에 `.env` 에 입력):
   - **App ID** → `META_APP_ID`
   - **App Secret** → "Show" 클릭해서 확인 → `META_APP_SECRET`
3. 좌측 메뉴 **App Review** → **Permissions and Features** (또는 **Use Cases**)
4. 다음 두 권한이 "Standard Access" 로 사용 가능한지 확인:
   - `threads_basic` — 기본 프로필 읽기
   - `threads_content_publish` — 게시물 생성/게시
5. 보통 위 두 개는 별도 심사 없이 Standard Access 로 즉시 사용 가능 (단, 본인 계정에 대해서만)

---

## 3. 사용자 토큰 발급 (가장 까다로운 단계)

스레드 API 는 **User Access Token** 을 사용합니다. 두 가지 방법:

### 방법 A: User Token Generator (간단, 권장)

1. 앱 대시보드 좌측 메뉴 **Threads API** → **Get started** (또는 **Setup**)
2. 보이는 **User Token Generator** 또는 **Generate Token** 버튼 클릭
3. 인스타그램 계정으로 로그인 → 권한 동의 (위 두 권한 모두 체크)
4. 발급되는 토큰 복사 (이건 **short-lived = 1시간 짜리**)

### 방법 B: 직접 OAuth URL 호출

방법 A 버튼이 안 보이면 다음 URL 을 브라우저에서 열기:

```
https://threads.net/oauth/authorize
  ?client_id={META_APP_ID}
  &redirect_uri=https://example.com/auth
  &scope=threads_basic,threads_content_publish
  &response_type=code
```

→ 권한 동의 후 리다이렉트되면 URL 의 `?code=...` 파라미터 복사.

그 code 를 access_token 으로 교환:
```bash
curl -X POST "https://graph.threads.net/oauth/access_token" \
  -F "client_id={META_APP_ID}" \
  -F "client_secret={META_APP_SECRET}" \
  -F "grant_type=authorization_code" \
  -F "redirect_uri=https://example.com/auth" \
  -F "code={위에서_복사한_code}"
```

응답으로 `access_token` 과 `user_id` 가 옴.

---

## 4. Long-lived (60일) 토큰으로 교환

방법 A/B 모두 처음엔 short-lived (1시간) 토큰. 운영용으로는 60일짜리로 바꿔야 함:

```bash
curl -X GET "https://graph.threads.net/access_token" \
  -G \
  -d "grant_type=th_exchange_token" \
  -d "client_secret={META_APP_SECRET}" \
  -d "access_token={SHORT_LIVED_TOKEN}"
```

응답:
```json
{"access_token": "THQVJ...", "token_type": "bearer", "expires_in": 5183944}
```

이 `access_token` 이 60일짜리 long-lived 토큰. 이 값을 `.env` 의 `THREADS_ACCESS_TOKEN` 에 넣습니다.

만료 1주 전 동일 엔드포인트로 갱신 가능. (코드는 추후 `utils/token_refresh.py` 에 구현 예정)

---

## 5. 사용자 ID 확인

토큰 발급 시 `user_id` 가 응답에 같이 옵니다. 없으면 발급된 토큰으로 한 번 호출:

```bash
curl "https://graph.threads.net/v1.0/me?fields=id,username&access_token={LONG_LIVED_TOKEN}"
```

응답의 `"id"` 값이 `THREADS_USER_ID`.

---

## 6. .env 채우기

`upload/.env` 파일에 다음 네 값이 들어가야 합니다:

```dotenv
META_APP_ID=1234567890
META_APP_SECRET=abcdef123456...
THREADS_USER_ID=9876543210
THREADS_ACCESS_TOKEN=THQVJ...
```

`.env` 파일이 없으면:
```powershell
copy upload\.env.example upload\.env
```
로 템플릿을 복사한 뒤 위 값들을 채워주세요.

---

## 7. 발급 검증 (스모크 테스트)

토큰이 살아 있는지 확인 (게시는 아직 안 함):

```powershell
curl "https://graph.threads.net/v1.0/me?fields=id,username&access_token=YOUR_LONG_LIVED_TOKEN"
```

본인 사용자명이 응답으로 오면 OK. 401 에러면 토큰 만료 또는 권한 부족.

---

## 8. 자주 막히는 부분

| 증상 | 원인 | 해결 |
|---|---|---|
| `(#10) Application does not have permission for this action` | 권한 미허용 | App Review 에서 두 권한 추가 |
| `Invalid OAuth access token` | 토큰 만료 또는 오타 | 4단계 다시 진행 |
| 권한 동의 화면에 폰스팟 IG 계정이 안 보임 | 스레드 가입 안 됨 | https://threads.net 에 IG 계정으로 로그인해서 프로필 생성 후 재시도 |
| Use case 에 "Threads API" 가 없음 | 지역/계정 제한 가능 | "Other" 로 앱 만든 뒤 좌측 메뉴 **Add product** 에서 Threads API 추가 |

---

## 9. 다음 단계

위 7단계까지 완료해서 `.env` 에 네 값이 모두 채워지면 알려주세요.

그 다음:
1. 이미지 호스팅 방식 결정 (R2 vs GitHub Pages vs ngrok)
2. `upload/scripts/channels/threads.py` 의 STUB 을 실제 구현으로 교체
3. dry-run 으로 검증 → 실제 게시 1회 테스트
