"""Read public primary sources only; retain raw responses and explicit access outcomes."""
import argparse, concurrent.futures, datetime, hashlib, html.parser, json, pathlib, urllib.request

class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.scripts=[]; self.text=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='a' and 'href' in d:self.links.append(d['href'])
        if tag=='script' and 'src' in d:self.scripts.append(d['src'])
    def handle_data(self,data):self.text.append(data)

def fetch(job):
    name,url=job
    out=pathlib.Path(__file__).parent
    result={'name':name,'url':url,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'access_method':'public urllib GET; no login or restriction bypass'}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Academic literature review','Accept':'application/json,text/html,application/pdf;q=0.9,*/*;q=0.8'})
        with urllib.request.urlopen(req,timeout=30) as r:
            raw=r.read();result.update(http_status=r.status,final_url=r.url,content_type=r.headers.get('Content-Type',''))
        path=out/(name+'.response');path.write_bytes(raw)
        result.update(response_path=str(path.resolve()),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
        if b'%PDF-'==raw[:5]:result['kind']='PDF; method review still required'
        else:
            data=raw.decode('utf-8',errors='replace');p=Links();p.feed(data)
            result.update(kind='HTML or API response; not assumed full paper',links=p.links,scripts=p.scripts)
            textpath=out/(name+'.extracted.txt');textpath.write_text('\n'.join(p.text),encoding='utf-8')
            result['extracted_path']=str(textpath.resolve())
    except Exception as e:result.update(kind='access failure',error=type(e).__name__+': '+str(e))
    (out/(name+'.access.json')).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return {k:v for k,v in result.items() if k not in ('response_path','extracted_path')}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('jobs',type=pathlib.Path);a=ap.parse_args()
    jobs=json.loads(a.jobs.read_text(encoding='utf-8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(fetch,jobs):print(json.dumps(result,ensure_ascii=True))
