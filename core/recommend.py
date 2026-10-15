from __future__ import annotations
import os
import pickle
import re
import warnings
from functools import lru_cache
from pathlib import Path

import json

import openpyxl

warnings .filterwarnings ("ignore")
os .environ .setdefault ("TOKENIZERS_PARALLELISM","false")

DATA =Path (__file__ ).resolve ().parent .parent /"data"
XLSX =DATA /"majors.xlsx"
VEC_CACHE =DATA /"major_vectors.pkl"
MODEL_NAME ="nlpai-lab/KoE5"

QUERY_PREFIX ="query: "

W_EMBED ,W_KEYWORD =1.0 ,0.0

SYNONYMS ={
"머신러닝":"기계학습","머신 러닝":"기계학습","ml":"기계학습",
"딥러닝":"딥러닝 심층학습","ai":"인공지능","에이아이":"인공지능",
"데이터사이언스":"데이터과학","데이터 사이언스":"데이터과학",
"빅데이터":"빅데이터분석","코딩":"프로그래밍","코팅":"프로그래밍",
"프로그래밍":"프로그래밍 소프트웨어","웹개발":"웹 프로그래밍",
"앱개발":"모바일 프로그래밍","해킹":"정보보호 보안",
"사이버보안":"정보보호 보안","블록체인":"블록체인 암호",
"주식":"금융 투자","재테크":"금융 투자","핀테크":"금융공학",
"바이오":"생명공학","제약":"생명공학 의약",
"의료":"의학 보건","헬스케어":"의학 보건",
"로봇":"로봇공학 기계","자율주행":"자율주행 인공지능",
"반도체":"반도체 신소재","게임":"게임 프로그래밍",
"디자인":"디자인 조형","마케팅":"마케팅 경영",
"창업":"창업 벤처","스타트업":"창업 벤처",
"환경":"환경 생태","기후":"기후변화 환경",
"심리":"심리학 인지","뇌":"뇌 인지과학",
"통역":"언어 통번역","번역":"언어 통번역",

"machine learning":"기계학습 인공지능","deep learning":"딥러닝 인공지능",
"artificial intelligence":"인공지능","data science":"데이터과학",
"security":"정보보호 보안","finance":"금융 투자",
"biology":"생명공학","robotics":"로봇공학",
"semiconductor":"반도체","startup":"창업 벤처",
"design":"디자인 조형","korean":"한국어 교육",
"environment":"환경 생태","medical":"의학 보건",
}

TERM_DICT =DATA /"term_dict.json"
MAX_EXPAND =3

EXPAND_DOCS =True
MIN_TERM =3

def _norm_term (s :str )->str :
    return re .sub (r"[\s·\-()]","",str (s )).lower ()

@lru_cache (maxsize =1 )
def _term_table ()->dict :

    if not TERM_DICT .exists ():
        return {}
    try :
        return json .loads (TERM_DICT .read_text ())
    except Exception :
        return {}

def expand_query (text :str )->str :

    n =_norm_term (text )
    added :list [str ]=[]

    for k ,v in SYNONYMS .items ():
        if _norm_term (k )in n :
            for t in v .split ():
                if _norm_term (t )not in n and t not in added :
                    added .append (t )

    table =_term_table ()
    if not table :
        return f"{text } {' '.join (added [:MAX_EXPAND ])}"if added else text

    hits =sorted ((k for k in table if len (k )>=MIN_TERM and k in n ),
    key =len ,reverse =True )
    used =""
    for k in hits :
        if k in used :
            continue
        used +=k
        for a in table [k ]:
            if _norm_term (a )not in n and a not in added :
                added .append (a )
        if len (added )>=MAX_EXPAND :
            break
    return f"{text } {' '.join (added [:MAX_EXPAND ])}"if added else text
TOP_COURSES =5

MIN_RAW_SCORE =0.26

@lru_cache (maxsize =1 )
def _majors ()->list [dict ]:

    wb =openpyxl .load_workbook (XLSX ,data_only =True )
    ws =wb ["융합전공_목록"]
    sheets =[s for s in wb .sheetnames if "교과목"in s ]
    out =[]
    for r in list (ws .iter_rows (values_only =True ))[1 :]:
        if not r or not r [0 ]:
            continue

        if len (r )>3 and r [3 ]and "세종"in str (r [3 ]):
            continue
        name =str (r [0 ]).strip ()

        def _n (x ):

            t =re .sub (r"\(.*?\)","",str (x ))
            t =re .sub (r"[\s()&·‧\-_]|융합전공|전공|교과목","",t ).lower ()
            return t .replace ("쳐","처").replace ("사업","산업")

        nk =_n (name )
        sheet =None
        if nk :
            for cand in sheets :
                nc =_n (cand )
                if nc ==nk :
                    sheet =cand
                    break
            if sheet is None :
                for cand in sheets :
                    nc =_n (cand )
                    if nc and (nk in nc or nc in nk ):
                        sheet =cand
                        break
        courses =[]
        if sheet :
            rows =list (wb [sheet ].iter_rows (values_only =True ))
            hdr =[str (c ).strip ()if c else ""for c in rows [0 ]]
            inm =next ((i for i ,h in enumerate (hdr )if "교과목명"in h ),None )
            if inm is not None :
                for cr in rows [1 :]:
                    if cr and inm <len (cr )and cr [inm ]:
                        courses .append (str (cr [inm ]).strip ())
        out .append ({
        "major_name":name ,
        "departments":str (r [1 ]or ""),
        "host":str (r [2 ]or ""),
        "campus":str (r [3 ]or ""),
        "eligibility":str (r [4 ]or "").strip ()or None ,
        "sheet":sheet ,
        "courses":courses ,
        "identity":f"{name } 전공. 참여학과: {r [1 ]or '미상'}. 주요 교과목: "
        +", ".join (courses [:15 ]),
        })
    return out

@lru_cache (maxsize =1 )
def _model ():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer (MODEL_NAME )

def _vectors ():

    majors =_majors ()
    if VEC_CACHE .exists ():
        try :
            blob =pickle .loads (VEC_CACHE .read_bytes ())
            if (blob .get ("n")==len (majors )
            and blob .get ("model")==MODEL_NAME
            and blob .get ("max_seq")==_model ().max_seq_length
            and blob .get ("prefix")==QUERY_PREFIX
            and blob .get ("expand_docs")==EXPAND_DOCS ):
                return blob ["identity"],blob ["courses"]
        except Exception :
            pass

    model =_model ()
    def _doc (t :str )->str :
        return expand_query (t )if EXPAND_DOCS else t

    ident =model .encode ([QUERY_PREFIX +_doc (m ["identity"])for m in majors ],
    convert_to_numpy =True ,normalize_embeddings =True )
    course_vecs =[]
    for m in majors :
        names =m ["courses"][:60 ]or [m ["major_name"]]
        course_vecs .append (model .encode (
        [QUERY_PREFIX +_doc (n )for n in names ],
        convert_to_numpy =True ,normalize_embeddings =True ))
    VEC_CACHE .write_bytes (pickle .dumps (
    {"n":len (majors ),"model":MODEL_NAME ,
    "max_seq":model .max_seq_length ,"prefix":QUERY_PREFIX ,
    "expand_docs":EXPAND_DOCS ,
    "identity":ident ,"courses":course_vecs }))
    return ident ,course_vecs

def recommend (interest_text :str ,campus :str |None =None ,
top_k :int =5 )->dict :

    majors =_majors ()
    kw =_keyword_score (interest_text ,majors )
    query =expand_query (interest_text )

    method ="KoE5 임베딩"
    raw_max =1.0
    try :
        emb ,raw_max =_embed_score (query ,majors )
    except Exception as e :
        emb =[0.0 ]*len (majors )
        method =f"키워드 매칭 (임베딩 불가: {type (e ).__name__ })"

    if raw_max <MIN_RAW_SCORE and max (k [0 ]for k in kw )<0.2 :
        return {"candidates":[],"method":method ,"low_confidence":True ,
        "display_text":"입력하신 내용으로는 적합한 전공을 찾기 어렵습니다. "
        "관심 분야를 조금 더 구체적으로 알려주세요. "
        "(예: 인공지능, 금융, 보안, 환경, 한국어교육)"}

    ranked =[]
    for i ,m in enumerate (majors ):
        if campus and campus not in m ["campus"]:
            continue
        score =W_EMBED *emb [i ]+W_KEYWORD *kw [i ][0 ]
        ranked .append ((m ,score ,emb [i ],kw [i ][0 ],kw [i ][1 ]))
    ranked .sort (key =lambda x :-x [1 ])
    top =ranked [:top_k ]

    cands ,lines =[],[]
    for i ,(m ,score ,es ,ks ,matched )in enumerate (top ,1 ):
        cands .append ({
        "major_name":m ["major_name"],"score":round (float (score ),3 ),
        "embed_score":round (float (es ),3 ),"keyword_score":round (float (ks ),3 ),
        "matched_keywords":matched [:4 ],"host_college":m ["host"],
        "campus":m ["campus"],"eligibility_note":m ["eligibility"],
        "sheet":m ["sheet"],
        })
        note =f" (지원조건: {m ['eligibility']})"if m ["eligibility"]else ""
        kws =f" — '{', '.join (matched [:3 ])}' 관련"if matched else ""
        host =f" · {m ['host']}"if m .get ("host")else ""
        lines .append (f"{i }. {m ['major_name']}{host } (상대 점수 {score :.2f}){kws }{note }")

    return {"candidates":cands ,"method":method ,
    "display_text":"\n".join (lines )+"\n\n(상대 점수는 후보 전공끼리 비교한 값으로 1위가 1.00)"
    if lines else "적합한 전공을 찾지 못했습니다."}

def _embed_score (text :str ,majors :list [dict ])->tuple [list [float ],float ]:

    import numpy as np
    model =_model ()
    ident ,course_vecs =_vectors ()
    q =model .encode (QUERY_PREFIX +text ,convert_to_numpy =True ,
    normalize_embeddings =True )

    id_sim =ident @q
    out =[]
    for i in range (len (majors )):
        cs =course_vecs [i ]@q
        k =min (TOP_COURSES ,len (cs ))
        top_mean =float (np .sort (cs )[-k :].mean ())if k else 0.0
        out .append (0.4 *float (id_sim [i ])+0.6 *top_mean )
    lo ,hi =min (out ),max (out )
    norm =[(v -lo )/(hi -lo )if hi >lo else 0.0 for v in out ]
    return norm ,hi

def _keyword_score (text :str ,majors :list [dict ]):
    toks =[t for t in re .split (r"[\s,./]+",text )if len (t )>=2 ]
    out =[]
    for m in majors :
        matched ,score =[],0.0
        corpus =f"{m ['major_name']} {m ['departments']} "+" ".join (m ["courses"])
        for t in toks :
            if t in m ["major_name"]:
                score +=3.0
                matched .append (t )
            elif t in corpus :
                score +=1.0
                matched .append (t )
            else :
                for kwname in m ["courses"]:
                    if t in kwname or kwname in t :
                        score +=0.7
                        matched .append (kwname )
                        break
        norm =score /(len (toks )*3 )if toks else 0.0
        out .append ((min (norm ,1.0 ),list (dict .fromkeys (matched ))))
    return out

def warm_cache ()->str :

    _vectors ()
    return f"vectors cached: {VEC_CACHE } ({VEC_CACHE .stat ().st_size :,} bytes)"
