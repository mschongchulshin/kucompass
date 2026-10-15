import sys ,pathlib ,json
sys .path .insert (0 ,str (pathlib .Path (__file__ ).resolve ().parents [1 ]))
from core .loader import load_major ,build_name_index ,list_majors
from core .prereq import PrereqGraph ,all_flowmap_edges
from core .roadmap import build_roadmap as _rm ,verify_no_violation
from core .requirements import get_rule ,check_requirements as _cr
from core .tools import build_roadmap ,check_requirements ,query_curriculum
from adapters .orchestrator import to_openai_schema ,normalize_tool_call
from core .tools import TOOLS

XLSX ="data/majors.xlsx";EDGES ="data/edges.json"
name2code =build_name_index (XLSX );flow =all_flowmap_edges (XLSX .replace ("majors.xlsx","edges.json"))
fails =[]

print ("="*66 )
print ("실험: 전 융합전공 대상 제약 위반율 측정 (논문 핵심 지표)")
print ("="*66 )
print (f"{'전공':30s}{'과목':>5s}{'간선':>5s}{'학기':>5s}{'학점':>6s}{'위반':>5s}")
tot_v =0 ;tot_m =0
for sheet in list_majors (XLSX ):
    courses =load_major (XLSX ,sheet )
    if len (courses )<5 :continue
    g =PrereqGraph ({c .code :c .name for c in courses })
    g .add_flowmap_edges (flow ,name2code );g .add_code_rules ()
    rule =get_rule (sheet )
    rm =_rm (courses ,g ,taken =set (),target_credits =rule .total_required ,
    required_core =rule .core_required )
    v =verify_no_violation (rm ,g ,set ())
    tot_v +=len (v );tot_m +=1
    if v :fails .append ((sheet ,v ))
    print (f"{sheet .replace ('_교과목',''):30s}{len (courses ):5d}{len (g .edges ):5d}"
    f"{len (rm .terms ):5d}{rm .total_credits :6d}{len (v ):5d}")
print (f"\n>> {tot_m }개 전공 전체 선수과목 순서 위배: {tot_v }건 "
f"{'✅ 위반율 0%'if tot_v ==0 else '❌'}")

print ("\n"+"="*66 );print ("졸업요건 정확도 (전공별 상이 규정)")
print ("="*66 )
for mc ,taken in [("AICE",["COSE213","COSE362","COSE214"]),
("소프트웨어기술벤처",["COSE213"]),
("정보보호",["COSE215","COSE222"]),
("뇌인지",[])]:
    r =check_requirements (mc ,taken )
    if "error"in r :print (f"  {mc }: {r ['error']}");continue
    print (f"  {r ['display_text']}")

print ("\n"+"="*66 );print ("툴 스키마 생성 (OpenAI 호환)")
print ("="*66 )
for f in TOOLS :
    s =to_openai_schema (f )
    fn =s ["function"]
    d =fn ["description"].split ("\n")[0 ]
    print (f"  {fn ['name']:20s} params={list (fn ['parameters']['properties'])} req={fn ['parameters']['required']}")
    if len (fn ["description"])<50 :fails .append ((f .__name__ ,"description too short"))

print ("\n"+"="*66 );print ("툴 호출 정규화 (제공자별 arguments 형식 차이)")
print ("="*66 )
class _F :pass
for label ,args in [("str(Groq/OpenAI)",'{"major_code":"AICE"}'),("dict(일부제공자)",{"major_code":"AICE"}),("빈문자열",""),("깨진JSON","{bad")]:
    o =_F ();o .function =_F ();o .function .name ="build_roadmap";o .function .arguments =args
    n ,a =normalize_tool_call (o );print (f"  {label :22s} -> {n }({a })")

print ("\n"+"="*66 );print ("엣지 케이스")
print ("="*66 )
print ("  없는 전공:",build_roadmap ("존재하지않는전공").get ("error","?")[:40 ])
print ("  빈 기이수:","OK"if build_roadmap ("AICE",[])["total_terms"]>0 else "FAIL")
r =build_roadmap ("AICE",["COSE213","COSE214","COSE361","COSE362","COSE382","COSE474"])
print (f"  6과목 기이수 -> {r ['total_terms']}학기 {r ['total_credits']}학점, 위반 {r ['prereq_violations']}")
print ("  이상한 학수번호:",check_requirements ("AICE",["XXXX999"])["display_text"][:70 ])

print ("\n"+"="*66 )
print ("❌ 실패:"if fails else "✅ 전체 통과")
for f in fails [:5 ]:print ("  ",f )
