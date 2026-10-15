import warnings ,sys ,pathlib ,json
warnings .filterwarnings ("ignore")
sys .path .insert (0 ,str (pathlib .Path (__file__ ).resolve ().parents [1 ]))
from adapters .orchestrator import OpenAICompatOrchestrator ,to_openai_schema ,normalize_tool_call
from core .tools import TOOLS

class _Fn :
    def __init__ (s ,n ,a ):s .name ,s .arguments =n ,a
class _Call :
    def __init__ (s ,i ,n ,a ):s .id ,s .function =i ,_Fn (n ,a )
    def model_dump (s ):return {"id":s .id ,"type":"function",
    "function":{"name":s .function .name ,
    "arguments":s .function .arguments }}
class _Msg :
    def __init__ (s ,c =None ,tc =None ):s .content ,s .tool_calls =c ,tc
class _Choice :
    def __init__ (s ,m ):s .message =m
class _Resp :
    def __init__ (s ,m ):s .choices =[_Choice (m )]

class MockClient :

    def __init__ (s ,script ):s .script ,s .i ,s .seen =script ,0 ,[]
    class chat :
        pass
    def _create (s ,**kw ):
        s .seen .append (kw )
        r =s .script [min (s .i ,len (s .script )-1 )];s .i +=1
        return _Resp (r )

def make (script ):
    o =OpenAICompatOrchestrator .__new__ (OpenAICompatOrchestrator )
    o .model ="mock-model";o .max_rounds =6
    mc =MockClient (script )
    completions =type ("Completions",(),{})()
    completions .create =mc ._create
    chat =type ("Chat",(),{})()
    chat .completions =completions
    client =type ("Client",(),{})()
    client .chat =chat
    o .client =client
    o ._mock =mc
    return o

print ("="*68 );print ("테스트 1: 단일 툴 호출 -> 답변");print ("="*68 )
o =make ([_Msg (tc =[_Call ("c1","check_requirements",
'{"major_code":"AICE","taken_courses":["COSE213"]}')]),
_Msg (c ="총 36학점 중 3학점 이수하셨고 33학점 남았습니다.")])
r =o .chat ([{"role":"user","content":"AICE 졸업요건 알려줘"}],TOOLS )
print ("trace:",r ["trace"]);print ("reply:",r ["reply"])
assert r ["trace"][0 ]["ok"],"툴 실행 실패"

print ("\n"+"="*68 );print ("테스트 2: 다중 툴 연쇄 (추천 -> 로드맵)");print ("="*68 )
o =make ([_Msg (tc =[_Call ("c1","search_majors",'{"interest_text":"딥러닝"}')]),
_Msg (tc =[_Call ("c2","build_roadmap",'{"major_code":"AICE"}')]),
_Msg (c ="인공지능응용융합전공을 추천드리고 로드맵을 만들었습니다.")])
r =o .chat ([{"role":"user","content":"딥러닝 관심있는데 계획 짜줘"}],TOOLS )
for t in r ["trace"]:print (f"  {t ['tool']}({t ['args']}) ok={t ['ok']}")

print ("\n"+"="*68 );print ("테스트 3: 병렬 툴 호출 (Groq llama-3.3 지원)");print ("="*68 )
o =make ([_Msg (tc =[_Call ("c1","check_requirements",'{"major_code":"AICE","taken_courses":[]}'),
_Call ("c2","query_curriculum",'{"major_code":"AICE","course_type":"전공필수"}')]),
_Msg (c ="졸업요건과 필수과목을 함께 안내드립니다.")])
r =o .chat ([{"role":"user","content":"AICE 요건이랑 필수과목"}],TOOLS )
for t in r ["trace"]:print (f"  {t ['tool']} ok={t ['ok']}")
assert len (r ["trace"])==2 ,"병렬 호출 처리 실패"

print ("\n"+"="*68 );print ("테스트 4: 잘못된 인자 -> 오류 복구");print ("="*68 )
o =make ([_Msg (tc =[_Call ("c1","build_roadmap",'{"major_code":"없는전공"}')]),
_Msg (tc =[_Call ("c2","build_roadmap",'{"major_code":"AICE"}')]),
_Msg (c ="정정해서 안내드립니다.")])
r =o .chat ([{"role":"user","content":"로드맵"}],TOOLS )
for t in r ["trace"]:print (f"  {t ['tool']}({t ['args']}) ok={t ['ok']}")

print ("\n"+"="*68 );print ("테스트 5: 존재하지 않는 툴 이름");print ("="*68 )
o =make ([_Msg (tc =[_Call ("c1","hallucinated_tool",'{}')]),
_Msg (c ="죄송합니다, 다시 시도합니다.")])
r =o .chat ([{"role":"user","content":"뭐든"}],TOOLS )
print ("  trace:",r ["trace"])
assert not r ["trace"][0 ]["ok"],"미지 툴이 성공 처리됨"

print ("\n"+"="*68 );print ("테스트 6: 무한루프 방지 (max_rounds)");print ("="*68 )
o =make ([_Msg (tc =[_Call ("c1","query_curriculum",'{"major_code":"AICE"}')])])
r =o .chat ([{"role":"user","content":"루프"}],TOOLS )
print (f"  호출 {len (r ['trace'])}회 후 중단, reply='{r ['reply'][:30 ]}...'")
assert len (r ["trace"])<=6 ,"max_rounds 미작동"

print ("\n"+"="*68 );print ("테스트 7: 툴 결과가 프롬프트에 실제로 들어가는지");print ("="*68 )
last =o ._mock .seen [-1 ]
tool_msgs =[m for m in last ["messages"]if m .get ("role")=="tool"]
print (f"  tool 메시지 {len (tool_msgs )}개 전달됨")
print (f"  첫 내용: {tool_msgs [0 ]['content'][:80 ]}...")
assert tool_msgs ,"툴 결과가 모델에 전달되지 않음"

print ("\n✅ 오케스트레이터 7개 테스트 전체 통과")
