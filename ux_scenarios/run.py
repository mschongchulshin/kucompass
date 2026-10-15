from __future__ import annotations
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from gradio_client import Client

sys .path .insert (0 ,str (Path (__file__ ).resolve ().parent ))
from scenarios import SEARCH ,ROADMAP ,REQUIREMENTS ,CHAT

URL =os .environ .get ("KUC_URL","http://127.0.0.1:7860/")
OUT =Path (__file__ ).resolve ().parent /"results.json"


def _text (content )->str :
    if isinstance (content ,str ):
        return content
    if isinstance (content ,list ):
        return "\n".join (_text (c )for c in content )
    if isinstance (content ,dict ):
        return content .get ("text")or content .get ("value")or ""
    return str (content )


def _timed (fn ,*args ,**kw ):
    t =time .time ()
    out =fn (*args ,**kw )
    return out ,round (time .time ()-t ,2 )


def main (only :str |None =None )->None :
    client =Client (URL ,verbose =False )
    sections =set (only .split (","))if only else {"search","roadmap","requirements","chat"}
    results =json .loads (OUT .read_text ())if OUT .exists ()else {}
    results ["server"]=URL
    results .setdefault ("run_at",{})
    if not isinstance (results ["run_at"],dict ):
        results ["run_at"]={}
    for sec in sections :
        results [sec ]=[]
        results ["run_at"][sec ]=datetime .now ().isoformat (timespec ="seconds")

    if "search"in sections :
        for s in SEARCH :
            out ,sec =_timed (client .predict ,s ["text"],api_name ="/_direct_search")
            results ["search"].append ({**s ,"response":out ,"seconds":sec })
            print (s ["id"],sec ,"s",flush =True )

    if "roadmap"in sections :
        for s in ROADMAP :
            out ,sec =_timed (client .predict ,s ["major"],s ["taken"],s ["cap"],"3학년 1학기",
            api_name ="/_direct_roadmap")
            results ["roadmap"].append ({**s ,"response":out ,"seconds":sec })
            print (s ["id"],sec ,"s",flush =True )

    if "requirements"in sections :
        for s in REQUIREMENTS :
            out ,sec =_timed (client .predict ,s ["major"],s ["taken"],
            api_name ="/_direct_req")
            results ["requirements"].append ({**s ,"response":out ,"seconds":sec })
            print (s ["id"],sec ,"s",flush =True )

    if "chat"in sections :
        reps =int (os .environ .get ("CHAT_REPS","1"))
        for s in CHAT :
            turns =s .get ("turns")or [s ["text"]]
            runs =[]
            for rep in range (reps ):
                fresh =Client (URL ,verbose =False )
                history :list =[]
                steps =[]
                for msg in turns :
                    (history ,tools ),sec =_timed (fresh .predict ,msg ,history ,
                    api_name ="/respond")
                    reply =_text (history [-1 ].get ("content"))if history else ""
                    shown =_text (history [-2 ].get ("content"))if len (history )>1 else msg
                    steps .append ({"input":msg ,"shown_input":shown ,"response":reply ,
                    "tools":tools ,"seconds":sec })
                runs .append (steps )
                print (s ["id"],"rep",rep +1 ,[st ["seconds"]for st in steps ],flush =True )
            results ["chat"].append ({**s ,"runs":runs })

    OUT .write_text (json .dumps (results ,ensure_ascii =False ,indent =1 ))
    print ("saved",OUT )


if __name__ =="__main__":
    main (sys .argv [1 ]if len (sys .argv )>1 else None )
