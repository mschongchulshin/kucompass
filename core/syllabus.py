from __future__ import annotations
import json
import re
import urllib .request
from pathlib import Path

CACHE =Path (__file__ ).resolve ().parent .parent /"data"/"syllabus_cache.json"
BASE ="https://infodepot.korea.ac.kr/lecture1/lecsubjectPlanViewNew.jsp"
def _cache ()->dict :
    if CACHE .exists ():
        try :
            return json .loads (CACHE .read_text (encoding ="utf-8"))
        except Exception :
            return {}
    return {}

def fetch_syllabus (course_code :str ,year :int =2024 ,term :int =2 )->dict :
    key =f"{course_code }:{year }:{term }"
    c =_cache ()
    if key in c :
        return c [key ]

    import os
    if (os .environ .get ("OFFLINE_MODE","").lower ()in ("1","true","yes","on")
    and os .environ .get ("ALLOW_SCHOOL_INTRANET")!="1"):
        return {"error":"오프라인 모드에서는 캐시에 없는 강의계획서를 조회할 수 없습니다. "
        "교내망 조회를 허용하려면 ALLOW_SCHOOL_INTRANET=1 을 설정하세요.",
        "course_code":course_code }

    return {
    "course_code":course_code ,
    "available":False ,
    "reason":"학과코드(dept_cd)·과목코드(cour_cd) 매핑표 미확보",
    "source_url_pattern":f"{BASE }?year={year }&term={term }&cour_cd=...",
    "display_text":(
    f"{course_code }의 강의계획서는 아직 조회할 수 없습니다. "
    "(학과·과목 코드 매핑표 확보 필요 — 디지털전략팀 요청 항목)"
    ),
    }
