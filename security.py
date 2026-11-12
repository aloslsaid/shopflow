import os, time, bcrypt, jwt
from dataclasses import dataclass
from fastapi import Depends, HTTPException, Header
SECRET = lambda: os.environ["JWT_SECRET"]
ROLES = {"owner": 3, "manager": 2, "staff": 1}
def hash_pw(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def check_pw(p, h): return bcrypt.checkpw(p.encode(), h.encode())
def make_token(uid, sid, role): return jwt.encode({"uid": uid, "sid": sid, "role": role, "exp": int(time.time()) + 3600 * 8}, SECRET(), "HS256")
@dataclass
class Ctx: uid: int; sid: int; role: str   # sid comes ONLY from the signed token, never from request input
def ctx(authorization: str = Header(default="")) -> Ctx:
    try:
        d = jwt.decode(authorization.removeprefix("Bearer "), SECRET(), ["HS256"])
        return Ctx(d["uid"], d["sid"], d["role"])
    except Exception:
        raise HTTPException(401, "invalid or missing token")
def need(min_role):
    def dep(c: Ctx = Depends(ctx)):
        if c.role not in ROLES or min_role not in ROLES:
            raise HTTPException(403, "invalid role")
        if ROLES[c.role] < ROLES[min_role]:
            raise HTTPException(403, "insufficient role")
        return c
    return dep
