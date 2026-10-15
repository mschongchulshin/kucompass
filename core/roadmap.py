from __future__ import annotations
from dataclasses import dataclass ,field

from .prereq import PrereqGraph

@dataclass
class Course :
    code :str
    name :str
    credits :int =3
    course_type :str ="전공선택"
    recommended :str |None =None
    choice_group :str |None =None
    offered :tuple [int ,...]|None =None
    prereqs :tuple [str ,...]=()
    prereq_note :str |None =None
    credits_known :bool =True

    @property
    def rec_order (self )->int |None :

        if not self .recommended or "/"not in str (self .recommended ):
            return None
        try :
            y ,s =str (self .recommended ).split ("/")
            return (int (y )-1 )*2 +int (s )
        except (ValueError ,TypeError ):
            return None

    @property
    def label (self )->str :
        code ="학수번호 미공개"if self .code .startswith ("TBD")else self .code
        return f"{self .name }({code })"

    def offered_in (self ,order :int )->bool :
        return not self .offered or ((order -1 )%2 +1 )in self .offered

@dataclass
class Term :
    label :str
    order :int
    courses :list [Course ]=field (default_factory =list )

    @property
    def credits (self )->int :
        return sum (c .credits for c in self .courses )

@dataclass
class Roadmap :
    terms :list [Term ]
    warnings :list [str ]
    unplaced :list [Course ]
    edges_used :int
    dropped :set [str ]=field (default_factory =set )
    completed_early :bool =False
    taken_credits :int =0

    @property
    def total_credits (self )->int :
        return sum (t .credits for t in self .terms )

    def display_text (self )->str :
        lines =[]
        for t in self .terms :
            if not t .courses :
                continue
            names =", ".join (c .label for c in t .courses )
            lines .append (f"{t .label .replace ('/','학년 ')}학기: {names } — {t .credits }학점")
        if self .unplaced :
            if self .completed_early :
                lines .append (
                f"(융합전공 졸업요건을 채워 나머지 {len (self .unplaced )}과목은 "
                f"로드맵에 넣지 않았습니다. 관심 과목은 추가로 수강 가능합니다.)")
            else :
                lines .append (f"배치하지 못한 {len (self .unplaced )}과목: "+
                ", ".join (c .name for c in self .unplaced [:5 ]))
        return "\n".join (lines )if lines else "배치할 과목이 없습니다."

def term_label (order :int )->str :

    return f"{(order -1 )//2 +1 }/{(order -1 )%2 +1 }"

def _eul_reul (word :str )->str :
    last =str (word ).strip ()[-1 :]or "x"
    if not ("가"<=last <="힣"):
        return "을(를)"
    return "을"if (ord (last )-0xAC00 )%28 else "를"

def count_taken (courses :list [Course ],taken :set [str ])->tuple [list [Course ],list [Course ]]:

    counted :list [Course ]=[]
    extra :list [Course ]=[]
    seen_groups :set [str ]=set ()
    for c in courses :
        if c .code not in taken :
            continue
        if c .choice_group :
            if c .choice_group in seen_groups :
                extra .append (c )
                continue
            seen_groups .add (c .choice_group )
        counted .append (c )
    return counted ,extra

def build_roadmap (
courses :list [Course ],
graph :PrereqGraph ,
*,
taken :set [str ]|None =None ,
start_order :int =5 ,
max_credits :int =18 ,
max_terms :int =8 ,
target_credits :int |None =None ,
required_core :int |None =None ,
)->Roadmap :

    taken ={c .upper ()for c in (taken or set ())}
    warnings :list [str ]=[]

    by_code ={c .code :c for c in courses }
    adj =graph .adjacency ()

    counted ,_ =count_taken (courses ,taken )
    taken_credits =sum (c .credits for c in counted )
    taken_core =sum (c .credits for c in counted if c .course_type =="전공필수")

    remaining ={c .code :c for c in courses if c .code not in taken }
    if not remaining :
        return Roadmap ([],["모든 과목을 이미 이수했습니다."],[],len (graph .edges ),set (),
        taken_credits =taken_credits )
    if (target_credits is not None and taken_credits >=target_credits
    and (required_core is None or taken_core >=required_core )):
        return Roadmap ([],["입력한 과목으로 이미 융합전공 졸업요건 학점을 채웠습니다."],[],
        len (graph .edges ),set (),True ,taken_credits )

    dropped :set [str ]=set ()
    choice_notes :list [tuple [Course ,list [Course ]]]=[]
    groups :dict [str ,list [Course ]]={}
    for c in courses :
        if c .choice_group :
            groups .setdefault (c .choice_group ,[]).append (c )
    for members in groups .values ():
        if len (members )<2 :
            continue
        if any (m .code in taken for m in members ):
            for m in members :
                if m .code not in taken :
                    dropped .add (m .code )
                    remaining .pop (m .code ,None )
            continue
        cand =[m for m in members if m .code in remaining ]
        keep =min (cand ,key =lambda c :(c .rec_order or 99 ,c .code ))
        for m in cand :
            if m .code !=keep .code :
                dropped .add (m .code )
                remaining .pop (m .code ,None )
        choice_notes .append ((keep ,members ))

    downstream :dict [str ,int ]={c :0 for c in remaining }
    for code in remaining :
        for pre in adj .get (code ,()):
            if pre in downstream :
                downstream [pre ]+=1

    def closure (codes )->set [str ]:
        out :set [str ]=set ()
        stack =list (codes )
        while stack :
            x =stack .pop ()
            if x in out or x not in remaining :
                continue
            out .add (x )
            stack .extend (p for p in adj .get (x ,())if p in remaining )
        return out

    def core_plan (short :int ,exclude :set [str ])->set [str ]:
        if short <=0 :
            return set ()
        pend =[x for x in remaining .values ()
        if x .course_type =="전공필수"and x .code not in exclude ]
        pend .sort (key =lambda x :(len (closure ([x .code ])),x .rec_order or 99 ,x .code ))
        pick ,got =[],0
        for x in pend :
            if got >=short :
                break
            pick .append (x .code )
            got +=x .credits
        return closure (pick )

    depth_memo :dict [str ,int ]={}

    def depth (code :str )->int :
        if code not in depth_memo :
            depth_memo [code ]=1 +max (
            (depth (p )for p in adj .get (code ,())if p in remaining ),default =0 )
        return depth_memo [code ]

    def placed_core ()->int :
        return taken_core +sum (
        c .credits for t in terms for c in t .courses if c .course_type =="전공필수")

    terms :list [Term ]=[]
    placed :set [str ]=set (taken )
    completed_early =False
    order =start_order
    max_order =start_order +max_terms -1

    while remaining and len (terms )<max_terms and order <=max_order :
        term =Term (label =term_label (order ),order =order )

        ready =[
        c for c in remaining .values ()
        if all (p in placed or p not in by_code or
        (p not in remaining and p not in placed and p in dropped )
        for p in adj .get (c .code ,()))
        ]

        available =[c for c in ready
        if (c .rec_order or 0 )<=order and c .offered_in (order )]

        if not available and ready :

            order +=1
            continue

        available .sort (key =lambda c :(
        c .course_type !="전공필수",
        -downstream .get (c .code ,0 ),
        c .rec_order or 99 ,
        c .code ,
        ))

        earned =taken_credits +sum (t .credits for t in terms )
        core_short =(required_core or 0 )-placed_core ()

        for c in available :
            if c .course_type !="전공필수"or core_short <=0 :
                continue
            if term .credits +c .credits <=max_credits :
                term .courses .append (c )
                core_short -=c .credits

        chosen ={c .code for c in term .courses }
        need =core_plan (core_short ,chosen )

        for c in available :
            if c .code in chosen or c .code not in need :
                continue
            if term .credits +c .credits <=max_credits :
                term .courses .append (c )
                chosen .add (c .code )

        reserve =sum (by_code [x ].credits for x in need if x not in chosen )
        soft_cap =max_credits
        if target_credits is not None :
            depth_memo .clear ()
            left =target_credits -earned
            chain =max ((depth (x )for x in need ),default =1 )
            span =max (chain ,-(-left //max_credits ),1 )
            soft_cap =min (max_credits ,max (-(-left //span ),1 ))
        for c in available :
            if c .code in chosen :
                continue
            if term .credits +c .credits >soft_cap :
                continue
            if target_credits is not None and (
            earned +term .credits +reserve +c .credits >target_credits ):
                continue
            term .courses .append (c )
            chosen .add (c .code )

        if not term .courses :
            if (core_short >0 or need )and order <max_order :
                order +=1
                continue
            if target_credits is not None :
                done =taken_credits +sum (t .credits for t in terms )
                if done >=target_credits and (
                required_core is None or placed_core ()>=required_core ):
                    completed_early =True
            break

        for c in term .courses :
            placed .add (c .code )
            remaining .pop (c .code ,None )
        terms .append (term )
        order +=1

        if target_credits is not None :
            done =taken_credits +sum (t .credits for t in terms )
            core_ok =required_core is None or placed_core ()>=required_core
            if done >=target_credits and core_ok :
                completed_early =True
                break

            if done >=target_credits and not core_ok :
                if not any (c .course_type =="전공필수"for c in remaining .values ()):
                    completed_early =True
                    break

    unplaced =list (remaining .values ())
    if unplaced and target_credits is None :
        warnings .append (
        f"{max_terms }학기 내 미배치 {len (unplaced )}과목 "
        f"(학점 상한 {max_credits } 또는 선수관계 제약)"
        )
    elif target_credits is not None :
        total =taken_credits +sum (t .credits for t in terms )
        if total <target_credits :
            warnings .append (
            f"융합전공 졸업요건 {target_credits }학점 중 {total }학점만 채웠습니다 "
            f"({max_terms }학기 상한)"
            )
        if required_core and placed_core ()<required_core :
            warnings .append (
            f"전공필수 {required_core }학점 중 {placed_core ()}학점만 배치했습니다."
            )

    if terms and terms [-1 ].order >8 :
        last =terms [-1 ].label .replace ("/","학년 ")
        warnings .append (
        f"계획이 {last }학기까지 이어져 4학년 2학기를 넘깁니다. "
        "학기당 학점을 늘리거나 계절학기를 고려하세요."
        )

    in_plan ={c .code for t in terms for c in t .courses }
    for keep ,members in choice_notes :
        if keep .code in in_plan :
            others =", ".join (m .label for m in members if m .code !=keep .code )
            warnings .append (f"택1 과목이라 {keep .label } 대신 {others }{_eul_reul (others )} 들어도 됩니다.")

    for t in terms :
        for c in t .courses :
            outside =[p for p in c .prereqs if p not in by_code and p not in taken ]
            if outside :
                note =c .prereq_note or ", ".join (outside )
                warnings .append (
                f"{c .label }은(는) 선수과목 {note }{_eul_reul (note )} 먼저 들어야 합니다 "
                "(이 융합전공 목록에 없는 과목)."
                )

    low_conf =[e for e in graph .edges if e .confidence <1.0 ]
    if low_conf :
        warnings .append (
        f"추정 선수관계 {len (low_conf )}건 포함 (학수번호 기반, 정확도 71%)"
        )

    return Roadmap (terms ,warnings ,unplaced ,len (graph .edges ),dropped ,
    completed_early ,taken_credits )

def verify_no_violation (roadmap :Roadmap ,graph :PrereqGraph ,
taken :set [str ]|None =None )->list [str ]:

    taken ={c .upper ()for c in (taken or set ())}
    when :dict [str ,int ]={c :-1 for c in taken }
    for t in roadmap .terms :
        for c in t .courses :
            when [c .code ]=t .order

    violations =[]
    for e in graph .edges :

        if e .dst not in when :
            continue
        if e .src in roadmap .dropped :
            continue
        if e .dst in taken :
            continue
        if e .src not in when :
            violations .append (
            f"{e .src } -> {e .dst }: 선수과목이 로드맵에 없는데 후속과목이 배치됨"
            )
            continue
        if when [e .src ]>=when [e .dst ]:
            violations .append (
            f"{e .src } -> {e .dst }: 선수과목이 같거나 늦은 학기에 배치됨"
            )
    return violations
