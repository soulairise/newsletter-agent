"""카카오톡 '나에게 보내기' 발행 경로.

카카오는 디스코드 웹훅과 달리 OAuth 가 필요하다.
  · access_token  — 6시간 만료
  · refresh_token — 약 2개월 만료 (이게 자동화의 발목을 잡는다)

매 실행마다 refresh_token 으로 access_token 을 새로 받아 쓴다.
refresh_token 이 갱신되어 돌아오면 화면에 찍어 준다 — 그때 Secret 을 바꿔야 한다.
"""
from __future__ import annotations
import os
import requests

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
TEXT_MAX = 200          # 기본 텍스트 템플릿의 본문 상한


def refresh_access_token() -> tuple[str, str | None]:
    """refresh_token 으로 access_token 을 받는다. 새 refresh_token 이 오면 함께 돌려준다."""
    rest_key = os.environ["KAKAO_REST_API_KEY"]
    refresh = os.environ["KAKAO_REFRESH_TOKEN"]
    r = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": rest_key,
        "refresh_token": refresh,
    }, timeout=20)
    r.raise_for_status()
    d = r.json()
    return d["access_token"], d.get("refresh_token")


def build_text(brand: str, items: list[dict]) -> str:
    """카톡 기본 템플릿은 본문 200자 제한 → 제목만 목록으로 보낸다."""
    from datetime import datetime
    head = f"🧘 {brand} · {datetime.now().strftime('%m/%d')}\n"
    if not items:
        return head + "오늘은 조용합니다."
    lines = [f"{i}. {a['headline']}" for i, a in enumerate(items, 1)]
    body = head + "\n".join(lines)
    return body[:TEXT_MAX - 3] + "..." if len(body) > TEXT_MAX else body


def send(brand: str, items: list[dict]) -> tuple[int, str]:
    """나에게 보내기. 첫 기사 링크를 대표 링크로 붙인다."""
    import json
    token, new_refresh = refresh_access_token()
    if new_refresh:
        print(f"   ⚠️ 새 refresh_token 발급됨 — GitHub Secret 을 갱신하세요:\n      {new_refresh}")

    link = items[0]["url"] if items else "https://github.com/soulairise/newsletter-agent"
    template = {
        "object_type": "text",
        "text": build_text(brand, items),
        "link": {"web_url": link, "mobile_web_url": link},
        "button_title": "첫 글 열기",
    }
    r = requests.post(SEND_URL,
                      headers={"Authorization": f"Bearer {token}"},
                      data={"template_object": json.dumps(template, ensure_ascii=False)},
                      timeout=20)
    return r.status_code, r.text[:200]
