from __future__ import annotations
import json
import os
import re
from abc import ABC ,abstractmethod
from typing import Any ,Callable

SYSTEM_PROMPT ="""고려대 학부생의 융합전공 상담 챗봇입니다.
고려대 서울캠퍼스 융합전공 29개에 대해 관심사 기반 전공 추천, 교과목 조회, 졸업요건 확인, 수강 로드맵만 다룹니다.

학점, 졸업요건, 과목, 수강순서는 반드시 툴을 호출해 확인하세요.
직접 계산하거나 기억으로 답하면 틀립니다.

툴 인자 규칙
- 전공은 학생이 말한 한글 이름을 그대로 넣으세요. 영문 약어나 코드를 만들지 마세요.
- 이수 과목은 학생이 말한 그대로(과목명 또는 학수번호) 넣으세요. 학수번호를 지어내지 마세요.
- 학생이 물은 것에 필요한 툴만 호출하세요. 전공 이름을 이미 말했으면 search_majors를 부르지 마세요.
- 학기당 학점, 현재 학기, 학년·학기 필터는 학생이 말한 경우에만 넣으세요.

툴 결과는 시스템이 학생에게 그대로 표시합니다.
따라서 당신은 결과를 반복하지 말고, 짧은 조언이나 후속 질문만 덧붙이세요.
숫자를 다시 쓰지 마세요. 2문장 이내, 존댓말.
학생이 쓴 언어로만 답하고 다른 언어를 섞지 마세요. 툴 이름이나 시트 이름 같은 내부 이름은 말하지 마세요.
주전공·이중전공·부전공 교육과정이나 신청 기간 같은 행정 정보는 이 서비스에 없습니다. 그렇게 말하고 소속 학과나 학사 공지에서 확인하라고 안내하세요. 사이트 이름을 지어내지 마세요.
인사나 무엇을 할 수 있는지 묻는 질문에는 위 네 가지 기능과 예시 질문 하나를 짧게 소개하세요.
강의계획서를 물으면 연도나 학기를 되묻지 말고 바로 조회하세요."""

LOCAL_PROVIDERS =("ollama","vllm","llamacpp")
_LOCAL_HOSTS =("localhost","127.0.0.1","::1","0.0.0.0")
_CLOUD_KEY_ENV =("GROQ_API_KEY","CEREBRAS_API_KEY","GEMINI_API_KEY",
"GOOGLE_API_KEY","OPENROUTER_API_KEY","ANTHROPIC_API_KEY",
"OPENAI_API_KEY","LLM_API_KEY")

class OfflineViolation (RuntimeError ):
    pass

def offline_mode ()->bool :
    return os .environ .get ("OFFLINE_MODE","").lower ()in ("1","true","yes","on")

def _host_of (url :str )->str :
    from urllib .parse import urlparse
    return (urlparse (url ).hostname or "").lower ()

def assert_local (url :str )->None :

    if not offline_mode ():
        return
    host =_host_of (url )
    if host not in _LOCAL_HOSTS :
        raise OfflineViolation (
        f"OFFLINE_MODE 위반: 외부 호스트 '{host }' 호출이 차단됐습니다. "
        f"허용 호스트는 {', '.join (_LOCAL_HOSTS )} 뿐입니다.")

def stale_cloud_keys ()->list [str ]:

    if not offline_mode ():
        return []
    return [k for k in _CLOUD_KEY_ENV if os .environ .get (k )]

class Orchestrator (ABC ):
    @abstractmethod
    def chat (self ,messages :list [dict ],tools :list [Callable ])->dict :
        ...

ARG_DESCRIPTIONS ={
"interest_text":"학생이 말한 관심 분야나 진로 원문",
"campus":"서울|세종 (학생이 말한 경우에만)",
"major_code":"융합전공 이름. 학생이 말한 한글 이름 그대로 (예: 인공지능응용, 정보보호, 금융공학). 영문 코드를 만들지 말 것",
"course_type":"전공필수|전공선택 (학생이 구분을 물은 경우에만)",
"year_semester":"학생이 특정 학년·학기를 물은 경우에만 '3/1' 형식. 그 외에는 넣지 말 것",
"taken_courses":'학생이 들었다고 말한 과목. 학수번호를 말했으면 학수번호, 과목명을 말했으면 과목명 그대로 (예: ["COSE213"], ["자료구조", "기계학습"]). 학수번호를 지어내지 말 것. 없으면 []',
"first_major":"학생의 제1전공 학과명 (말한 경우에만)",
"start_year_semester":"학생이 말한 현재 학기 '3/1' 형식. 말하지 않았으면 넣지 말 것",
"max_credits_per_term":"학생이 말한 학기당 최대 학점. 말하지 않았으면 넣지 말 것",
"course_code":"학수번호 (예: COSE362)",
"year":"강의계획서 연도. 학생이 말한 경우에만 넣을 것",
"term":"강의계획서 학기 1 또는 2. 학생이 말한 경우에만 넣을 것",
}

def to_openai_schema (fn :Callable )->dict :

    import inspect
    sig =inspect .signature (fn )
    doc =(fn .__doc__ or "").strip ()
    props ,required ={},[]

    hints =[("list","array"),("dict","object"),("bool","boolean"),
    ("int","integer"),("float","number"),("str","string")]
    for name ,p in sig .parameters .items ():
        ann =p .annotation
        tname =getattr (ann ,"__name__",str (ann )).lower ()
        jtype =next ((v for k ,v in hints if k in tname ),"string")
        spec :dict [str ,Any ]={"type":jtype }
        if jtype =="array":
            spec ["items"]={"type":"string"}

        if name in ARG_DESCRIPTIONS :
            spec ["description"]=ARG_DESCRIPTIONS [name ]
        props [name ]=spec
        if p .default is inspect .Parameter .empty :
            required .append (name )
    return {"type":"function","function":{
    "name":fn .__name__ ,"description":doc ,
    "parameters":{"type":"object","properties":props ,"required":required }}}

def normalize_tool_call (raw )->tuple [str ,dict ]:

    fn =raw ["function"]if isinstance (raw ,dict )else raw .function
    name =fn ["name"]if isinstance (fn ,dict )else fn .name
    args =fn ["arguments"]if isinstance (fn ,dict )else fn .arguments
    if isinstance (args ,str ):
        try :
            args =json .loads (args or "{}")
        except json .JSONDecodeError :
            args ={}
    return name ,(args or {})

_FAILED_RE =re .compile (
r"<function=(\w+)>\s*(\{.*?\})\s*</function>",re .S )

def _salvage_failed_call (exc :Exception ,registry :dict )->tuple |None :

    body =getattr (exc ,"message","")or str (exc )
    if "tool_use_failed"not in body and "did not match schema"not in body :
        return None
    m =_FAILED_RE .search (body )
    if not m :
        return None
    name =m .group (1 )
    fn =registry .get (name )
    if fn is None :
        return None
    try :
        args =json .loads (m .group (2 ))
    except json .JSONDecodeError :
        return None
    try :
        result =fn (**args )
    except Exception as e :
        result ={"error":f"{type (e ).__name__ }: {e }"}
    return name ,args ,result

class OpenAICompatOrchestrator (Orchestrator ):

    def __init__ (self ,base_url :str |None =None ,api_key :str |None =None ,
    model :str |None =None ,max_rounds :int =4 ):
        from openai import OpenAI

        default_url =(PROVIDERS ["ollama"]["base_url"]if offline_mode ()
        else "https://api.groq.com/openai/v1")
        default_model =(""if offline_mode ()else "llama-3.3-70b-versatile")
        resolved =base_url or os .environ .get ("LLM_BASE_URL",default_url )
        assert_local (resolved )
        self .model =model or os .environ .get ("LLM_MODEL",default_model )
        self .client =OpenAI (
        base_url =resolved ,
        api_key =api_key or os .environ .get ("LLM_API_KEY")or os .environ .get ("GROQ_API_KEY"),
        )
        self .max_rounds =max_rounds

    def _create (self ,convo ,schemas ,retries :int =3 ):

        import time as _t
        delay =2.0
        for attempt in range (retries +1 ):
            try :
                return self .client .chat .completions .create (
                model =self .model ,messages =convo ,tools =schemas ,
                tool_choice ="auto")
            except Exception as e :
                if type (e ).__name__ !="RateLimitError"or attempt ==retries :
                    raise
                wait =delay
                hdrs =getattr (getattr (e ,"response",None ),"headers",{})or {}
                hint =hdrs .get ("x-ratelimit-reset-tokens")or hdrs .get ("retry-after")
                if hint :
                    try :
                        txt =str (hint )
                        if txt .endswith ("ms"):
                            wait =float (txt [:-2 ])/1000
                        elif txt .endswith ("s")and "m"not in txt :
                            wait =float (txt [:-1 ])
                        else :
                            wait =float (txt )
                    except ValueError :
                        pass
                _t .sleep (min (max (wait +0.5 ,1.0 ),30.0 ))
                delay *=2
        raise RuntimeError ("unreachable")

    def chat (self ,messages :list [dict ],tools :list [Callable ])->dict :
        registry ={f .__name__ :f for f in tools }
        schemas =[to_openai_schema (f )for f in tools ]
        convo =[{"role":"system","content":SYSTEM_PROMPT }]+messages
        trace :list [dict ]=[]
        retried_tool_failure =False

        for _ in range (self .max_rounds ):
            try :
                resp =self ._create (convo ,schemas )
            except Exception as e :

                salvaged =_salvage_failed_call (e ,registry )
                if salvaged is None :

                    if ("tool_use_failed"in str (e )or "Failed to call a function"in str (e ))and not retried_tool_failure :
                        retried_tool_failure =True
                        continue
                    raise
                name ,args ,result =salvaged
                trace .append ({"tool":name ,"args":args ,"result":result ,
                "ok":"error"not in result ,"salvaged":True })
                convo .append ({"role":"assistant",
                "content":f"[{name } 호출]"})
                convo .append ({"role":"user",
                "content":"툴 결과: "+
                json .dumps (result ,ensure_ascii =False )[:1500 ]})
                continue
            msg =resp .choices [0 ].message
            calls =getattr (msg ,"tool_calls",None )
            if not calls :
                return {"reply":msg .content or "","trace":trace ,"model":self .model }

            convo .append ({"role":"assistant","content":msg .content ,
            "tool_calls":[c .model_dump ()for c in calls ]})
            for c in calls :
                name ,args =normalize_tool_call (c )
                fn =registry .get (name )
                if fn is None :
                    result ={"error":f"unknown tool: {name }"}
                else :
                    import inspect as _sig
                    known =_sig .signature (fn ).parameters
                    args ={k :v for k ,v in args .items ()if k in known and v is not None }
                    try :
                        result =fn (**args )
                    except TypeError as e :

                        import inspect as _i
                        params =list (_i .signature (fn ).parameters )
                        result ={"error":f"인자 오류: {e }",
                        "expected_arguments":params ,
                        "hint":f"{name }의 인자는 {params } 입니다."}
                    except Exception as e :
                        result ={"error":f"{type (e ).__name__ }: {e }"}
                trace .append ({"tool":name ,"args":args ,"result":result ,
                "ok":"error"not in result })
                convo .append ({"role":"tool","tool_call_id":c .id ,
                "content":json .dumps (result ,ensure_ascii =False )[:1500 ]})

        return {"reply":"요청이 복잡해 처리를 완료하지 못했습니다. 다시 질문해 주세요.",
        "trace":trace ,"model":self .model }

class ClaudeOrchestrator (Orchestrator ):

    def __init__ (self ,model :str ="claude-opus-5",max_rounds :int =4 ):
        if offline_mode ():
            raise OfflineViolation (
            "OFFLINE_MODE에서는 Anthropic API를 사용할 수 없습니다.")
        import anthropic
        self .client =anthropic .Anthropic ()
        self .model =model
        self .max_rounds =max_rounds

    def chat (self ,messages :list [dict ],tools :list [Callable ])->dict :
        registry ={f .__name__ :f for f in tools }
        schemas =[{"name":f .__name__ ,"description":(f .__doc__ or "").strip (),
        "input_schema":to_openai_schema (f )["function"]["parameters"]}
        for f in tools ]
        convo =list (messages )
        trace :list [dict ]=[]

        for _ in range (self .max_rounds ):
            resp =self .client .messages .create (
            model =self .model ,max_tokens =4096 ,system =SYSTEM_PROMPT ,
            tools =schemas ,messages =convo )
            if resp .stop_reason !="tool_use":
                text ="".join (b .text for b in resp .content if b .type =="text")
                return {"reply":text ,"trace":trace ,"model":self .model }
            convo .append ({"role":"assistant","content":resp .content })
            results =[]
            for b in resp .content :
                if b .type !="tool_use":
                    continue
                fn =registry .get (b .name )
                try :
                    out =fn (**b .input )if fn else {"error":f"unknown tool: {b .name }"}
                except Exception as e :
                    out ={"error":f"{type (e ).__name__ }: {e }"}
                trace .append ({"tool":b .name ,"args":b .input ,"result":out ,
                "ok":"error"not in out })
                results .append ({"type":"tool_result","tool_use_id":b .id ,
                "content":json .dumps (out ,ensure_ascii =False )[:4000 ]})
            convo .append ({"role":"user","content":results })

        return {"reply":"처리를 완료하지 못했습니다.","trace":trace ,"model":self .model }

PROVIDERS ={
"groq":{
"base_url":"https://api.groq.com/openai/v1",
"model":"llama-3.3-70b-versatile",
"env":["GROQ_API_KEY","LLM_API_KEY"],
"note":"TPD 100k (하루 ~60턴). 300+ tok/s로 가장 빠름",
},
"cerebras":{
"base_url":"https://api.cerebras.ai/v1",
"model":"llama-3.3-70b",
"env":["CEREBRAS_API_KEY"],
"note":"일일 토큰 한도가 Groq보다 크다고 알려짐 (계정에서 확인 필요)",
},
"gemini":{
"base_url":"https://generativelanguage.googleapis.com/v1beta/openai/",
"model":"gemini-2.5-flash",
"env":["GEMINI_API_KEY","GOOGLE_API_KEY"],
"note":"RPD 기준 한도. Flash 계열이 무료",
},
"openrouter":{
"base_url":"https://openrouter.ai/api/v1",
"model":"qwen/qwen3.6-27b:free",
"env":["OPENROUTER_API_KEY"],
"note":"하루 50건(크레딧 구매 시 1000건). 보조용",
},
"ollama":{
"base_url":"http://localhost:11434/v1",
"model":"qwen3:14b-instruct-q4_K_M",
"env":[],
"note":"완전 로컬. 한도 없음. GPU 8GB 필요",
},
}

def _key_for (spec :dict )->str |None :
    for name in spec ["env"]:
        v =os .environ .get (name )
        if v :
            return v
    return "local"if not spec ["env"]else None

def _ollama_models ()->list [str ]:

    import json as _j
    import urllib .request
    try :
        with urllib .request .urlopen (
        "http://localhost:11434/api/tags",timeout =0.7 )as r :
            return [m ["name"]for m in _j .loads (r .read ()).get ("models",[])]
    except Exception :
        return []

def _ollama_alive ()->bool :
    return bool (_ollama_models ())

def available_providers ()->list [str ]:

    out =[]
    for n ,spec in PROVIDERS .items ():

        if offline_mode ()and n not in LOCAL_PROVIDERS :
            continue
        if not _key_for (spec ):
            continue
        if n =="ollama":
            installed =_ollama_models ()
            if not installed :
                continue

            if spec ["model"]not in installed :
                spec ["model"]=installed [0 ]
        out .append (n )
    return out

class FallbackOrchestrator (Orchestrator ):

    def __init__ (self ,names :list [str ]|None =None ):
        self .names =names or available_providers ()
        if not self .names :
            raise RuntimeError (
            "사용 가능한 제공자가 없습니다. "
            "GROQ_API_KEY / CEREBRAS_API_KEY / GEMINI_API_KEY 중 하나를 설정하세요.")
        self .model ="+".join (self .names )

    def chat (self ,messages :list [dict ],tools :list [Callable ])->dict :
        last =None
        for name in self .names :
            spec =PROVIDERS [name ]
            key =_key_for (spec )
            if not key :
                continue
            try :

                override =os .environ .get ("LLM_MODEL")
                model =override if (override and name ==self .names [0 ])else spec ["model"]
                o =OpenAICompatOrchestrator (
                base_url =spec ["base_url"],api_key =key ,model =model )
                out =o .chat (messages ,tools )
                out ["provider"]=name
                return out
            except Exception as e :
                last =e
                if type (e ).__name__ not in (
                "RateLimitError","APIStatusError","APIConnectionError",
                "AuthenticationError","NotFoundError","BadRequestError",
                "InternalServerError","APITimeoutError"):
                    raise
                continue
        raise last or RuntimeError ("모든 제공자 실패")

def get_orchestrator ()->Orchestrator :

    if offline_mode ():

        stale =stale_cloud_keys ()
        if stale and os .environ .get ("OFFLINE_ALLOW_STALE_KEYS")!="1":
            raise OfflineViolation (
            f"환경에 클라우드 API 키가 남아 있습니다: {', '.join (stale )}. "
            "오프라인 운영 시 unset 하세요. "
            "(검증 목적이라면 OFFLINE_ALLOW_STALE_KEYS=1)")
        names =available_providers ()
        if not names :
            raise OfflineViolation (
            "로컬 LLM 서버를 찾지 못했습니다. "
            "`ollama serve` 실행 후 모델이 하나 이상 받아져 있어야 합니다.")
        return FallbackOrchestrator (names )

    provider =os .environ .get ("LLM_PROVIDER","").lower ()
    if provider in ("anthropic","claude"):
        return ClaudeOrchestrator (os .environ .get ("LLM_MODEL","claude-opus-5"))
    if provider in PROVIDERS :

        rest =[n for n in available_providers ()if n !=provider ]
        return FallbackOrchestrator ([provider ]+rest )
    return FallbackOrchestrator ()
