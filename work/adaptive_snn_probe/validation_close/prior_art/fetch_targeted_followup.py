"""Public primary-author/publisher access follow-up; no authentication or bypass."""
from pathlib import Path
import hashlib
import json
import urllib.request
import urllib.error

P=Path(__file__).resolve().parent/'targeted_followup'
P.mkdir(exist_ok=True)
resources=[
 ('mckeown_qub_record.html','https://pure.qub.ac.uk/en/publications/power-efficient-dynamic-range-utilisation-for-dsp-on-fpga/'),
 ('mcallister_eusipco2009.pdf','https://eurasip.org/Proceedings/Eusipco/Eusipco2009/contents/papers/1569193849.pdf'),
 ('yu_macau_author.html','https://ime.um.edu.mo/zh-hans/people-zh-hans/weihan-yu/'),
 ('gong_ustc_author.html','https://cs.ustc.edu.cn/2020/1203/c23239a462623/page.htm'),
 ('udp_releases.json','https://api.github.com/repos/wintermelon008/UDP/releases'),
 ('udp_tree.json','https://api.github.com/repos/wintermelon008/UDP/git/trees/main?recursive=1'),
 ('udp_publisher_pdf_response.bin','https://dl.acm.org/doi/pdf/10.1145/3748173.3779194'),
]
results=[]
for name,url in resources:
    row={'url':url,'primary_host':True,'artifact':name}
    try:
        with urllib.request.urlopen(url,timeout=25) as response:
            body=response.read()
            row.update(status=response.status,content_type=response.headers.get('Content-Type'),
                       final_url=response.url,bytes=len(body))
        (P/name).write_bytes(body)
        row['sha256']=hashlib.sha256(body).hexdigest()
        row['pdf_magic']=body.startswith(b'%PDF-')
    except urllib.error.HTTPError as exc:
        body=exc.read()
        (P/name).write_bytes(body)
        row.update(status=exc.code,error=str(exc),bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),pdf_magic=body.startswith(b'%PDF-'))
    except Exception as exc:
        row.update(error=type(exc).__name__+': '+str(exc))
    results.append(row)
    print(name,row.get('status'),row.get('bytes'),row.get('error',''),flush=True)
(P/'access_checks.json').write_text(json.dumps({'status':'completed_bounded_public_primary_followup',
    'resources':results,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'authentication_attempted':False,'access_restrictions_bypassed':False},indent=2)+'\n')
