import os ,sys
from core .tools import TOOLS
from adapters .orchestrator import get_orchestrator

def cli ():
    orch =get_orchestrator ()
    print (f"KU Compass ({orch .model }) — 'quit'로 종료\n")
    history =[]
    while True :
        try :q =input ("학생> ").strip ()
        except (EOFError ,KeyboardInterrupt ):break
        if q .lower ()in ("quit","exit","종료"):break
        if not q :continue
        history .append ({"role":"user","content":q })
        out =orch .chat (history ,TOOLS )
        for t in out ["trace"]:
            print (f"  [tool] {t ['tool']}({t ['args']}) {'ok'if t ['ok']else 'ERR'}")
        print (f"챗봇> {out ['reply']}\n")
        history .append ({"role":"assistant","content":out ["reply"]})

def demo ():

    from core .tools import search_majors ,build_roadmap ,check_requirements
    print ("=== API 키 없이 코어 로직 검증 ===\n")
    print ("[search_majors] '생물 데이터로 질병 예측'")
    print (search_majors ("생물 데이터로 질병 예측")["display_text"],"\n")
    print ("[check_requirements] AICE, 기이수 COSE213+COSE362")
    print (check_requirements ("AICE",["COSE213","COSE362"])["display_text"],"\n")
    print ("[build_roadmap] AICE, 기이수 COSE213")
    r =build_roadmap ("AICE",["COSE213"])
    print (r ["display_text"])
    print (f"\n선수과목 순서 위배: {r ['prereq_violations']}건 (간선 {r ['edges_used']}개 기준)")

if __name__ =="__main__":
    (demo if "--demo"in sys .argv else cli )()
