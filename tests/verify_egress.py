import warnings ,sys ,pathlib ,socket ,os ,json ,ipaddress
warnings .filterwarnings ("ignore")
sys .path .insert (0 ,str (pathlib .Path (__file__ ).resolve ().parents [1 ]))

CONNECTIONS :list [tuple [str ,int ]]=[]
_real_connect =socket .socket .connect
_real_getaddrinfo =socket .getaddrinfo
RESOLVED :list [str ]=[]

def _audited_connect (self ,address ):
    try :
        host ,port =address [0 ],address [1 ]
        CONNECTIONS .append ((str (host ),int (port )))
    except Exception :
        CONNECTIONS .append ((str (address ),-1 ))
    return _real_connect (self ,address )

def _audited_getaddrinfo (host ,port ,*a ,**kw ):
    RESOLVED .append (str (host ))
    return _real_getaddrinfo (host ,port ,*a ,**kw )

socket .socket .connect =_audited_connect
socket .getaddrinfo =_audited_getaddrinfo

def is_local (host :str )->bool :
    try :
        return ipaddress .ip_address (host ).is_loopback
    except ValueError :
        return host in ("localhost","::1")

def main ():
    os .environ .setdefault ("OFFLINE_MODE","1")
    os .environ .setdefault ("OFFLINE_ALLOW_STALE_KEYS","1")

    from core .tools import search_majors ,query_curriculum ,check_requirements ,build_roadmap

    print ("="*62 )
    print ("1. 결정적 코어 (추천 · 조회 · 졸업요건 · 로드맵)")
    print ("="*62 )
    search_majors ("데이터 분석과 통계에 관심 있어요")
    query_curriculum ("AICE")
    check_requirements ("AICE",["COSE213","COSE362"])
    build_roadmap ("AICE",["COSE213"])
    print (f"   누적 연결 {len (CONNECTIONS )}건")

    print ()
    print ("="*62 )
    print ("2. 챗봇 (로컬 LLM 경유)")
    print ("="*62 )
    try :
        from adapters .orchestrator import get_orchestrator
        from core .tools import TOOLS
        out =get_orchestrator ().chat (
        [{"role":"user","content":"AICE 졸업요건 알려줘"}],TOOLS )
        print (f"   모델 {out .get ('model')} · 툴 {[t ['tool']for t in out ['trace']]}")
    except Exception as e :
        print (f"   건너뜀 ({type (e ).__name__ }: {str (e )[:80 ]})")

    print ()
    print ("="*62 )
    print ("3. 연결 목적지 전수")
    print ("="*62 )
    external =[]
    for host ,port in sorted (set (CONNECTIONS )):
        mark ="로컬"if is_local (host )else "외부"
        if not is_local (host ):
            external .append ((host ,port ))
        print (f"   [{mark }] {host }:{port }")
    if not CONNECTIONS :
        print ("   (연결 없음)")

    ext_names =[h for h in sorted (set (RESOLVED ))if not is_local (h )]
    if ext_names :
        print ("\n   DNS 조회된 외부 이름:")
        for h in ext_names :
            print (f"     - {h }")

    print ()
    print ("="*62 )
    if external or ext_names :
        print (f"실패: 외부 연결 {len (external )}건, 외부 DNS {len (ext_names )}건")
        code =1
    else :
        print ("통과: 외부로 나간 연결 0건")
        code =0
    print ("="*62 )

    pathlib .Path ("tests/egress_result.json").write_text (json .dumps (
    {"connections":sorted (set (CONNECTIONS )),"resolved":sorted (set (RESOLVED )),
    "external":external ,"external_dns":ext_names ,"pass":code ==0 },
    ensure_ascii =False ,indent =2 ))
    return code

if __name__ =="__main__":
    sys .exit (main ())
