PhoneSpot CODEX_VIDEO_DESK 유지보수 안내

이제 영상 관련 일상 작업과 유지보수 도구는 이 폴더 안에서 관리합니다.

[기존 일상 작업]
01_PREPARE_GPT_PROMPTS.bat
- 신규 카드뉴스를 선택하고 필요한 GPT 일러스트 프롬프트를 준비합니다.

02_IMPORT_DOWNLOADS_AND_RENDER.bat
- 다운로드한 일러스트를 가져오고 최신 영상을 렌더링합니다.

03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat
- 새 일러스트 없이 최근 선택 영상을 다시 렌더링합니다.

15_SELECT_AND_RENDER_EXISTING.bat
- 원하는 기존 영상을 번호로 골라 다시 렌더링합니다.

[유지보수]
16_APPLY_CURRENT_BASELINE.bat
- 현재 합의된 Codex 영상 기준 기능을 다시 설치합니다.

17_APPLY_FIXED_CAPTION_RHYTHM.bat
- 고정 자막 크기와 개선된 화면 리듬 실험을 적용합니다.

18_ROLLBACK_FIXED_CAPTION_RHYTHM.bat
- 위 실험 결과가 좋지 않을 때 되돌립니다.

19_BACKUP_CURRENT_BASELINE.bat
- 현재 기준 파일을 백업합니다.

20_OPEN_MAINTENANCE.bat
- 세부 유지보수 도구 폴더를 엽니다.

21_DELETE_OLD_DOCUMENTS_CODEX.bat
- 이전 도구를 확인한 뒤 C:\Users\di898\Documents\Codex 폴더를 삭제합니다.
- 이전 완료 후 한 번만 사용합니다.

[보관 폴더]
RESULTS
- 최종 MP4와 업로드 문서를 보관합니다.

ILLUSTRATION_DROP
- 재사용 일러스트 라이브러리입니다.

BACKUPS
- 최신 기준 백업을 보관합니다.

MAINTENANCE
- 설치, 롤백, 점검 도구 모음입니다.

22_APPLY_KOREAN_CAPTION_COMPILER_V2.bat
- Installs the experimental Korean-aware caption splitter and Pretendard pixel line layout.

23_ROLLBACK_KOREAN_CAPTION_COMPILER_V2.bat
- Restores the previous caption layout if the V2 comparison render is not better.

24_APPLY_ILLUSTRATION_SCOUT_V2.bat
- Upgrades GPT Plus prompt scouting. Suggests up to three reusable editorial illustrations when semantic visual coverage is weak.

25_ROLLBACK_ILLUSTRATION_SCOUT_V2.bat
- Restores the previous illustration scout and tag DB seeds.

