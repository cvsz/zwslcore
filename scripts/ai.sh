#!/usr/bin/env bash
# zwslcore AI CLI - standalone Bash entrypoint with Python stdlib runtime
set -Eeuo pipefail
umask 077
command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 127; }
exec python3 - "$@" <<'PY'
import json, os, sys, pathlib, urllib.request, urllib.error, urllib.parse, ssl, stat, tempfile, time

VERSION = "1.0.0"
ROOT = pathlib.Path(os.environ.get("XDG_STATE_HOME", str(pathlib.Path.home()/".local/state"))) / "zwslcore-ai"
SESSION = os.environ.get("AI_SESSION", "default")
if not SESSION or not all(c.isalnum() or c in "-_" for c in SESSION) or len(SESSION)>64:
    sys.exit("Invalid AI_SESSION: use 1-64 letters, digits, hyphen or underscore")
HISTORY = ROOT / (SESSION + ".json")
DEFAULT_URL = "http://127.0.0.1:8080/v1/chat/completions"
def secure_root():
    if ROOT.is_symlink(): sys.exit("Refusing symlink state directory")
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(ROOT, 0o700)
def load():
    secure_root()
    if HISTORY.is_symlink(): sys.exit("Refusing symlink session")
    if not HISTORY.exists(): return []
    if HISTORY.stat().st_size > 5_000_000: sys.exit("Session too large")
    with HISTORY.open(encoding="utf-8") as f: obj=json.load(f)
    if not isinstance(obj,list): sys.exit("Invalid session format")
    return obj[-40:]
def save(messages):
    secure_root()
    if HISTORY.is_symlink(): sys.exit("Refusing symlink session")
    fd,name=tempfile.mkstemp(dir=ROOT,prefix=".session-",text=True)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(messages[-40:],f,ensure_ascii=False)
            f.flush(); os.fsync(f.fileno())
        os.replace(name,HISTORY)
    finally:
        if os.path.exists(name): os.unlink(name)
def endpoint():
    url=os.environ.get("AI_API_URL",DEFAULT_URL)
    p=urllib.parse.urlsplit(url)
    if p.scheme not in ("http","https") or not p.hostname or p.username or p.password or p.fragment:
        sys.exit("Invalid AI_API_URL")
    if p.scheme=="http" and p.hostname not in ("localhost","127.0.0.1","::1"):
        sys.exit("Remote AI_API_URL must use HTTPS")
    return url
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise urllib.error.HTTPError(args[0].full_url,302,"Redirect refused",{},None)
def ask(prompt):
    history=load()
    messages=[{"role":"system","content":os.environ.get("AI_SYSTEM_PROMPT","You are a helpful technical assistant. Respond in Thai unless asked otherwise.")}]
    messages.extend(x for x in history if isinstance(x,dict) and x.get("role") in ("user","assistant") and isinstance(x.get("content"),str))
    messages.append({"role":"user","content":prompt})
    model=os.environ.get("AI_MODEL","zeaz-auto")
    payload=json.dumps({"model":model,"messages":messages,"stream":False},ensure_ascii=False).encode()
    url=endpoint()
    headers={"Content-Type":"application/json","Accept":"application/json"}
    token=os.environ.get("AI_API_KEY") or os.environ.get("PROVIDER_CLIENT_KEY") or os.environ.get("OPENAI_API_KEY")
    if token: headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(url,data=payload,headers=headers,method="POST")
    opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(req,timeout=float(os.environ.get("AI_TIMEOUT","60"))) as res:
            if res.status!=200: sys.exit("Unexpected HTTP status "+str(res.status))
            data=res.read(2_000_001)
            if len(data)>2_000_000: sys.exit("Response too large")
            obj=json.loads(data)
        answer=obj["choices"][0]["message"]["content"]
        if not isinstance(answer,str): raise ValueError("Non-text response")
    except (urllib.error.URLError,ValueError,KeyError,IndexError,TypeError,TimeoutError) as e:
        sys.exit("Inference failed: "+str(e))
    print(answer)
    history.extend(({"role":"user","content":prompt},{"role":"assistant","content":answer}))
    save(history)
def main():
    args=sys.argv[1:]
    cmd=args.pop(0) if args else "help"
    if cmd in ("help","--help","-h"):
        print("zwslcore AI CLI "+VERSION+"\nUsage: bash scripts/ai.sh [doctor|selftest|ask TEXT|chat|sessions|clear|version]\nEnvironment: AI_API_URL (default local provider), AI_MODEL (default zeaz-auto), AI_API_KEY/PROVIDER_CLIENT_KEY, AI_SESSION, AI_TIMEOUT")
    elif cmd=="version": print(VERSION)
    elif cmd=="doctor":
        print("Python:",sys.version.split()[0]); print("Endpoint:",endpoint()); print("Model:",os.environ.get("AI_MODEL","zeaz-auto"))
        print("Credential configured:",bool(os.environ.get("AI_API_KEY") or os.environ.get("PROVIDER_CLIENT_KEY") or os.environ.get("OPENAI_API_KEY")))
        print("Session:",SESSION)
    elif cmd=="selftest":
        assert SESSION and endpoint()
        secure_root()
        assert stat.S_IMODE(ROOT.stat().st_mode)==0o700
        print("Selftest passed")
    elif cmd=="ask":
        if not args: sys.exit("Usage: ai.sh ask TEXT")
        ask(" ".join(args))
    elif cmd=="chat":
        print("Chat ready. Type /exit to quit.")
        while True:
            try: prompt=input("you> ").strip()
            except (EOFError,KeyboardInterrupt): print(); break
            if prompt in ("/exit","/quit"): break
            if prompt: ask(prompt)
    elif cmd=="sessions":
        secure_root()
        for p in sorted(ROOT.glob("*.json")):
            if not p.is_symlink(): print(p.stem)
    elif cmd=="clear":
        secure_root()
        if HISTORY.is_symlink(): sys.exit("Refusing symlink session")
        HISTORY.unlink(missing_ok=True)
        print("Session cleared")
    else: sys.exit("Unknown command: "+cmd)
if __name__=="__main__": main()
PY
