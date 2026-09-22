import importlib, logging, pkgutil
from config import R2_FEATURES, R2_CATEGORY_TREE
COMMANDS = {}
FEATURES = {}
_PENDING = []
def register(*cmds, scope="both"):
    def deco(fn):
        for cmd in cmds:
            if cmd in COMMANDS:
                logging.warning("Duplicate: %s, skip", cmd); continue
            COMMANDS[cmd] = (fn, scope)
        return fn
    return deco
def register_feature_specs(handler_name, runner, category=None):
    cats={category} if category else {c for c,(_,_,h,_) in R2_CATEGORY_TREE.items() if h==handler_name}
    for spec in R2_FEATURES:
        if spec["handler"]==handler_name and spec["category"] in cats: _PENDING.append((runner,spec))
def _finalize_features():
    if not _PENDING: return
    for runner,spec in _PENDING:
        aliases=[]
        for raw in spec["aliases"]:
            alias=raw; n=2
            while alias in COMMANDS or alias in aliases:
                alias=f"/r2-{spec['category']}-{spec['operation']}-{n}"; n+=1
            aliases.append(alias)
        spec["aliases"]=tuple(aliases); FEATURES[spec["id"]]=spec
        def _entry(client,message,cj,chat,sender,args,ctx,_spec=spec): return runner(client,message,cj,chat,sender,args,ctx,_spec)
        _entry.__name__=f"r2_{spec['category']}_{spec['operation']}"; _entry.__qualname__=_entry.__name__
        register(*aliases,scope="both")(_entry)
    _PENDING.clear()
def load_all():
    loaded=[]; failed=[]
    for _,modname,ispkg in pkgutil.iter_modules(__path__):
        if ispkg or modname.startswith("_"): continue
        try: importlib.import_module(f"handlers.{modname}"); loaded.append(modname)
        except Exception as exc: failed.append((modname,str(exc))); logging.exception("Handler '%s' failed",modname)
    if failed: raise RuntimeError(f"Handler load failed: {failed}")
    _finalize_features(); return loaded
def count_commands(): return len(COMMANDS)
def setup_scheduler(client,scheduler):
    load_all()
    for _,modname,ispkg in pkgutil.iter_modules(__path__):
        if ispkg or modname.startswith("_"): continue
        mod=importlib.import_module(f"handlers.{modname}"); hook=getattr(mod,"setup_scheduler",None)
        if callable(hook): hook(client,scheduler)
def detect_owner(*a,**k): return importlib.import_module("handlers.auth").detect_owner(*a,**k)
def owner_uid(*a,**k): return importlib.import_module("handlers.auth").owner_uid(*a,**k)
def ensure_owner_profile(*a,**k): return importlib.import_module("handlers.auth").ensure_owner_profile(*a,**k)
def is_group_admin(*a,**k): return importlib.import_module("handlers.group")._is_group_admin(*a,**k)
