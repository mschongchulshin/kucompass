from __future__ import annotations
import re

def render_search_majors (r :dict )->str :
    if r .get ("error"):
        return r ["error"]
    head =[r ["scope_note"]]if r .get ("scope_note")else []
    cands =r .get ("candidates")or []
    if not cands :
        body =r .get ("display_text")or "조건에 맞는 융합전공을 찾지 못했습니다."
        if r .get ("scope_note"):
            body =body .replace (r ["scope_note"],"").strip ()
        return "\n\n".join (head +[body ])
    lines =["추천 융합전공"]
    for i ,c in enumerate (cands ,1 ):
        line =f"{i }. {c ['major_name']}"
        if c .get ("host_college"):
            line +=f" · {c ['host_college']}"
        line +=f" (상대 점수 {c ['score']:.2f})"
        lines .append (line )
        if c .get ("eligibility_note"):
            lines .append (f"   지원조건: {c ['eligibility_note']}")
    lines .append ("(상대 점수는 후보 전공끼리 비교한 값으로 1위가 1.00)")
    return "\n\n".join (head +["\n".join (lines )])

def render_query_curriculum (r :dict )->str :
    if r .get ("error"):
        return r ["error"]
    total =r .get ("total_count",0 )
    if not total :
        ft =r .get ("filter_applied")
        if ft :
            note =(f"{r ['major_name']}에는 '{ft }' 구분의 교과목이 없습니다.")
            if r .get ("total_unfiltered"):
                note +=f" (전체 교과목은 {r ['total_unfiltered']}개)"
            return note
        return f"{r ['major_name']} 교과목 정보를 찾을 수 없습니다."
    head =f"{r ['major_name']} 교과목 {total }개"
    body =r .get ("display_text","")
    return f"{head }\n{body }"if body else head

def render_check_requirements (r :dict )->str :
    if r .get ("error"):
        return r ["error"]
    lines =[f"{r .get ('major_name','')} 졸업요건"]if r .get ("major_name")else []
    lines +=[
    f"총 이수학점: {r ['total_required']}학점 중 {r ['earned_total']}학점 이수"
    f" ({r ['remaining_total']}학점 남음)"
    ]
    if r .get ("core_required"):
        core =(f"전공필수: {r ['core_required']}학점 중 {r ['earned_core']}학점 이수")
        core +=(" (충족)"if not r ["remaining_core"]
        else f" ({r ['remaining_core']}학점 부족)")
        lines .append (core )
    if r .get ("rule_note"):
        lines .append (f"규정: {r ['rule_note']}")
    for n in r .get ("notes")or []:
        lines .append (f"※ {n }")
    lines .append ("융합전공 졸업요건 충족"if r .get ("satisfied")else "융합전공 졸업요건 미충족")
    return "\n".join (lines )

def render_build_roadmap (r :dict )->str :
    if r .get ("error"):
        return r ["error"]
    lines =[f"{r ['major_name']} 수강 로드맵"]
    for t in r .get ("terms",[]):
        names =t .get ("names")or t ["courses"]
        label =t ["term"].replace ("/","학년 ")+"학기"
        lines .append (f"{label } ({t ['term_credits']}학점): "+", ".join (names ))
    taken =r .get ("taken_credits")or 0
    if taken :
        lines .append (
        f"이번 계획 {r ['total_credits']}학점 / {r ['total_terms']}학기 + 기이수 {taken }학점"
        f" (융합전공 졸업요건 {r ['target_credits']}학점)")
    else :
        lines .append (
        f"총 {r ['total_credits']}학점 / {r ['total_terms']}학기"
        f" (융합전공 졸업요건 {r ['target_credits']}학점)")
    lines .append (f"선수과목 순서 위배: {r ['prereq_violations']}건")
    if r .get ("completed_early")and r .get ("unplaced_count"):
        lines .append (f"(졸업요건을 채워 나머지 {r ['unplaced_count']}과목은 제외)")
    for w in r .get ("warnings",[])[:4 ]:
        lines .append (f"참고: {w }")
    return "\n".join (lines )

def render_get_syllabus (r :dict )->str :
    if not r .get ("available"):
        return r .get ("display_text","강의계획서를 조회할 수 없습니다.")
    ev =r .get ("evaluation")or {}
    lines =[f"{r .get ('course_name','')} 강의계획서"]
    if r .get ("overview"):
        lines .append (r ["overview"][:300 ])
    if ev :
        lines .append ("평가 비중: "+", ".join (f"{k } {v }%"for k ,v in ev .items ()))
    return "\n".join (lines )

RENDERERS ={
"search_majors":render_search_majors ,
"query_curriculum":render_query_curriculum ,
"check_requirements":render_check_requirements ,
"build_roadmap":render_build_roadmap ,
"get_syllabus":render_get_syllabus ,
}

def render_facts (trace :list [dict ])->str :

    blocks =[]
    for t in trace :
        fn =RENDERERS .get (t ["tool"])
        result =t .get ("result")
        if fn is None or not isinstance (result ,dict )or "expected_arguments"in result :
            continue
        text =fn (result )
        if text and text not in blocks :
            blocks .append (text )
    return "\n\n".join (blocks )

_NUM =re .compile (r"\d+")

_FACT_CTX =re .compile (r"(\d+)\s*(학점|과목|건|개)")

def extract_fact_numbers (trace :list [dict ])->set [str ]:

    out :set [str ]=set ()
    for t in trace :
        r =t .get ("result")
        if not isinstance (r ,dict ):
            continue
        for k ,v in r .items ():
            if isinstance (v ,(int ,float ))and not isinstance (v ,bool ):
                out .add (str (int (v )))
        for m in _NUM .finditer (str (r .get ("display_text",""))):
            out .add (m .group ())
    return out

_LINK =re .compile (r"\[([^\]]*)\]\((?:https?://|www\.)[^)]*\)|https?://\S+|www\.\S+")

_EMOJI =re .compile (
"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF"
"\U00002190-\U000021FF\U00002B00-\U00002BFF\uFE0F\u200D]+")

_INTERNAL =re .compile (
r"_교과목|search_majors|query_curriculum|check_requirements|build_roadmap|get_syllabus|툴")
_HAN =re .compile (r"[\u4e00-\u9fff]")
_HANGUL =re .compile (r"[가-힣]")
_LATIN_WORD =re .compile (r"[A-Za-z]{2,}")

def scrub_advice (advice :str ,trace :list [dict ])->tuple [str ,list [str ]]:

    advice =_LINK .sub (lambda m :m .group (1 )or "",advice )
    advice =_EMOJI .sub ("",advice )
    allowed =extract_fact_numbers (trace )
    korean =bool (_HANGUL .search (advice ))
    kept ,dropped =[],[]
    for sent in re .split (r"(?<=[.!?。])\s+|\n+",advice ):
        s =sent .strip ()
        if not s :
            continue
        bad =[m .group (1 )for m in _FACT_CTX .finditer (s )
        if m .group (1 )not in allowed ]
        foreign =korean and not _HANGUL .search (s )and len (_LATIN_WORD .findall (s ))>=2
        if bad or _INTERNAL .search (s )or _HAN .search (s )or foreign :
            dropped .append (s )
        else :
            kept .append (s )
    return " ".join (kept ).strip (),dropped

ADVICE_PROMPT ="""당신은 고려대 융합전공 상담 챗봇입니다.

아래 '조회 결과'는 이미 학생에게 그대로 보여집니다.
당신은 그 뒤에 붙일 짧은 조언이나 후속 질문만 작성하세요.

규칙:
- 학점 수, 과목 수 같은 숫자를 절대 다시 쓰지 마세요. 이미 위에 표시됩니다.
- 조회 결과를 반복하지 마세요.
- 2문장 이내, 존댓말.
- 정보가 부족하면 무엇이 필요한지 되물으세요."""
