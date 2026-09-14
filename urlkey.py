"""기사 주소를 중복 판정용 키로 정규화한다.

기존 방식은 link.split("?")[0] 로 쿼리를 통째로 잘랐는데,
국내 언론사는 기사 번호를 쿼리에 넣는다(?idxno=442281).
그래서 한 매체의 50건이 1건으로 뭉개졌다.

→ 추적용 꼬리표만 골라서 떼고 나머지 쿼리는 보존한다.
"""
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

# 명백한 추적 파라미터만 제거한다. 모르는 것은 남긴다.
TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {
    "fbclid", "gclid", "dclid", "msclkid", "igshid", "twclid", "ttclid",
    "mc_cid", "mc_eid", "_ga", "_gl", "yclid", "wbraid", "gbraid",
    "ref_src", "ref_url", "spm", "scid", "trk", "trkCampaign",
}


def canonical(url: str) -> str:
    if not url:
        return ""
    p = urlsplit(url.strip())
    keep = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
            if not k.lower().startswith(TRACKING_PREFIXES) and k.lower() not in TRACKING_KEYS]
    # 호스트는 소문자, www. 는 떼고, 조각(#)은 버린다
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    # http/https 차이로 같은 글이 두 번 들어오는 것을 막는다
    path = p.path.rstrip("/") or "/"
    return urlunsplit(("https", host, path, urlencode(keep), ""))
