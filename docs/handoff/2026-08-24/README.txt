AVA 수정 파일 전달 (2026-08-24 작업분)
========================================

기준 커밋: 4e74b29 (feat: use configured LLMs for post-call summaries #620)

포함 파일 (레포 상대 경로 그대로):
  config/ai-agent.yaml            — 메인 설정 (8/24 19:56 수정)
  src/engine.py                   — 엔진 (8/24 20:27 수정)
  src/providers/openai_realtime.py — OpenAI Realtime 프로바이더 (8/24 20:26 수정)
  changes-2026-08-24.patch        — 위 3개 파일의 git diff (기준 커밋 대비 변경분만)

적용 방법 (둘 중 하나):
  1) 파일 통째로 교체: 레포 루트에 같은 경로로 덮어쓰기
     (단, 받는 쪽 체크아웃이 4e74b29 기준일 때만 안전)
  2) 패치 적용: git apply changes-2026-08-24.patch

주의:
  - .env(API 키 등 시크릿)는 포함하지 않았음. 별도 전달 필요 시 안전한 채널로.
  - 적용 후 docker compose up -d --build ai_engine 으로 재빌드 필요.
