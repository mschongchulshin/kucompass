import os

def _offline ()->bool :
    return os .environ .get ("OFFLINE_MODE","").lower ()in ("1","true","yes","on")

if _offline ():

    os .environ .setdefault ("HF_HUB_OFFLINE","1")
    os .environ .setdefault ("TRANSFORMERS_OFFLINE","1")
    os .environ .setdefault ("HF_DATASETS_OFFLINE","1")
    os .environ .setdefault ("HF_HUB_DISABLE_TELEMETRY","1")

    from core import netguard
    netguard .install_if_offline ()
