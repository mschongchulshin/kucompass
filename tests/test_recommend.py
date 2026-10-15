import warnings ,sys ,pathlib
warnings .filterwarnings ("ignore")
sys .path .insert (0 ,str (pathlib .Path (__file__ ).resolve ().parents [1 ]))
from core import recommend as R

CASES =[
("생물 데이터로 질병 예측 모델을 만들고 싶어요",["인공지능응용","메디컬융합공학","뇌인지과학","미생물융합기술"]),
("주식이나 파생상품 가격 결정에 관심 있어요",["금융공학","PEP"]),
("해킹이랑 보안 쪽 공부하고 싶어요",["정보보호","개인정보보호"]),
("창업해서 소프트웨어 서비스 만들고 싶어요",["소프트웨어기술벤쳐","기술창업"]),
("환경 문제랑 도시 계획에 관심 있어요",["에코스마트시티","기후변화","생태조경"]),
("외국인한테 한국어 가르치고 싶어요",["다문화한국어교육","GKS"]),
("반도체 공정 배우고 싶어요",["차세대반도체"]),
("뇌가 어떻게 작동하는지 궁금해요",["뇌인지과학","LB&C"]),
("공공정책이나 행정 쪽 진로 생각중이에요",["공직과사회규범","공공거버넌스와리더십","PEP"]),
("딥러닝으로 이미지 인식 하고싶어요",["인공지능응용"]),
]

def hit (cands ,gold ,k ):
    names =[c ["major_name"]for c in cands [:k ]]
    return any (any (g in n or n in g for g in gold )for n in names )

for label ,we ,wk in [("키워드만",0.0 ,1.0 ),("임베딩만",1.0 ,0.0 ),("하이브리드(0.7/0.3)",0.7 ,0.3 )]:
    R .W_EMBED ,R .W_KEYWORD =we ,wk
    h1 =h3 =0
    for q ,gold in CASES :
        c =R .recommend (q ,top_k =5 )["candidates"]
        h1 +=hit (c ,gold ,1 );h3 +=hit (c ,gold ,3 )
    print (f"{label :22s} P@1={h1 }/{len (CASES )} ({h1 /len (CASES )*100 :3.0f}%)  "
    f"P@3={h3 }/{len (CASES )} ({h3 /len (CASES )*100 :3.0f}%)")

print ("\n=== 하이브리드 상세 (실패 케이스 확인) ===")
R .W_EMBED ,R .W_KEYWORD =0.7 ,0.3
for q ,gold in CASES :
    c =R .recommend (q ,top_k =3 )["candidates"]
    ok ="O"if hit (c ,gold ,3 )else "X"
    print (f"[{ok }] {q }")
    shown =", ".join ("%s(%.2f)"%(x ["major_name"],x ["score"])for x in c )
    print ("     -> "+shown )
