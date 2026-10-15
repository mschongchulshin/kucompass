from __future__ import annotations
import ipaddress
import os
import socket

_installed =False
_allowed_ips :set [str ]=set ()
_allowed_hosts :set [str ]=set ()

class EgressBlocked (RuntimeError ):
    pass

def _is_loopback (host :str )->bool :
    try :
        return ipaddress .ip_address (host ).is_loopback
    except ValueError :
        return host in ("localhost","::1")

def allow_host (hostname :str )->None :

    _allowed_hosts .add (hostname .lower ())

def install ()->None :

    global _installed
    if _installed :
        return
    _installed =True

    real_connect =socket .socket .connect
    real_getaddrinfo =socket .getaddrinfo

    def guarded_getaddrinfo (host ,port ,*a ,**kw ):
        res =real_getaddrinfo (host ,port ,*a ,**kw )
        if str (host ).lower ()in _allowed_hosts :
            for entry in res :
                _allowed_ips .add (str (entry [4 ][0 ]))
        return res

    def guarded_connect (self ,address ):

        if self .family not in (socket .AF_INET ,socket .AF_INET6 ):
            return real_connect (self ,address )
        try :
            host =str (address [0 ])
        except Exception :
            return real_connect (self ,address )
        if not (_is_loopback (host )or host in _allowed_ips ):
            raise EgressBlocked (
            f"오프라인 모드에서 외부 연결이 차단됐습니다: {host }. "
            "리다이렉트나 라이브러리 내부 호출일 수 있습니다.")
        return real_connect (self ,address )

    socket .getaddrinfo =guarded_getaddrinfo
    socket .socket .connect =guarded_connect

def install_if_offline ()->None :
    if os .environ .get ("OFFLINE_MODE","").lower ()not in ("1","true","yes","on"):
        return
    if os .environ .get ("ALLOW_SCHOOL_INTRANET")=="1":
        allow_host ("infodepot.korea.ac.kr")
    install ()
