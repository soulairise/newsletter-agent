"""카카오 최초 인증 — 한 번만 실행한다. refresh_token 을 받아 낸다.

먼저 developers.kakao.com 에서:
  1) 애플리케이션 추가하기 → 앱 이름 아무거나
  2) 앱 키 → REST API 키 복사
  3) 카카오 로그인 → 활성화 ON
  4) 카카오 로그인 → Redirect URI 에  https://localhost  추가
  5) 카카오 로그인 → 동의항목 → '카카오톡 메시지 전송(talk_message)' 을 선택 동의로 설정
"""
import os, sys, requests

KEY = os.getenv("KAKAO_REST_API_KEY", "")
REDIRECT = "https://localhost"

if not KEY:
    sys.exit("KAKAO_REST_API_KEY 를 환경변수로 넣고 다시 실행하세요.")

if len(sys.argv) < 2:
    url = ("https://kauth.kakao.com/oauth/authorize"
           f"?client_id={KEY}&redirect_uri={REDIRECT}"
           "&response_type=code&scope=talk_message")
    print("\n① 아래 주소를 브라우저에 붙여 넣고 '동의하고 계속하기' 를 누르세요.\n")
    print(f"   {url}\n")
    print("② 그러면 https://localhost/?code=XXXXX 로 이동하며 '연결할 수 없음' 화면이 뜹니다.")
    print("   정상입니다. 주소창의 code= 뒤 값만 복사하세요.\n")
    print("③ 그 값을 넣어 다시 실행하세요:\n")
    print("   uv run python kakao_auth.py <붙여넣은_코드>\n")
    sys.exit(0)

r = requests.post("https://kauth.kakao.com/oauth/token", data={
    "grant_type": "authorization_code", "client_id": KEY,
    "redirect_uri": REDIRECT, "code": sys.argv[1],
}, timeout=20)
if r.status_code != 200:
    sys.exit(f"실패 {r.status_code}: {r.text[:300]}")
d = r.json()
print("\n✅ 발급 성공. 아래 값을 안전한 곳에 저장하세요.\n")
print(f"   KAKAO_REFRESH_TOKEN={d['refresh_token']}\n")
print(f"   (access_token 은 {d['expires_in']//3600}시간, refresh_token 은 "
      f"{d.get('refresh_token_expires_in', 0)//86400}일 뒤 만료됩니다)\n")
