import sys ,pathlib
sys .path .insert (0 ,str (pathlib .Path (__file__ ).resolve ().parents [1 ]))
from core .loader import load_major ,build_name_index
from core .prereq import PrereqGraph ,all_flowmap_edges
from core .roadmap import build_roadmap ,verify_no_violation

XLSX ="data/majors.xlsx";EDGES ="data/edges.json"
courses =load_major (XLSX ,"인공지능응용융합전공_교과목")
name2code =build_name_index (XLSX )
flow =all_flowmap_edges (EDGES )

g =PrereqGraph ({c .code :c .name for c in courses },enable_l3 =False )
n1 =g .add_flowmap_edges (flow ,name2code );n2 ,n3 =g .add_code_rules ()
print (f"AICE {len (courses )}과목 | 간선 {len (g .edges )} (flowmap {n1 }, code_level {n2 }, code_number {n3 })")

print ("\n=== 시나리오 1: 기이수 없음 (신규 진입) ===")
r =build_roadmap (courses ,g ,taken =set ())
print (r .display_text ())
print (f"총 {r .total_credits }학점 / {len (r .terms )}학기")
v =verify_no_violation (r ,g ,set ())
print (f"선수과목 순서 위배: {len (v )}건 {'✅'if not v else '❌ '+str (v [:3 ])}")

print ("\n=== 시나리오 2: 파이썬 기초만 이수 (신청서 예시 학생) ===")
taken ={"COSE213"}
r2 =build_roadmap (courses ,g ,taken =taken )
print (r2 .display_text ())
v2 =verify_no_violation (r2 ,g ,taken )
print (f"선수과목 순서 위배: {len (v2 )}건 {'✅'if not v2 else '❌'}")
for w in r2 .warnings :print ("  ⚠",w )

print ("\n=== 시나리오 3: 학점상한 12 (부담 경감) ===")
r3 =build_roadmap (courses ,g ,taken =set (),max_credits =12 )
print (f"{len (r3 .terms )}학기, 총 {r3 .total_credits }학점")
v3 =verify_no_violation (r3 ,g ,set ())
print (f"선수과목 순서 위배: {len (v3 )}건 {'✅'if not v3 else '❌'}")
