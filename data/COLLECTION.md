# 이수체계도 수집 현황 (2026-07-28)

## 수집 완료 (3개 학과 · 이미지 4장)

| 학과 | URL | 간선 |
|---|---|---|
| 컴퓨터학과 | `info.korea.ac.kr/info/under/computer_flowmap.do` | 58 |
| 인공지능학과 | `info.korea.ac.kr/info/under/underai_flowmap.do` | 44 |
| 데이터과학과 | `info.korea.ac.kr/info/under/data_flowmap.do` | (학기격자형) |

수집 방법: `{slug}_flowmap.do` → `articleNo` 추출 → `?mode=view&articleNo=N`
→ `/_res/editor_image/*.png` 다운로드. **로그인 불필요.**

## 탐색했으나 없음

- **타 단과대 20곳** (전기전자·기계·통계·수학·물리·화학·경영·생명 등):
  이수체계도 페이지 자체가 없음
- **2차 탐색 27개 도메인**: `edu`, `socio`만 문자열 매칭됐으나
  실제 다이어그램 없음 (메뉴 라벨만 존재)
- **registrar 교육과정표**: iBook 뷰어라 크롤링 불가
- **hes 보건환경융합**: 404

## 결론

이수체계도는 **정보대학 전용 자산**이다. 전교 확대 수집은 불가능하므로
학수번호 백단위 규칙(L2, 검증 정확도 100%)이 나머지 커버리지를 담당한다.
