from __future__ import annotations
import re

_PATTERNS :list [tuple [str ,re .Pattern ]]=[

("주민등록번호",re .compile (r"\b\d{6}\s*[-–]\s*[1-4]\d{6}\b")),

("학번",re .compile (r"(?<!\d)(19|20)\d{8}(?!\d)")),
("전화번호",re .compile (r"(?<!\d)01[016-9][-\s]?\d{3,4}[-\s]?\d{4}(?!\d)")),
("이메일",re .compile (r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")),
]

MASK ="[비식별]"

def scrub_input (text :str )->tuple [str ,list [str ]]:

    found :list [str ]=[]
    for label ,pat in _PATTERNS :
        if pat .search (text ):
            found .append (label )
            text =pat .sub (MASK ,text )
    return text ,found

def _eul_reul (word :str )->str :

    last =word [-1 ]
    if not ("가"<=last <="힣"):
        return "를"
    return "을"if (ord (last )-0xAC00 )%28 else "를"

def notice (found :list [str ])->str :

    if not found :
        return ""
    items =", ".join (found )
    return (f"입력에서 {items }{_eul_reul (found [-1 ])} 발견해 가렸습니다. "
    "이 시스템은 학수번호와 학년·학기만 있으면 동작하므로 "
    "개인정보를 적지 않으셔도 됩니다.")
