# -*- coding: utf-8 -*-
"""Suggest reusable GPT Plus illustrations when the current visual map is weak.

CODEX_ILLUSTRATION_SCOUT_V21
CODEX_ILLUSTRATION_SCOUT_V2
- Grow a reusable editorial library instead of requesting article-specific art.
- Audit semantic quality gaps, not only missing predefined files.
- Limit each article to at most three new GPT Plus requests.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from codex_illustration_db import ensure_db, load_db, mark_requests, semantic_score, variant_tags, write_report


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARDNEWS = ROOT / "cardnews"
ILLUST_DIR = SHORTS / "public" / "assets" / "illustrations"
MAX_REQUESTS = 3

STYLE = """\ud55c\uad6d \ud734\ub300\ud3f0\u00b7IT \ub274\uc2a4 \uc1fc\uce20\uc6a9 \uace0\ud488\uc9c8 \uc5d0\ub514\ud1a0\ub9ac\uc5bc \uc77c\ub7ec\uc2a4\ud2b8.
\ubcf8\ubb38\uc758 \ud575\uc2ec \uc758\ubbf8\ub97c \ud55c\ub208\uc5d0 \uc774\ud574\ud560 \uc218 \uc788\uac8c \ud45c\ud604\ud558\ub418, \ud55c \uae30\uc0ac\uc5d0\uc11c\ub9cc \uc4f8 \uc218 \uc788\ub294 \uc138\ubd80 \ubb18\uc0ac\ub294 \ud53c\ud558\uc138\uc694.
\ud2b9\uc815 \ube0c\ub79c\ub4dc \ub85c\uace0, \uc81c\ud488 \ubaa8\ub378\uba85, \ub0a0\uc9dc, \uac00\uaca9, \uc778\ubb3c \uc774\ub984, \ub9e4\uc7a5 \uc774\ub984, \uc6cc\ud130\ub9c8\ud06c\ub294 \ub123\uc9c0 \ub9c8\uc138\uc694.
\ub2e8\uc21c \uc544\uc774\ucf58 \ud558\ub098\uac00 \uc544\ub2c8\ub77c \uc911\uc2ec \uc624\ube0c\uc81d\ud2b8\uc640 1~2\uac1c\uc758 \ubcf4\uc870 \uc694\uc18c\ub97c \ud65c\uc6a9\ud574 \uc644\uc131\ub3c4 \uc788\uac8c \uad6c\uc131\ud558\uc138\uc694.
\uc624\ub80c\uc9c0(#F74B0B), \uac80\uc815, \ud770\uc0c9\uc744 \uc911\uc2ec\uc73c\ub85c \uc0ac\uc6a9\ud558\uace0 \ubc1d\uc740 \uc0b4\uad6c\uc0c9(#FFF1EA) \ubc30\uacbd\uc744 \uc801\uc6a9\ud558\uc138\uc694.
\uae54\ub054\ud55c \uc678\uacfd\uc120, \uc790\uc5f0\uc2a4\ub7ec\uc6b4 \uae4a\uc774\uac10, \ucda9\ubd84\ud55c \ub514\ud14c\uc77c\uc744 \uac16\ucd98 \ud604\ub300\uc801\uc778 \uc5d0\ub514\ud1a0\ub9ac\uc5bc \uc2a4\ud0c0\uc77c.
\ud654\uba74 \ube44\uc728 4:3, \ud574\uc0c1\ub3c4 1024x768 PNG."""


RULES = [
    {
        "variant": "telecom_discount_compare",
        "groups": (("\uacf5\uc2dc\uc9c0\uc6d0\uae08", "\ub2e8\ub9d0 \uac00\uaca9", "\ucd9c\uace0\uac00"), ("\uc120\ud0dd\uc57d\uc815", "\uc6d4 \uc694\uae08", "\uc694\uae08 \ud560\uc778")),
        "reason": "\ub2e8\ub9d0 \uc989\uc2dc \ud560\uc778\uacfc \uc6d4 \uc694\uae08 \ud560\uc778\uc744 \ube44\uad50\ud558\ub294 \ud1b5\uc2e0\ube44 \ucf58\ud150\uce20\uc5d0 \ubc18\ubcf5 \ud65c\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc2a4\ub9c8\ud2b8\ud3f0\uc744 \uc911\uc2ec\uc73c\ub85c \uc88c\uce21\uc5d0\ub294 \ub2e8\ub9d0 \uac00\uaca9\uc774 \ud55c \ubc88\uc5d0 \ub0ae\uc544\uc9c0\ub294 \ud750\ub984, \uc6b0\uce21\uc5d0\ub294 \ub9e4\uc6d4 \uc694\uae08\uc774 \uc904\uc5b4\ub4dc\ub294 \ud750\ub984. \uc22b\uc790 \uc5c6\uc774 \ub450 \ud560\uc778 \ubc29\uc2dd\uc758 \ucc28\uc774\ub97c \uc2dc\uac01\uc801\uc73c\ub85c \ube44\uad50.",
    },
    {
        "variant": "plan_price_tier_compare",
        "groups": (("\uc694\uae08\uc81c",), ("\uace0\uac00", "\uc911\uc800\uac00", "\ubd84\uae30\uc810", "\uc6d0\ub300")),
        "reason": "\uc694\uae08\uc81c \uad6c\uac04\ubcc4 \ud61c\ud0dd \ube44\uad50\uc640 \uad6c\ub9e4 \uac00\uc774\ub4dc\uc5d0 \uc7ac\uc0ac\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc138 \ub2e8\uacc4\ub85c \ub098\ub258 \uc694\uae08\uc81c \uad6c\uac04\uc744 \uacc4\ub2e8\uc2dd\uc73c\ub85c \ubcf4\uc5ec\uc8fc\uace0, \uad6c\uac04\ubcc4\ub85c \ub2ec\ub77c\uc9c0\ub294 \ud560\uc778 \ud750\ub984\uc744 \uac04\uacb0\ud55c \ud654\uc0b4\ud45c\uc640 \uccb4\ud06c \ud45c\uc2dc\ub85c \ud45c\ud604. \uc2e4\uc81c \uac00\uaca9 \uc22b\uc790\ub294 \uc0ac\uc6a9\ud558\uc9c0 \uc54a\uae30.",
    },
    {
        "variant": "smishing_fake_link",
        "groups": (("\ubb38\uc790", "\uba54\uc2dc\uc9c0", "\ub9c1\ud06c", "URL"), ("\uc2a4\ubbf8\uc2f1", "\uc545\uc131 \uc571", "\uac00\uc9dc \ud398\uc774\uc9c0", "\ud074\ub9ad")),
        "reason": "\uc2a4\ubbf8\uc2f1, \uc545\uc131 \ub9c1\ud06c, \uac00\uc9dc \uc2e0\uccad\uc11c \uc8fc\uc758 \ucf58\ud150\uce20\uc5d0 \ubc94\uc6a9\uc73c\ub85c \uc4f8 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\ubb38\uc790 \uba54\uc2dc\uc9c0\uc758 \uc758\uc2ec\uc2a4\ub7ec\uc6b4 \ub9c1\ud06c\uac00 \uac00\uc9dc \uc6f9\ud398\uc774\uc9c0\uc640 \uc545\uc131 \uc571 \uc124\uce58 \uacbd\uace0\ub85c \uc5f0\uacb0\ub418\ub294 \ud750\ub984. \uc911\uc2ec \uc2a4\ub9c8\ud2b8\ud3f0, \uc704\ud5d8 \ud45c\uc2dc, \uc9e7\uc740 \uc5f0\uacb0\uc120\uc73c\ub85c \uad6c\uc131.",
    },
    {
        "variant": "impersonation_call",
        "groups": (("\uc0ac\uce6d", "\ubcf4\uc774\uc2a4\ud53c\uc2f1", "\uc0ac\uae30\ubc94"), ("\ud1b5\ud654", "\uc804\ud654", "\uac80\ucc30", "\uacbd\ucc30", "\uae08\uac10\uc6d0")),
        "reason": "\uae30\uad00\uc0ac\uce6d\ud615 \ubcf4\uc774\uc2a4\ud53c\uc2f1\uacfc \uc704\ud5d8 \ud1b5\ud654 \uc8fc\uc758 \ub274\uc2a4\uc5d0 \ubc18\ubcf5 \ud65c\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc2a4\ub9c8\ud2b8\ud3f0 \ud1b5\ud654 \ud654\uba74 \uc8fc\ubcc0\uc5d0 \uc704\uc870\ub41c \uacf5\uacf5\uae30\uad00 \ubc30\uc9c0\uc640 \uacbd\uace0 \ud45c\uc2dc. \ud2b9\uc815 \uae30\uad00 \ub85c\uace0 \uc5c6\uc774 \uc0ac\uce6d \uc804\ud654\uc758 \uc704\ud5d8\uc744 \ubcf4\uc5ec\uc8fc\ub294 \ubc94\uc6a9 \uad6c\uc131.",
    },
    {
        "variant": "emergency_account_freeze",
        "groups": (("\uc9c0\uae09\uc815\uc9c0", "\ud658\uc218", "\uc2e0\uace0"), ("\uc1a1\uae08", "\uac70\ub798 \uc740\ud589", "112", "1332", "1\uc2dc\uac04")),
        "reason": "\uc1a1\uae08 \uc0ac\uae30 \uc9c1\ud6c4 \ub300\uc751\uacfc \uace8\ub4e0\ud0c0\uc784 \uc548\ub0b4\uc5d0 \uc7ac\uc0ac\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc1a1\uae08 \ud654\uc0b4\ud45c\uac00 \uc740\ud589 \uacc4\uc88c \uc55e\uc5d0\uc11c \uae34\uae09 \uc815\uc9c0\ub418\ub294 \uc7a5\uba74. \uc791\uc740 \uc2dc\uacc4\uc640 \ubcf4\ud638 \ubc29\ud328\ub97c \ubcf4\uc870 \uc694\uc18c\ub85c \uc0ac\uc6a9\ud574 \ube60\ub978 \ub300\uc751\uc744 \uac15\uc870.",
    },
    {
        "variant": "fake_government_page",
        "groups": (("\uc815\ubd80", "\uacf5\uc2dd \uc0ac\uc774\ud2b8", "\uc2e0\uccad \uc548\ub0b4"), ("\uac00\uc9dc \ud398\uc774\uc9c0", "\ub611\uac19\uc774 \uc0dd\uae34", "\uc2a4\ubbf8\uc2f1")),
        "reason": "\uacf5\uacf5\uae30\uad00 \uc0ac\uce6d \uc6f9\uc0ac\uc774\ud2b8\uc640 \uac00\uc9dc \uc2e0\uccad \ud398\uc774\uc9c0 \uacbd\uace0\uc5d0 \ubc94\uc6a9\uc73c\ub85c \ud65c\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc11c\ub85c \ube44\uc2b7\ud55c \ub450 \uac1c\uc758 \ubaa8\ubc14\uc77c \uc6f9\ud398\uc774\uc9c0. \ud558\ub098\ub294 \uc548\uc804 \uccb4\ud06c, \ub2e4\ub978 \ud558\ub098\ub294 \uacbd\uace0 \ud45c\uc2dc\uc640 \uc8fc\uc758 \uc0c9\uc0c1\uc73c\ub85c \uad6c\ubd84. \ud2b9\uc815 \uc815\ubd80 \ub85c\uace0\ub098 URL\uc740 \ub123\uc9c0 \uc54a\uae30.",
    },
    {
        "variant": "personal_data_leak",
        "groups": (("\uc8fc\ubbfc\ubc88\ud638", "\uacc4\uc88c", "\uc778\uc99d\ubc88\ud638", "\uac1c\uc778\uc815\ubcf4"), ("\uc720\ucd9c", "\ud0c8\ucde8", "\uc545\uc131 \uc571", "\ub178\ucd9c")),
        "reason": "\uac1c\uc778\uc815\ubcf4 \uc720\ucd9c, \uc545\uc131 \uc571, \uacc4\uc815 \ud0c8\ucde8 \ub274\uc2a4\uc5d0 \ubc18\ubcf5 \ud65c\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc2a4\ub9c8\ud2b8\ud3f0 \uc548\uc758 \uac1c\uc778\uc815\ubcf4 \uce74\ub4dc, \uacc4\uc88c, \uc778\uc99d \ucf54\ub4dc\uac00 \ubc16\uc73c\ub85c \ube60\uc838\ub098\uac00\ub824\ub294 \uc21c\uac04\uc744 \ubcf4\ud638 \ubc29\ud328\uac00 \ub9c9\ub294 \uc7a5\uba74.",
    },
    {
        "variant": "official_site_check",
        "groups": (("\uacf5\uc2dd \uc0ac\uc774\ud2b8", "\uacf5\uc2dd \ud398\uc774\uc9c0", "\uc815\ubd8024", "mygov"),),
        "reason": "\uacf5\uc2dd \uc548\ub0b4 \ucc44\ub110 \ud655\uc778\uacfc \uc758\uc2ec \ub9c1\ud06c \ud53c\ud574 \uc608\ubc29\uc5d0 \uc7ac\uc0ac\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc2a4\ub9c8\ud2b8\ud3f0 \ube0c\ub77c\uc6b0\uc800\uc758 \uc548\uc804\ud55c \uacf5\uc2dd \ud398\uc774\uc9c0\ub97c \uccb4\ud06c \ud45c\uc2dc\uc640 \ubcf4\ud638 \ubc29\ud328\ub85c \ud655\uc778\ud558\ub294 \uc7a5\uba74. \ud2b9\uc815 URL\uacfc \ub85c\uace0\ub294 \uc0ac\uc6a9\ud558\uc9c0 \uc54a\uae30.",
    },
    {
        "variant": "device_data_transfer",
        "groups": (("\ub370\uc774\ud130", "\uc0ac\uc9c4", "\ub3d9\uc601\uc0c1", "\uc5f0\ub77d\ucc98", "\uba54\uc2dc\uc9c0"), ("\uc62e\uae30", "\uc774\uc804", "Smart Switch", "iCloud", "USB \ucf00\uc774\ube14")),
        "reason": "\uc2e0\uaddc \uae30\uae30 \uad50\uccb4, \uc2a4\ub9c8\ud2b8\uc704\uce58, \ud074\ub77c\uc6b0\ub4dc \uc774\uc804 \uac00\uc774\ub4dc\uc5d0 \ubc94\uc6a9\uc73c\ub85c \ud65c\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\ub450 \ub300\uc758 \uc2a4\ub9c8\ud2b8\ud3f0 \uc0ac\uc774\ub85c \uc0ac\uc9c4, \uc5f0\ub77d\ucc98, \uba54\uc2dc\uc9c0\ub97c \uc0c1\uc9d5\ud558\ub294 \uc791\uc740 \uce74\ub4dc\uac00 \uc548\uc804\ud558\uac8c \uc774\ub3d9\ud558\ub294 \uc7a5\uba74. \uc5f0\uacb0 \ucf00\uc774\ube14\uacfc \ud074\ub77c\uc6b0\ub4dc\ub97c \ubcf4\uc870 \uc694\uc18c\ub85c \ud45c\ud604.",
    },
    {
        "variant": "chat_backup_restore",
        "groups": (("\ub300\ud654", "\uba54\uc2e0\uc800", "\uce74\uce74\uc624\ud1a1", "\ucc44\ud305"), ("\ubc31\uc5c5", "\ubcf5\uc6d0", "\ub85c\uadf8\uc778")),
        "reason": "\uba54\uc2e0\uc800 \ub300\ud654 \ubc31\uc5c5, \ud734\ub300\ud3f0 \uad50\uccb4, \uacc4\uc815 \ubcf5\uc6d0 \uc548\ub0b4\uc5d0 \uc7ac\uc0ac\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\ucc44\ud305 \ub9d0\ud48d\uc120\uc774 \ub2f4\uae34 \uc2a4\ub9c8\ud2b8\ud3f0\uc5d0\uc11c \ud074\ub77c\uc6b0\ub4dc \ubc31\uc5c5\uc744 \uac70\uccd0 \uc0c8 \uc2a4\ub9c8\ud2b8\ud3f0\uc73c\ub85c \ubcf5\uc6d0\ub418\ub294 \ud750\ub984. \ud2b9\uc815 \uba54\uc2e0\uc800 \ub85c\uace0\ub294 \uc0ac\uc6a9\ud558\uc9c0 \uc54a\uae30.",
    },
    {
        "variant": "secure_app_reregistration",
        "groups": (("\uc778\uc99d\uc11c", "\uae08\uc735 \uc571", "\uacb0\uc81c \uc218\ub2e8", "\ubaa8\ubc14\uc77c \uc2e0\ubd84\uc99d", "\uae30\uae30 \uc778\uc99d"), ("\uc7ac\ub4f1\ub85d", "\uc7ac\ubc1c\uae09", "\uc0c8 \ud3f0", "\ub85c\uadf8\uc778", "\ub2e4\uc2dc \ub4f1\ub85d")),
        "reason": "\ud3f0 \uad50\uccb4 \ud6c4 \uae08\uc735 \uc571, \uc778\uc99d\uc11c, \uacb0\uc81c\uc218\ub2e8 \uc7ac\uc124\uc815 \uc548\ub0b4\uc5d0 \ubc18\ubcf5 \ud65c\uc6a9\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
        "concept": "\uc0c8 \uc2a4\ub9c8\ud2b8\ud3f0 \ud654\uba74 \uc548\uc5d0 \uc790\ubb3c\uc1e0, \uc778\uc99d \uce74\ub4dc, \uacb0\uc81c \uce74\ub4dc\uac00 \uc21c\ucc28\uc801\uc73c\ub85c \ub2e4\uc2dc \ub4f1\ub85d\ub418\ub294 \uc7a5\uba74. \uc548\uc804\ud55c \uc7ac\uc124\uc815 \ud750\ub984\uc744 \uccb4\ud06c \ud45c\uc2dc\ub85c \ud45c\ud604.",
    },

]



GAP_PROMPT_RULES = [
    {
        "variant": "transfer_path_steps",
        "keywords": ["데이터 어떻게", "데이터 이전", "옮기는", "전송", "이전", "Smart Switch", "스마트 스위치", "받기", "보내기", "자동으로 진행"],
        "reason": "기기 변경, 데이터 이전, 스마트 스위치, 아이클라우드 이전 안내에 범용으로 재사용할 수 있습니다.",
        "concept": "두 대의 스마트폰이 나란히 있고, 한쪽에서 다른 쪽으로 데이터 카드들이 부드럽게 이동하는 장면. 사진, 연락처, 앱을 상징하는 작은 카드와 진행 체크 표시를 사용하되 실제 앱 로고, 브랜드명, 긴 텍스트는 넣지 않기. 데이터 이전 절차를 직관적으로 표현.",
    },
    {
        "variant": "phone_setup_ready",
        "keywords": ["준비물", "두 폰", "새 폰", "기존 폰", "로그인", "USB", "케이블", "연결", "Wi-Fi", "와이파이"],
        "reason": "새 휴대폰 초기 세팅, 기존 폰 연결, 와이파이·케이블 준비 단계에 범용으로 쓸 수 있습니다.",
        "concept": "새 스마트폰과 기존 스마트폰이 책상 위에 놓여 있고, 와이파이 신호, USB 케이블, 체크리스트 카드가 함께 배치된 준비 장면. 특정 제조사 로고 없이 초기 세팅과 연결 준비를 깔끔하게 표현.",
    },
    {
        "variant": "transfer_interruption_warning",
        "keywords": ["중간에 꺼지면", "처음부터", "다시 시작", "실패", "끊기면", "배터리 50", "배터리"],
        "reason": "데이터 이전 실패, 배터리 부족, 연결 끊김, 재시도 안내에 반복 활용할 수 있습니다.",
        "concept": "스마트폰 화면 위에 멈춘 진행 바와 작은 경고 삼각형, 배터리 아이콘, 재시도 화살표가 있는 장면. 불안감을 과하게 키우지 않고 주의 안내처럼 보이게 구성하며, 숫자와 긴 문구는 넣지 않기.",
    },
    {
        "variant": "launch_event",
        "keywords": ["언팩", "키노트", "행사", "공개", "발표", "런던", "현지 시각"],
        "reason": "제품 공개 행사, 언팩, 키노트 뉴스에 반복 활용할 수 있습니다.",
        "concept": "밝은 무대 또는 발표 공간을 상징하는 추상적 행사 장면. 중앙에는 스마트폰 실루엣과 발표용 스포트라이트, 주변에는 작은 일정 카드와 관객석을 암시하는 단순 요소. 특정 브랜드 로고, 실제 장소명, 날짜, 인물 얼굴 없이 제품 공개 이벤트 분위기를 표현.",
    },
    {
        "variant": "release_calendar",
        "keywords": ["출시", "정식 출시", "사전예약", "예약", "일정", "초", "말", "D-", "날짜"],
        "reason": "출시일, 사전예약, 업데이트 일정, 행사 D-day 콘텐츠에 범용으로 쓸 수 있습니다.",
        "concept": "스마트폰 옆에 놓인 깔끔한 달력과 체크 표시, 작은 알림 벨, 진행 화살표를 조합한 일정 안내 장면. 숫자와 날짜는 읽히지 않게 추상화하고, 특정 모델명이나 브랜드 로고 없이 출시·예약 일정을 표현.",
    },
    {
        "variant": "cover_screen_widgets",
        "keywords": ["외부 디스플레이", "커버 화면", "위젯", "앱 호환", "닫은 상태", "플립"],
        "reason": "플립 외부 화면, 위젯, 잠금화면, 앱 호환성 주제에 재사용할 수 있습니다.",
        "concept": "접힌 형태의 스마트폰 외부 화면에 작은 위젯 카드들이 정돈되어 떠 있는 장면. 날씨, 알림, 음악 같은 범용 카드 형태만 사용하고 실제 앱 로고와 텍스트는 넣지 않기. 외부 화면 확장과 위젯 활용성을 직관적으로 표현.",
    },
    {
        "variant": "camera_controls",
        "keywords": ["카메라", "촬영", "줌", "HDR", "셔터", "필터", "렌즈", "속도", "2배"],
        "reason": "카메라 설정, 촬영 팁, 렌즈·줌·HDR 제어 콘텐츠에 재사용할 수 있습니다.",
        "concept": "스마트폰 카메라 화면을 추상화한 장면. 화면 위에 줌 다이얼, 셔터 버튼, 작은 토글 스위치, 렌즈 원형 그래픽을 배치해 카메라 수동 설정과 고급 촬영 제어를 표현. 텍스트와 실제 UI는 넣지 않기.",
    },
    {
        "variant": "module_install",
        "keywords": ["설치", "모듈", "스토어", "추가", "플러그인", "어시스턴트"],
        "reason": "앱 모듈 설치, 플러그인 추가, 기능 확장 가이드에 재사용할 수 있습니다.",
        "concept": "스마트폰 화면 위에 퍼즐 조각 형태의 모듈이 부드럽게 끼워지는 장면. 작은 다운로드 화살표와 체크 표시를 보조 요소로 사용해 기능 추가·모듈 설치를 표현. 실제 앱 이름과 스토어 로고는 넣지 않기.",
    },
    {
        "variant": "display_ratio_change",
        "keywords": ["화면 비율", "와이드", "넓어", "디스플레이", "화면이 더", "모형"],
        "reason": "화면 비율 변경, 디스플레이 확대, 폼팩터 변화 뉴스에 재사용할 수 있습니다.",
        "concept": "두 개의 스마트폰 화면 실루엣이 나란히 있고, 한쪽 화면이 더 넓게 확장되는 장면. 부드러운 확장 화살표와 화면 프레임을 사용해 비율 변화와 넓어진 디스플레이를 표현. 모델명과 숫자 표기는 넣지 않기.",
    },
    {
        "variant": "health_sensor_watch",
        "keywords": ["워치", "건강", "측정", "센서", "심박", "헬스"],
        "reason": "스마트워치 건강 측정, 센서 개선, 웨어러블 뉴스에 반복 활용할 수 있습니다.",
        "concept": "둥근 스마트워치 실루엣과 심박 파형, 작은 센서 점, 건강 체크 표시를 조합한 웨어러블 건강 측정 장면. 특정 브랜드 로고나 실제 수치 없이 건강 센서와 측정 기능을 표현.",
    },
]


def request_from_gap(gap: dict, existing: set[str], seen: set[str], section_name: str) -> dict | None:
    text = clean(gap.get("text", ""))
    value = text.lower()
    for rule in GAP_PROMPT_RULES:
        variant = rule["variant"]
        if variant in existing or variant in seen:
            continue
        if not any(keyword.lower() in value for keyword in rule["keywords"]):
            continue
        seen.add(variant)
        return {
            "variant": variant,
            "filename": f"{variant}.png",
            "section": gap.get("section") or section_name,
            "chunk_index": int(gap.get("chunk_index") or 0),
            "reason": rule["reason"],
            "quality_gap": f"weak fallback `{gap.get('variant')}` for: {text}",
            "tags": [],
            "prompt": STYLE + "\n\n핵심 콘셉트:\n" + rule["concept"],
            "status": "requested",
        }
    return None

def clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def sections(data: dict):
    yield "hook", data.get("hook", {})
    for idx, fact in enumerate(data.get("facts", []) or [], 1):
        yield f"fact_{idx}", fact
    yield "cta", data.get("cta", {})


def section_text(section: dict) -> str:
    return clean(" ".join([section.get("topic", ""), " ".join(section.get("caption_chunks", []) or []), " ".join(section.get("display_chunks", []) or []), section.get("tts", "")]))


def chunk_text(section: dict, idx: int) -> str:
    chunks = section.get("caption_chunks", []) or []
    displays = section.get("display_chunks", []) or []
    return clean(" ".join([(chunks[idx] if idx < len(chunks) else ""), (displays[idx] if idx < len(displays) else ""), section.get("topic", "")]))


def matches(rule: dict, text: str) -> bool:
    value = text.lower()
    return all(any(keyword.lower() in value for keyword in group) for group in rule["groups"])


def find_chunk(section: dict, rule: dict) -> int:
    chunks = section.get("caption_chunks", []) or []
    displays = section.get("display_chunks", []) or []
    for idx in range(max(len(chunks), len(displays))):
        if matches(rule, chunk_text(section, idx)):
            return idx
    flattened = [keyword for group in rule["groups"] for keyword in group]
    for idx in range(max(len(chunks), len(displays))):
        value = chunk_text(section, idx).lower()
        if any(keyword.lower() in value for keyword in flattened):
            return idx
    return 0


def current_visual(section: dict, idx: int) -> dict:
    visuals = section.get("chunk_visuals", []) or []
    if 0 <= idx < len(visuals) and isinstance(visuals[idx], dict):
        return visuals[idx]
    return {}


def preserve_hook_anchor(section_name: str, section: dict, idx: int) -> int:
    visuals = section.get("chunk_visuals", []) or []
    if section_name == "hook" and idx == 0 and len(visuals) > 1:
        return 1
    return idx


def quality_gap(db: dict, section: dict, idx: int) -> tuple[int, str]:
    visual = current_visual(section, idx)
    if visual.get("type") != "illust":
        return 0, f"current visual is {visual.get('type', 'missing')}; a reusable semantic illustration can improve this slot"
    variant = str(visual.get("value") or "")
    entry = (db.get("illustrations", {}) or {}).get(variant, {})
    score = semantic_score(chunk_text(section, idx), entry)
    return score, f"current illust:{variant} semantic score={score}; replace weak fallback with a reusable semantic asset"



def semantic_gap_rows(db: dict, data: dict) -> list[dict]:
    rows = []
    for section_name, section in sections(data):
        if section_name == "cta":
            continue
        visuals = section.get("chunk_visuals", []) or []
        chunks = section.get("caption_chunks", []) or section.get("display_chunks", []) or []
        for idx, visual in enumerate(visuals):
            if not isinstance(visual, dict) or visual.get("type") != "illust":
                continue
            variant = str(visual.get("value") or "")
            entry = (db.get("illustrations", {}) or {}).get(variant, {})
            score = semantic_score(chunk_text(section, idx), entry)
            if score <= 0:
                rows.append(
                    {
                        "section": section_name,
                        "chunk_index": idx,
                        "variant": variant,
                        "text": chunks[idx] if idx < len(chunks) else "",
                    }
                )
    return rows

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/codex_illustration_scout.py <slug>")
        return 2
    slug = sys.argv[1]
    ensure_db()
    output_dir = CARDNEWS / "output" / slug
    script_path = output_dir / "shorts_script.json"
    if not script_path.exists():
        print(f"[illustration_scout_v2] skip, missing: {script_path}")
        return 0

    data = json.loads(script_path.read_text(encoding="utf-8-sig"))
    db = load_db()
    existing = {path.stem for path in ILLUST_DIR.glob("*.png")} if ILLUST_DIR.exists() else set()
    requests = []
    seen = set()
    reserved_slots = set()

    for section_name, section in sections(data):
        if section_name == "cta":
            continue
        text = section_text(section)
        for rule in RULES:
            variant = rule["variant"]
            if variant in seen or variant in existing or not matches(rule, text):
                continue
            chunk_idx = preserve_hook_anchor(section_name, section, find_chunk(section, rule))
            slot = (section_name, chunk_idx)
            if slot in reserved_slots:
                continue
            score, gap = quality_gap(db, section, chunk_idx)
            if score >= 12:
                continue
            seen.add(variant)
            reserved_slots.add(slot)
            requests.append(
                {
                    "variant": variant,
                    "filename": f"{variant}.png",
                    "section": section_name,
                    "chunk_index": chunk_idx,
                    "reason": rule["reason"],
                    "quality_gap": gap,
                    "tags": variant_tags(variant),
                    "prompt": STYLE + "\n\n\ud575\uc2ec \ucf58\uc149\ud2b8:\n" + rule["concept"],
                    "status": "requested",
                }
            )
            if len(requests) >= MAX_REQUESTS:
                break
        if len(requests) >= MAX_REQUESTS:
            break

    uncovered_gaps = semantic_gap_rows(db, data)
    if len(requests) < MAX_REQUESTS and uncovered_gaps:
        for gap in uncovered_gaps:
            item = request_from_gap(gap, existing, seen, str(gap.get("section") or ""))
            if item is None:
                continue
            requests.append(item)
            if len(requests) >= MAX_REQUESTS:
                break

    payload = {
        "version": 2.1,
        "slug": slug,
        "policy": "suggest reusable GPT Plus assets when existing semantic coverage is weak; max three requests per video",
        "upload_dir": str(ILLUST_DIR),
        "requests": requests,
        "uncovered_gaps": uncovered_gaps,
    }
    json_path = output_dir / "codex_illustration_requests.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Codex Illustration Requests V2: {slug}",
        "",
        "\ud604\uc7ac \uc2dc\uac01 \ub9e4\ud551\uc758 \ubb38\ub9e5 \ud488\uc9c8\uc744 \uac80\uc0ac\ud574, \ub2e4\ub978 \uae30\uc0ac\uc5d0\uc11c\ub3c4 \uc7ac\uc0ac\uc6a9\ud560 \uc218 \uc788\ub294 \uc77c\ub7ec\uc2a4\ud2b8\ub9cc \ucd94\ucc9c\ud569\ub2c8\ub2e4.",
        "\uc601\uc0c1 \ud55c \ud3b8\ub2f9 \ucd5c\ub300 3\uac1c\ub9cc \uc81c\uc548\ud569\ub2c8\ub2e4.",
        "",
    ]
    if not requests:
        if uncovered_gaps:
            lines.append("새 프롬프트는 없지만, 문맥 적합도가 낮은 폴백 일러스트가 남아 있습니다. 현재 규칙으로는 범용 후보를 만들 수 없는 항목입니다.")
        else:
            lines.append("추가로 만들 범용 일러스트가 없습니다. 바로 렌더링해도 됩니다.")
    for idx, item in enumerate(requests, 1):
        lines.extend(
            [
                f"## {idx}. `{item['filename']}`",
                "",
                f"- \uc801\uc6a9 \uc704\uce58: `{item['section']}` \uccad\ud06c {item['chunk_index'] + 1}",
                f"- \ucd94\ucc9c \uc774\uc720: {item['reason']}",
                f"- \uad50\uccb4 \uadfc\uac70: {item['quality_gap']}",
                "",
                "```text",
                item["prompt"],
                "```",
                "",
            ]
        )
    if uncovered_gaps:
        lines.extend(["", "## 남아 있는 문맥 커버리지 경고", ""])
        for gap in uncovered_gaps[:8]:
            lines.append(f"- `{gap['section']}` 청크 {gap['chunk_index'] + 1}: `{gap['variant']}` -> {gap['text']}")
        lines.append("- 위 항목은 렌더링을 막지 않지만, 반복되면 범용 일러스트 규칙을 추가해야 합니다.")

    md_path = output_dir / "codex_illustration_requests.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    mark_requests(slug, requests)
    write_report()
    print(f"[illustration_scout_v2] report: {md_path}")
    print(f"[illustration_scout_v21] requests: {len(requests)}, uncovered_gaps: {len(uncovered_gaps)}")
    for item in requests:
        print(f"  - {item['filename']} -> {item['section']} chunk {item['chunk_index'] + 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
