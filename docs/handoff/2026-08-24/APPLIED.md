# handoff.zip 적용 기록 (2026-08-25)

기준 커밋: `4e74b29` — 이 레포의 현재 HEAD와 동일하므로 코드 패치는 충돌 없이 적용됨.

## 적용됨 (working tree)

| 파일 | 상태 |
|---|---|
| `src/engine.py` | ✅ 적용 (patch clean apply, 전달본과 바이트 동일) |
| `src/providers/openai_realtime.py` | ✅ 적용 (patch clean apply, 전달본과 바이트 동일) |

적용 후 `python -m py_compile` 통과.

### 변경 내용 요약

**`src/providers/openai_realtime.py`**
1. `_emit_audio_done()` — egress pacer 드레인 대기 추가.
   OpenAI가 실시간보다 빠르게 오디오를 생성해 `response.done` 시점에 `_outbuf`에
   재생 안 된 오디오가 남아 있었고, 그대로 pacer를 끄면 응답 꼬리가 잘렸다
   (문장 중간 끊김). 이제 버퍼가 빌 때까지(최대 60s) 대기. barge-in/cancel
   경로는 `_outbuf`를 먼저 비우므로 즉시 통과.
2. Pacer emit loop — `sleep(0.02)` → **절대 deadline 기반 페이싱**.
   기존 방식은 루프 처리 비용만큼 누적 드리프트(관측 ~15%)가 생겨 다운스트림
   재생이 굶고 문장 중간에 공백이 생겼다. 밀리면 sleep을 건너뛰어 따라잡고,
   0.5s 이상 밀리면 deadline을 재동기화.

**`src/engine.py`**
3. **openai_realtime 에코 게이팅** — 기존엔 `google_live`만 게이팅했다.
   `barge_in.enabled == false`일 때 openai_realtime도 half-duplex 게이팅
   (재생 중 caller 오디오를 무음으로 치환). 우리 TTS 에코가 OpenAI server VAD의
   `speech_started`를 발화시켜 응답이 중간에 flush/cancel 되던 문제 해결.
4. **tail guard** — 게이팅 해제 판정을 `_agent_output_active_calls`(지터버퍼
   드레인 완료 시점) 기준으로 바꾸고, 해제 후에도 최소 600ms(`post_tts_end_protection_ms`)
   동안 무음 치환 유지. 텔레포니 왕복 지연만큼 늦게 도착하는 에코 차단용.
5. `PROVIDER CHUNK` INFO 로그 rate-limit (`seq <= 3 or seq % 50 == 0`).
   20ms마다 INFO 로깅이 이벤트 루프에 부하를 줘 재생 페이싱 드리프트에 기여.

## 적용 안 함 — `config/ai-agent.yaml`

**의도적으로 덮어쓰지 않았음.** 이 레포의 `config/ai-agent.yaml`은 이미
HEAD에서 크게 갈라진 로컬 작업본(당직 전용, 31KB → 7.7KB로 재작성)이다:

- `asterisk.app_name: ava-156-72` (전달본은 `ava-134-73`)
- `contexts.default` — 한국어 당직 greeting/prompt, PII 안내 문구
- `mcp.servers.danjik` — stdio MCP 툴 3종 (escalate_emergency / lookup_manual / file_intake)
- `profiles.default: telephony_responsive`, `openai_realtime_24k` 24kHz 경로

전달본은 강남구청 + 원격 Asterisk(`98.23.133.90`) 환경 기준이라 그대로 덮으면
위 당직 설정이 전부 사라진다. 전달본 전체는 `ai-agent.yaml.reference`,
diff는 `changes-2026-08-24.patch`에 보관.

### 로컬 config에 골라 반영할 후보

| 항목 | 전달본 | 현재 로컬 | 비고 |
|---|---|---|---|
| `barge_in.enabled` | `false` | `true` | ⚠ **위 3번 에코 게이팅은 `false`일 때만 동작한다.** 현재 로컬 설정에서는 해당 수정이 무효. |
| `providers.openai_realtime.turn_detection.threshold` | `0.8` | `0.5` | 에코 오인식 완화. 민원인 목소리가 안 잡히면 0.7 → 0.6 순으로 낮출 것 |
| `providers.openai_realtime.turn_detection.silence_duration_ms` | `1000` | `200` | 로컬이 훨씬 공격적 — 말 끊김 잦으면 올릴 것 |
| `input_gain_max_db` / `input_gain_target_rms` | `18` / `1400` | 미설정 | 인입 음성이 작아 STT 뭉개질 때. 문제 시 둘 다 `0` |
| `egress_pacer_enabled` | `true` | `true` | 이미 동일 |

## 적용 안 함 — `.env`

전달본에 시크릿은 포함되지 않았다 (README.txt 참조).

## 다음 단계

```
docker compose up -d --build ai_engine
```
