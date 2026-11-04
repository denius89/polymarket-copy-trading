import base64, hashlib, hmac, html, http.client, json, re, secrets, struct, subprocess, time
from urllib.parse import urlsplit

def ip(service):
    return subprocess.check_output(["sudo","-n","docker","inspect","--format","{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}","shadow-v00-"+service+"-1"],text=True).strip()

def req(host, port, method, path, data=None, token=None, discard=False):
    conn=http.client.HTTPConnection(host,port,timeout=8)
    headers={"Content-Type":"application/json"}
    if token: headers["Authorization"]="Bearer "+token
    conn.request(method,path,json.dumps(data) if data is not None else None,headers)
    response=conn.getresponse()
    status=response.status
    if discard:
        conn.close()
        return status,None
    body=response.read()
    conn.close()
    try: return status,json.loads(body)
    except ValueError: return status,{}

def expect(label,status,allowed):
    print(f"{label}={status}",flush=True)
    if status not in allowed: raise SystemExit("unexpected result: "+label)

auth,mail=ip("auth"),ip("mail")
def api(method,path,**kwargs): return req(auth,9999,method,path,**kwargs)
email="v00-"+secrets.token_hex(8)+"@shadow-v00.invalid"
password=secrets.token_urlsafe(30)
status,_=api("POST","/signup",data={"email":email,"password":password})
expect("synthetic_signup_http",status,{200})
verify_path=None
for _ in range(10):
    _, messages=req(mail,8025,"GET","/api/v1/messages")
    for item in messages.get("messages",[]):
        if not any(addr.get("Address")==email for addr in item.get("To",[])): continue
        _, message=req(mail,8025,"GET","/api/v1/message/"+item["ID"])
        match=re.search(r'https?://[^\s"<>]+/verify\?[^\s"<>]+',html.unescape(message.get("HTML","")+" "+message.get("Text","")))
        if match:
            url=urlsplit(match.group())
            verify_path=url.path+"?"+url.query
            break
    if verify_path: break
    time.sleep(1)
if not verify_path: raise SystemExit("synthetic verification message missing")
print("test_mail_delivered=true",flush=True)

def dbstate():
    query="SELECT count(*) FILTER (WHERE u.email_confirmed_at IS NOT NULL), count(s.id) FROM auth.users u LEFT JOIN auth.sessions s ON s.user_id=u.id WHERE u.email='"+email+"'"
    return subprocess.check_output(["sudo","-n","docker","exec","shadow-v00-db-1","psql","-XAt","-U","postgres","-d","shadow_v00","-c",query],text=True).strip()

before=dbstate()
status,_=api("GET",verify_path,discard=True)
expect("verification_response_dropped_after_headers_http",status,{302,303})
after=dbstate()
status,_=api("GET",verify_path,discard=True)
expect("same_verification_url_replay_http",status,{302,303,400,403,422})
replay=dbstate()
print(f"confirmed_rows_and_session_counts={before},{after},{replay}",flush=True)
assert before=="0|0" and after in ("1|0","1|1") and replay==after

status, body=api("POST","/token?grant_type=password",data={"email":email,"password":password})
expect("provider_login_http",status,{200})
token=body["access_token"]
status, body=api("POST","/factors",token=token,data={"factor_type":"totp","friendly_name":"V00"})
expect("totp_enrol_http",status,{200})
factor=body["id"]
secret=body["totp"]["secret"]
status, body=api("POST",f"/factors/{factor}/challenge",token=token,data={})
expect("totp_challenge_http",status,{200})
challenge=body["id"]

def code_for(step):
    mac=hmac.digest(base64.b32decode(secret+"="*((-len(secret))%8)),struct.pack(">Q",step),hashlib.sha1)
    return str((int.from_bytes(mac[mac[-1]&15:][:4],"big")&0x7fffffff)%1000000).zfill(6)

step=int(time.time())//30
valid=code_for(step)
wrong=next(str(i).zfill(6) for i in range(100) if str(i).zfill(6) not in {code_for(step+j) for j in range(-2,3)})
path=f"/factors/{factor}/verify"
status,_=api("POST",path,token=token,data={"challenge_id":challenge,"code":wrong})
expect("totp_wrong_code_http",status,{400,401,403,422})
valid_step=int(time.time())//30
valid=code_for(valid_step)
status,body=api("POST",path,token=token,data={"challenge_id":challenge,"code":valid})
expect("totp_valid_code_http",status,{200})
print("verify_exposes_matching_steps="+str(any("step" in k.lower() for k in body)).lower(),flush=True)
status,_=api("POST",path,token=token,data={"challenge_id":challenge,"code":valid})
expect("totp_same_challenge_replay_http",status,{400,401,403,404,422})

status, body=api("POST",f"/factors/{factor}/challenge",token=token,data={})
expect("totp_fresh_challenge_http",status,{200})
if int(time.time())//30==valid_step:
    status,_=api("POST",path,token=token,data={"challenge_id":body["id"],"code":valid})
    print(f"totp_same_step_fresh_challenge_http={status}",flush=True)
else:
    print("totp_same_step_fresh_challenge=not_observed_window_changed",flush=True)
