부사수 PC 권한 점검 안내

부사수 PC가 네트워크 공유 폴더에서 영상 렌더링을 하려면 읽기 권한만으로는 부족합니다.
다음 위치에 쓰기/수정 권한이 필요합니다.

- CODEX_VIDEO_DESK
- cardnews\output
- shorts\public
- shorts\public\audio
- shorts\public\assets

문제가 생기면 부사수 PC에서 먼저 실행:
00_CHECK_ASSISTANT_PC_WRITE_ACCESS.bat

모두 OK가 나와야 01 프롬프트 준비, 02 가져오기+렌더, 15 렌더가 안정적으로 동작합니다.

권장 권한:
공유 권한: Change + Read
보안 권한: Modify

읽기 전용으로 우회하면 shorts_script.json, 오디오, public/assets, 결과 패키지가 PC별로 갈라져서
영상 결과와 프롬프트 상태가 서로 맞지 않을 수 있습니다.
