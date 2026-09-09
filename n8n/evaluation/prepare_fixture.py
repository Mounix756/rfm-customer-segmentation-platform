"""Produire un workflow de recette sans modifier le workflow publié."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
w=json.loads((root/'taiss-tp-final.json').read_text())
w['id']='rfmEvaluationTemplate';w['name']='RFM : recette isolée';w['active']=False
config=next(n for n in w['nodes'] if n['name']=='Configuration')
config['parameters']['jsCode']=config['parameters']['jsCode'].replace('http://segmentation-api:8000','http://eval-api:8090')
next(n for n in w['nodes'] if n['name']=='Webhook')['parameters']['path']='rfm-evaluation'
out=root/'local-exports/evaluation-workflow.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n')
print('Workflow de recette :',out)
