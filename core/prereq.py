from __future__ import annotations
import json
import re
from dataclasses import dataclass
from pathlib import Path

CODE_RE =re .compile (r"^([A-Z]{3,5})(\d{3})")

def parse_code (code :str )->tuple [str |None ,int |None ]:

    m =CODE_RE .match ((code or "").strip ().upper ())
    return (m .group (1 ),int (m .group (2 )))if m else (None ,None )

def level_of (code :str )->int |None :

    _ ,num =parse_code (code )
    return num //100 if num is not None else None

def normalize_name (name :str )->str :

    s =re .sub (r"[\s\-·()]","",str (name ))
    return s .replace ("Ⅰ","I").replace ("Ⅱ","II").replace ("Ⅲ","III").strip ()

@dataclass (frozen =True )
class Edge :

    src :str
    dst :str
    source :str
    confidence :float

    def __repr__ (self )->str :
        return f"{self .src }->{self .dst }({self .source [:4 ]},{self .confidence :.2f})"

CONFIDENCE ={"flowmap":1.00 ,"sheet":1.00 ,"sequence":1.00 ,
"code_level":1.00 ,"code_number":0.71 }

_SEQ =re .compile (r"^(.+?)(III|II|I|[1-3])((?:및.*)?)$")
_RANK ={"I":1 ,"II":2 ,"III":3 }

def sequence_key (name :str )->tuple [str ,int ]|None :

    m =_SEQ .match (normalize_name (name ))
    if not m :
        return None
    rank =_RANK .get (m .group (2 ))or int (m .group (2 ))
    return f"{m .group (1 )}#{m .group (3 )}",rank

class PrereqGraph :

    def __init__ (self ,courses :dict [str ,str ],*,enable_l3 :bool =False ):

        self .courses =courses
        self .enable_l3 =enable_l3
        self .edges :list [Edge ]=[]
        self ._seen :set [tuple [str ,str ]]=set ()

    def _add (self ,src :str ,dst :str ,source :str )->bool :
        if src ==dst or (src ,dst )in self ._seen :
            return False

        if (dst ,src )in self ._seen :
            existing =next (e for e in self .edges if e .src ==dst and e .dst ==src )
            if CONFIDENCE [source ]<=existing .confidence :
                return False
            self .edges .remove (existing )
            self ._seen .discard ((dst ,src ))
        self .edges .append (Edge (src ,dst ,source ,CONFIDENCE [source ]))
        self ._seen .add ((src ,dst ))
        return True

    def add_flowmap_edges (self ,flow_edges :list [tuple [str ,str ]],name2code :dict [str ,str ])->int :

        n =0
        for src_name ,dst_name in flow_edges :
            cs =name2code .get (normalize_name (src_name ))
            cd =name2code .get (normalize_name (dst_name ))
            if cs in self .courses and cd in self .courses and self ._add (cs ,cd ,"flowmap"):
                n +=1
        return n

    def add_sheet_prereqs (self ,prereqs :dict [str ,tuple [str ,...]])->int :

        n =0
        for dst ,srcs in prereqs .items ():
            for src in srcs :
                if src in self .courses and dst in self .courses and self ._add (src ,dst ,"sheet"):
                    n +=1
        return n

    def add_sequence_rules (self )->int :

        groups :dict [str ,list [tuple [int ,str ]]]={}
        for code ,name in self .courses .items ():
            key =sequence_key (name )
            if key :
                groups .setdefault (key [0 ],[]).append ((key [1 ],code ))
        n =0
        for items in groups .values ():
            items .sort ()
            for (ra ,a ),(rb ,b )in zip (items ,items [1 :]):
                if ra <rb and self ._add (a ,b ,"sequence"):
                    n +=1
        return n

    def add_code_rules (self )->tuple [int ,int ]:

        by_prefix :dict [str ,list [str ]]={}
        for code in self .courses :
            pre ,_ =parse_code (code )
            if pre :
                by_prefix .setdefault (pre ,[]).append (code )

        n2 =n3 =0
        for codes in by_prefix .values ():
            for a in codes :
                for b in codes :
                    if a >=b :
                        continue
                    la ,lb =level_of (a ),level_of (b )
                    if la is None or lb is None :
                        continue
                    lo ,hi =(a ,b )if la <lb else (b ,a )
                    if la !=lb :

                        if self ._add (lo ,hi ,"code_level"):
                            n2 +=1
                    elif self .enable_l3 :

                        _ ,na =parse_code (a )
                        _ ,nb =parse_code (b )
                        if na !=nb and self ._add (*((a ,b )if na <nb else (b ,a )),"code_number"):
                            n3 +=1
        return n2 ,n3

    def adjacency (self )->dict [str ,set [str ]]:

        adj :dict [str ,set [str ]]={c :set ()for c in self .courses }
        for e in self .edges :
            adj [e .dst ].add (e .src )
        return adj

    def stats (self )->dict [str ,int ]:
        out ={"total":len (self .edges )}
        for e in self .edges :
            out [e .source ]=out .get (e .source ,0 )+1
        return out

def load_flowmap_edges (path :str |Path )->dict [str ,list [tuple [str ,str ]]]:

    blob =json .loads (Path (path ).read_text (encoding ="utf-8"))
    return {
    dept :[(s ,t )for s ,t in data ["edges"]]
    for dept ,data in blob .items ()
    if not dept .startswith ("_")
    }

def all_flowmap_edges (path :str |Path )->list [tuple [str ,str ]]:

    out :list [tuple [str ,str ]]=[]
    for edges in load_flowmap_edges (path ).values ():
        out .extend (edges )
    return out
