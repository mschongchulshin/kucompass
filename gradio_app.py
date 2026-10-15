from __future__ import annotations
import os
import time

os .environ .setdefault ("GRADIO_ANALYTICS_ENABLED","False")
os .environ .setdefault ("HF_HUB_DISABLE_TELEMETRY","1")

import core

import gradio as gr

from core .tools import (TOOLS ,search_majors ,build_roadmap ,check_requirements ,
asks_out_of_scope ,SCOPE_NOTE )
from core .render import render_facts ,scrub_advice
from core .privacy import scrub_input ,notice
from adapters .orchestrator import get_orchestrator

MAX_TURNS =int (os .environ .get ("MAX_TURNS_PER_SESSION","20"))
_MIN_INTERVAL =2.0

def _tool_summary (trace :list [dict ])->str :
    if not trace :
        return "툴 호출 없음 (일반 대화)"
    rows =["| 툴 | 인자 | 결과 |","|---|---|---|"]
    for t in trace :
        args =", ".join (f"{k }={v }"for k ,v in list (t ["args"].items ())[:3 ])
        rows .append (f"| {t ['tool']} | {args [:60 ]} | {'성공'if t ['ok']else '실패'} |")
    return "\n".join (rows )

def respond (message :str ,history :list ,state :dict ):
    state =state or {"turns":0 ,"last":0.0 ,"last_major":None }
    if not message .strip ():
        yield history ,state ,""
        return

    if state ["turns"]>=MAX_TURNS :
        history =history +[
        {"role":"user","content":message },
        {"role":"assistant",
        "content":f"세션당 {MAX_TURNS }턴 제한에 도달했습니다. 페이지를 새로고침해 주세요."}]
        yield history ,state ,""
        return

    elapsed =time .time ()-state ["last"]
    if elapsed <_MIN_INTERVAL :
        time .sleep (_MIN_INTERVAL -elapsed )

    message ,pii =scrub_input (message )
    yield (history +[{"role":"user","content":message },
    {"role":"assistant",
    "content":"답변을 준비하고 있습니다. 보통 10초 안팎 걸립니다."}],
    state ,"툴 호출 중")

    if asks_out_of_scope (message ):
        reply =(SCOPE_NOTE +"\n\n관심 분야나 진로를 알려주시면 맞는 융합전공을 찾아드릴게요. "
        "(예: 데이터 분석에 관심 있어요)")
        if pii :
            reply =notice (pii )+"\n\n"+reply
        state ["turns"]+=1
        state ["last"]=time .time ()
        yield (history +[{"role":"user","content":message },
        {"role":"assistant","content":reply }],
        state ,_tool_summary ([]))
        return

    convo =[{"role":m ["role"],"content":m ["content"]}for m in history ]

    ctx =state .get ("last_major")
    if ctx :
        convo .append ({"role":"system",
        "content":f"현재 대화에서 다루는 전공: {ctx }. "
        f"학생이 전공을 새로 말하지 않으면 이 전공으로 툴을 호출하세요."})
    convo .append ({"role":"user","content":message })

    try :
        out =get_orchestrator ().chat (convo ,TOOLS )
        trace =out ["trace"]

        facts =render_facts (trace )
        advice ,dropped =scrub_advice (out ["reply"],trace )

        for t in trace :
            r =t .get ("result")
            if isinstance (r ,dict )and r .get ("major_name"):
                state ["last_major"]=r ["major_name"]
                break
        else :
            for t in trace :
                r =t .get ("result")
                if isinstance (r ,dict )and r .get ("candidates"):
                    state ["last_major"]=r ["candidates"][0 ]["major_name"]
                    break
        if facts :
            reply =facts +(f"\n\n{advice }"if advice else "")
        else :
            reply =advice or out ["reply"]
    except Exception as e :
        detail =str (e )
        if "per day"in detail or "TPD"in detail :
            import re as _re
            m =_re .search (r"try again in (\d+m)?(\d+)(?:\.\d+)?s",detail )

            when =""
            if m :
                mins =int ((m .group (1 )or "0m")[:-1 ])
                secs =int (m .group (2 ))
                total =mins *60 +secs
                when =(f" 약 {total //60 }분 뒤 다시 시도할 수 있습니다."
                if total >=60 else " 잠시 후 다시 시도할 수 있습니다.")
            reply =("무료 티어 토큰 한도(24시간 기준)에 도달했습니다."+when
            +" 다른 탭은 API 키 없이 계속 사용할 수 있습니다.")
        elif type (e ).__name__ =="RateLimitError":
            reply ="요청이 몰려 잠시 제한되었습니다. 잠시 후 다시 시도해 주세요."
        elif type (e ).__name__ in ("AuthenticationError","NotFoundError"):
            reply =("사용 가능한 LLM 제공자가 없습니다. "
            "GROQ_API_KEY 또는 CEREBRAS_API_KEY를 설정해 주세요.")
        elif type (e ).__name__ =="BadRequestError":
            reply =("모델이 요청을 처리하지 못했습니다. "
            "질문을 조금 더 구체적으로 바꿔 다시 시도해 주세요. "
            "(예: '인공지능응용 전공에서 자료구조 들었는데 뭘 더 들어야 해?')")
        elif type (e ).__name__ =="OfflineViolation":

            reply =f"오프라인 모드 차단: {detail }"
        else :
            reply =f"오류가 발생했습니다: {type (e ).__name__ } - {detail [:150 ]}"
        trace =[]

    if asks_out_of_scope (message )and SCOPE_NOTE not in reply :
        reply =SCOPE_NOTE +"\n\n"+reply
    if pii :
        reply =notice (pii )+"\n\n"+reply

    state ["turns"]+=1
    state ["last"]=time .time ()
    history =history +[
    {"role":"user","content":message },
    {"role":"assistant","content":reply }]
    yield history ,state ,_tool_summary (trace )

def _direct_search (text ,campus ):
    if not text .strip ():
        return "관심사를 입력해 주세요."
    r =search_majors (text ,campus =campus or None ,top_k =5 )
    if str (r .get ("method","")).startswith ("키워드"):
        return ("※ 임베딩 모델을 불러오지 못해 키워드로만 찾았습니다. 결과가 부정확할 수 있습니다.\n\n"
        +r ["display_text"])
    return r ["display_text"]

START_TERMS =["2학년 1학기","2학년 2학기","3학년 1학기","3학년 2학기",
"4학년 1학기","4학년 2학기"]

def _direct_roadmap (major ,taken ,cap ,start ="3학년 1학기"):
    codes =[c .strip ().upper ()for c in (taken or "").replace (","," ").split ()if c .strip ()]
    ys =(start or "3학년 1학기").replace ("학년 ","/").replace ("학기","")
    r =build_roadmap (major ,codes ,start_year_semester =ys ,max_credits_per_term =int (cap ))
    if "error"in r :
        return r ["error"]
    warn ="\n".join (f"- {w }"for w in r ["warnings"])
    done =r .get ("taken_credits")or 0
    if done :
        total =(f"이번 계획 {r ['total_credits']}학점 / {r ['total_terms']}학기 + 기이수 인정 {done }학점 "
        f"= {r ['total_credits']+done }학점 (융합전공 졸업요건 {r ['target_credits']}학점)")
    else :
        total =(f"총 {r ['total_credits']}학점 / {r ['total_terms']}학기 "
        f"(융합전공 졸업요건 {r ['target_credits']}학점)")
    return (f"{r ['major_name']}\n\n{r ['display_text']}\n\n{total }\n\n"
    f"선수과목 순서 위배: {r ['prereq_violations']}건 "
    f"(등록된 선수관계 {r ['edges_used']}개 기준)"
    +(f"\n\n참고\n{warn }"if warn else ""))

def _direct_req (major ,taken ):
    codes =[c .strip ().upper ()for c in (taken or "").replace (","," ").split ()if c .strip ()]
    r =check_requirements (major ,codes )
    return r .get ("error")or r ["display_text"]

CSS ="""
.gradio-container {max-width: 1000px !important}
footer {display: none !important}

/* ---- 전체 흑백 ---- */
/* 색상만 통일하고, 테두리는 여기서 주지 않는다.
   .message/.bubble 같은 넓은 선택자에 border를 걸면 Gradio가
   메시지를 감싸는 래퍼와 내부 요소에 이중으로 적용돼 네모가 겹쳐 보인다. */
*, *::before, *::after {
  color: #000 !important;
  box-shadow: none !important;
  text-shadow: none !important;
}
body, .gradio-container, .tabs, .tabitem,
.block, .form, .panel, .gr-box { background: #fff !important; }

/* ---- 입력 요소 ---- */
button {
  background: #fff !important;
  border: 1px solid #000 !important;
  border-radius: 0 !important;
  font-weight: 400 !important;
}
button:hover { background: #f0f0f0 !important; }
input, textarea, select {
  background: #fff !important;
  border: 1px solid #000 !important;
  border-radius: 0 !important;
}
input[type=range] { accent-color: #000 !important; border: none !important; }

/* ---- 표 ---- */
table { border-collapse: collapse !important; }
table, th, td { border: 1px solid #000 !important; }
th { background: #f5f5f5 !important; font-weight: 400 !important; }

/* ---- 챗봇 말풍선 ----
   테두리는 실제 말풍선 요소 하나에만 건다.
   래퍼(.message-row, .message-wrap)는 테두리를 제거해 이중 사각형을 막는다. */
.message-row, .message-wrap, .chatbot > div, .bubble-wrap {
  border: none !important;
  background: transparent !important;
}
.message-row .message {
  background: #fff !important;
  border: 1px solid #000 !important;
  border-radius: 0 !important;
}
.message .message { border: none !important; }

/* ---- 타이포 ---- */
svg { fill: #000 !important; stroke: #000 !important; }
h1, h2, h3, h4, strong, b { font-weight: 600 !important; }
a { text-decoration: underline !important; }
"""

def _mode_banner ()->str :

    from adapters .orchestrator import offline_mode ,available_providers ,PROVIDERS
    if not offline_mode ():
        return ("> ⚠️ **온라인 모드** — 대화 내용이 외부 LLM API로 전송됩니다. "
        "학생 데이터를 다루려면 `OFFLINE_MODE=1` 로 실행하세요.")

    try :
        names =available_providers ()
        model =(os .environ .get ("LLM_MODEL")
        or (PROVIDERS [names [0 ]]["model"]if names else None )
        or "확인 불가")
        engine =names [0 ]if names else "없음"
    except Exception :
        model ,engine ="확인 불가","없음"
    return (f"> 🔒 **오프라인 모드** — 이 서버 안에서 **{model }** 이(가) 실행됩니다 "
    f"(실행 엔진 {engine }). 대화 내용은 외부로 전송되지 않습니다.")

with gr .Blocks (title ="KU Compass")as demo :
    gr .Markdown (
    "# KU Compass\n"
    "고려대 학부생 맞춤형 이중/융합전공 추천 및 수강 로드맵 시스템"
    )
    gr .Markdown (_mode_banner ())

    with gr .Tab ("챗봇"):

        chatbot =gr .Chatbot (height =440 )
        with gr .Row ():
            msg =gr .Textbox (placeholder ="예: 생물 데이터로 질병 예측하는 쪽에 관심 있어요",
            show_label =False ,scale =5 ,container =False )
            send =gr .Button ("전송",scale =1 )
        gr .Examples (
        examples =[
        "생물 데이터로 질병 예측 모델을 만들고 싶어요",
        "인공지능응용융합전공 졸업요건이 어떻게 되나요?",
        "자료구조는 들었는데 앞으로 뭘 들어야 할까요?",
        "보안 쪽 융합전공 중에 뭐가 있나요?",
        ],inputs =msg )
        with gr .Accordion ("호출된 툴",open =False ):
            tools_md =gr .Markdown ("아직 호출 없음")
        state =gr .State ({"turns":0 ,"last":0.0 ,"last_major":None })

        for trigger in (msg .submit ,send .click ):
            trigger (respond ,[msg ,chatbot ,state ],[chatbot ,state ,tools_md ]).then (
            lambda :"",None ,msg )

    with gr .Tab ("전공 추천"):
        gr .Markdown ("관심 분야나 하고 싶은 일을 자유롭게 적으면 맞는 융합전공 5개를 찾아드립니다.")
        s_text =gr .Textbox (label ="관심사",
        placeholder ="딥러닝으로 이미지 인식을 하고 싶어요")
        gr .Examples (examples =["데이터로 주식 시장을 분석해 보고 싶어요",
        "외국인 유학생에게 한국어를 가르치고 싶어요",
        "기후 위기 대응 정책 쪽으로 진로를 생각하고 있어요",
        "사람 뇌가 언어를 어떻게 처리하는지 궁금해요"],inputs =s_text )
        s_campus =gr .State ("")
        s_btn =gr .Button ("추천받기")
        s_out =gr .Markdown ()
        s_btn .click (_direct_search ,[s_text ,s_campus ],s_out )

    with gr .Tab ("로드맵"):
        gr .Markdown ("융합전공과 이미 들은 과목을 넣으면 선수과목 순서를 지킨 학기별 수강 계획을 만들어 드립니다. "
        "학수번호 대신 과목명(예: 자료구조)을 적어도 됩니다.")
        with gr .Row ():
            r_major =gr .Textbox (label ="전공",value ="AICE",scale =2 )
            r_taken =gr .Textbox (label ="기이수 학수번호 또는 과목명 (공백 구분)",
            placeholder ="COSE213 COSE214",scale =3 )
        with gr .Row ():
            r_start =gr .Dropdown (START_TERMS ,value ="3학년 1학기",label ="시작 학기",scale =2 )
            r_cap =gr .Slider (6 ,21 ,value =18 ,step =3 ,label ="학기당 최대 학점",scale =3 )
        gr .Examples (examples =[["인공지능응용","",18 ,"3학년 1학기"],
        ["정보보호","COSE341 SMRT111",15 ,"3학년 1학기"],
        ["금융공학","재무관리",12 ,"2학년 2학기"]],
        inputs =[r_major ,r_taken ,r_cap ,r_start ])
        r_btn =gr .Button ("로드맵 생성")
        r_out =gr .Markdown ()
        r_btn .click (_direct_roadmap ,[r_major ,r_taken ,r_cap ,r_start ],r_out )

    with gr .Tab ("졸업요건"):
        gr .Markdown ("융합전공과 이미 들은 과목을 넣으면 남은 학점과 남은 전공필수 과목을 알려드립니다.")
        with gr .Row ():
            q_major =gr .Textbox (label ="전공",value ="AICE",scale =2 )
            q_taken =gr .Textbox (label ="기이수 학수번호 또는 과목명",value ="COSE213 COSE362",scale =3 )
        gr .Examples (examples =[["인공지능응용","자료구조"],
        ["소프트웨어기술벤처","COSE213 COSE352"],
        ["기후변화","CCST301 LESE302"]],inputs =[q_major ,q_taken ])
        q_btn =gr .Button ("검증")
        q_out =gr .Markdown ()
        q_btn .click (_direct_req ,[q_major ,q_taken ],q_out )

if __name__ =="__main__":

    demo .launch (server_name =os .environ .get ("BIND_HOST","127.0.0.1"),
    server_port =int (os .environ .get ("PORT",7860 )),
    css =CSS ,theme =gr .themes .Base (
    primary_hue =gr .themes .colors .gray ,
    secondary_hue =gr .themes .colors .gray ,
    neutral_hue =gr .themes .colors .gray ))
