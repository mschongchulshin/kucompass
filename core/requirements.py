from __future__ import annotations
from dataclasses import dataclass ,field

from .roadmap import Course

@dataclass
class MajorRule :

    major_code :str
    total_required :int =36
    core_required :int =6
    other_field_min :int =18
    overlap_max :int =6
    coop_max :int =6
    note :str =""

DEFAULT_RULE =MajorRule ("_default",36 ,6 ,18 ,6 ,6 ,"일반 융합전공 기준")

RULES :dict [str ,MajorRule ]={
"정보보호융합전공":MajorRule (
"정보보호융합전공",36 ,0 ,18 ,6 ,12 ,
"전공선택 36학점 (필수/선택 구분 폐지, 2024-2학기부터)"),
"소프트웨어기술벤처융합전공":MajorRule (
"소프트웨어기술벤처융합전공",42 ,12 ,18 ,12 ,18 ,
"전공필수 12 + 전공선택 30 = 42학점, COOP 미인정"),
"뇌인지과학융합전공":MajorRule (
"뇌인지과학융합전공",36 ,9 ,18 ,6 ,6 ,
"전공필수 9 + 전공선택 27 = 36학점"),
}

def get_rule (major_sheet :str ,courses :list |None =None )->MajorRule :

    key =major_sheet .replace ("_교과목","")
    rule =RULES .get (key )
    if rule is not None :
        return rule
    if courses is None :
        return DEFAULT_RULE

    core_avail =sum (getattr (c ,"credits",0 )for c in courses
    if getattr (c ,"course_type","")=="전공필수")
    if core_avail ==0 :
        return MajorRule (key ,DEFAULT_RULE .total_required ,0 ,
        DEFAULT_RULE .other_field_min ,DEFAULT_RULE .overlap_max ,
        DEFAULT_RULE .coop_max ,"전공필수 구분 없음 (전공선택으로 이수)")
    if core_avail <DEFAULT_RULE .core_required :

        return MajorRule (key ,DEFAULT_RULE .total_required ,core_avail ,
        DEFAULT_RULE .other_field_min ,DEFAULT_RULE .overlap_max ,
        DEFAULT_RULE .coop_max ,
        f"전공필수 {core_avail }학점 (개설 과목 기준)")
    return DEFAULT_RULE

@dataclass
class RequirementResult :
    major_name :str
    total_required :int
    core_required :int
    earned_total :int
    earned_core :int
    remaining_total :int
    remaining_core :int
    overlap_allowed :int
    overlap_applied :int
    satisfied :bool
    unmet :list [dict ]=field (default_factory =list )
    unknown_codes :list [str ]=field (default_factory =list )
    duplicate_codes :list [str ]=field (default_factory =list )
    choice_extra :list [str ]=field (default_factory =list )
    missing_core :list [str ]=field (default_factory =list )
    missing_core_optional :bool =False
    other_major_codes :list [str ]=field (default_factory =list )
    unknown_names :list [str ]=field (default_factory =list )

    def notes (self )->list [str ]:
        out =[]
        if self .remaining_core and self .missing_core :
            if self .missing_core_optional :
                out .append (f"다음 전공필수 중 {self .remaining_core }학점을 더 들어야 합니다: "
                +", ".join (self .missing_core ))
            else :
                out .append ("남은 전공필수: "+", ".join (self .missing_core ))
        if self .duplicate_codes :
            out .append ("같은 학수번호를 두 번 이상 입력해 한 번만 셌습니다 ("
            +", ".join (self .duplicate_codes )+")")
        if self .choice_extra :
            out .append ("택1 과목은 1과목만 셌습니다 ("+", ".join (self .choice_extra )
            +" 제외, 추가 인정 여부는 학과 확인)")
        if self .unknown_codes :
            parts =[]
            if self .other_major_codes :
                parts .append ("다른 융합전공 과목 "+", ".join (self .other_major_codes ))
            rest =[c for c in self .unknown_codes if c not in self .other_major_codes ]
            if rest :
                parts .append ("확인되지 않는 학수번호 "+", ".join (rest ))
            out .append ("이 전공 교과목이 아니어서 제외했습니다: "+", ".join (parts ))
        if self .unknown_names :
            out .append ("인식하지 못한 과목명은 제외했습니다: "+", ".join (self .unknown_names ))
        return out

    def display_text (self )->str :
        parts =[
        f"{self .major_name }: 총 {self .total_required }학점 중 "
        f"{self .earned_total }학점 이수, {self .remaining_total }학점 남음"
        ]
        if self .core_required :
            parts .append (
            f"전공필수 {self .core_required }학점 중 {self .earned_core }학점 이수"
            +(f", {self .remaining_core }학점 부족"if self .remaining_core else " (충족)")
            )
        if self .overlap_applied :
            parts .append (f"제1전공 중복인정 {self .overlap_applied }/{self .overlap_allowed }학점 적용")
        parts +=[f"※ {n }"for n in self .notes ()]
        parts .append ("융합전공 졸업요건 충족"if self .satisfied else "융합전공 졸업요건 미충족")
        return ". ".join (parts )+"."

def check_requirements (
courses :list [Course ],
taken :list [str ],
rule :MajorRule ,
major_name :str ,
*,
first_major_courses :set [str ]|None =None ,
known_codes :set [str ]|None =None ,
unknown_names :list [str ]|None =None ,
)->RequirementResult :

    from .roadmap import count_taken

    by_code ={c .code :c for c in courses }
    taken_up :list [str ]=[]
    dups :list [str ]=[]
    for t in taken :
        code =str (t ).strip ().upper ()
        if not code :
            continue
        if code in taken_up :
            if code not in dups :
                dups .append (code )
            continue
        taken_up .append (code )

    valid =[t for t in taken_up if t in by_code ]
    unknown =[t for t in taken_up if t not in by_code ]
    counted ,extra =count_taken ([by_code [t ]for t in valid ],set (valid ))

    earned_total =sum (c .credits for c in counted )
    earned_core =sum (c .credits for c in counted if c .course_type =="전공필수")

    overlap_applied =0
    if first_major_courses :
        overlap_credits =sum (c .credits for c in counted if c .code in first_major_courses )
        overlap_applied =min (overlap_credits ,rule .overlap_max )

    remaining_total =max (0 ,rule .total_required -earned_total )
    remaining_core =max (0 ,rule .core_required -earned_core )

    missing :list [str ]=[]
    optional =False
    if remaining_core :
        done_groups ={c .choice_group for c in counted if c .choice_group }
        seen_groups :set [str ]=set ()
        slots :list [tuple [str ,int ]]=[]
        for c in courses :
            if c .course_type !="전공필수"or c .code in valid :
                continue
            if c .choice_group :
                if c .choice_group in done_groups or c .choice_group in seen_groups :
                    continue
                seen_groups .add (c .choice_group )
                members =[m for m in courses if m .choice_group ==c .choice_group ]
                slots .append ((" 또는 ".join (m .label for m in members ),c .credits ))
            else :
                slots .append ((c .label ,c .credits ))
        missing =[s for s ,_ in slots ]
        optional =sum (cr for _ ,cr in slots )>remaining_core

    unmet =[]
    if remaining_core :
        unmet .append ({"rule":"전공필수","detail":f"{remaining_core }학점 부족"})
    if remaining_total :
        unmet .append ({"rule":"총 이수학점","detail":f"{remaining_total }학점 부족"})

    return RequirementResult (
    major_name =major_name ,
    total_required =rule .total_required ,
    core_required =rule .core_required ,
    earned_total =earned_total ,
    earned_core =earned_core ,
    remaining_total =remaining_total ,
    remaining_core =remaining_core ,
    overlap_allowed =rule .overlap_max ,
    overlap_applied =overlap_applied ,
    satisfied =not unmet ,
    unmet =unmet ,
    unknown_codes =unknown ,
    duplicate_codes =dups ,
    choice_extra =[c .label for c in extra ],
    missing_core =missing ,
    missing_core_optional =optional ,
    other_major_codes =[u for u in unknown if known_codes and u in known_codes ],
    unknown_names =list (unknown_names or []),
    )
