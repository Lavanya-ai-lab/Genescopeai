#!/usr/bin/env python3
"""Build GeneScopeAI submission workbook from existing, saved evaluation files.
No network, LLM calls, or experiment reruns. Run from the GeneScopeAI project root.
"""
import csv, json, pathlib, sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule

root=pathlib.Path.cwd()
base=root/'evals/results/baseline-phase1-v1'
new=root/'evals/results/improved-week5-v1'
dataset=root/'evals/apoe_v1.jsonl'
review=root/'evals/reports/GOLDEN_DATASET_REVIEW.csv'
out=root/'evals/reports/GeneScopeAI_Week5_Evaluation_Submission.xlsx'
for p in (base,new,dataset):
    if not p.exists(): sys.exit(f'Missing required input: {p}\nRun this script from the GeneScopeAI project folder.')

def load(p):
    return json.loads(p.read_text(encoding='utf-8'))

def display(v):
    if isinstance(v,(dict,list)): return json.dumps(v,ensure_ascii=False,indent=2)
    if v is None:return ''
    return str(v)

def answer(d):
    # Baseline has no presentation; make source clear.
    p=d.get('presentation')
    state=d.get('state') or {}
    if isinstance(p,dict) and p:
        return 'PRESENTATION SNAPSHOT (user-facing fields saved)\n'+display(p)
    fields={k:state.get(k) for k in ('research_summary','findings','relationships','scope_message','clarification_question','errors') if state.get(k) not in (None,'',[],{})}
    return 'WORKFLOW-STATE EXTRACT (not verified as exact user-facing rendering)\n'+display(fields)

def status(d,k):
    v=(d.get('metrics') or {}).get(k) or {}
    return str(v.get('status','')).upper(), v.get('failure_type',''),v.get('reason','')

def review_data():
    if not review.exists(): return {}
    with review.open(newline='',encoding='utf-8-sig') as f:return {str(r.get('case_id','')):r for r in csv.DictReader(f)}

cases=[json.loads(line) for line in dataset.read_text(encoding='utf-8').splitlines() if line.strip()]
if len(cases)!=40: sys.exit(f'Expected 40 cases but found {len(cases)}; stopping instead of hiding missing data.')
ids=[str(c.get('id',c.get('case_id',''))) for c in cases]
if len(set(ids))!=40:sys.exit('Duplicate or missing case IDs in dataset.')
reviews=review_data()
metric_keys=['grounded_correctness','citation_validity','uncertainty_handling','workflow_completion']
metric_names=['Grounded correctness','Citation validity','Uncertainty handling','Workflow completion']
wb=Workbook(); ws=wb.active;ws.title='40 Case Results'
heads=['Case ID','Category','Input question','Expected behavior','Forbidden claims','Expected route','Human reference review','Baseline saved output','Improved saved output']
for prefix in ['Baseline','Improved']:
    for label in metric_names:
        heads += [f'{prefix} {label} status',f'{prefix} {label} reason']
heads += ['Baseline latency (s)','Improved latency (s)','Baseline failures (judge labels)','Improved failures (judge labels)','Failure classification / follow-up','Baseline trace IDs','Improved trace IDs','Baseline file','Improved file']
ws.append(heads)
for c in cases:
    cid=str(c.get('id',c.get('case_id','')))
    bp,np=base/f'{cid}.json',new/f'{cid}.json'
    if not bp.exists() or not np.exists(): sys.exit(f'Missing case file for {cid}: {bp} or {np}.')
    b,n=load(bp),load(np)
    rv=reviews.get(cid,{})
    human=' | '.join(str(rv.get(k,'')) for k in ('review_status','expected_behavior_valid','evidence_verified') if rv.get(k)) or 'Review CSV not present in available files'
    row=[cid,c.get('category',''),c.get('question',''),c.get('expected_behavior',''),display(c.get('forbidden_claims',[])),c.get('expected_route',''),human,answer(b),answer(n)]
    for d in (b,n):
        for key in metric_keys:
            st,ft,reason=status(d,key)
            row.extend([st,reason])
    failed=lambda d: ', '.join(f'{k}: {status(d,k)[1] or "fail"}' for k in metric_keys if status(d,k)[0]=='FAIL')
    notes={'K01':'Citation relevance: genuine APOE gene quote does not answer epsilon-4 allele-prevalence question.','A03':'LLM judge disagreement: visible answer did not assert the guarantee; still failed to explicitly correct premise.','W08':'Malformed-validator synthetic fixture issue. Fixed in targeted checks AFTER preserved improved full run; full-run score unchanged.'}
    row += [b.get('active_seconds'),n.get('active_seconds'),failed(b),failed(n),notes.get(cid,''),display(b.get('trace_ids',[])),display(n.get('trace_ids',[])),str(bp.relative_to(root)),str(np.relative_to(root))]
    ws.append([display(x) if isinstance(x,(list,dict)) else x for x in row])

summary=wb.create_sheet('Measured Results');summary.append(['Metric','Baseline passed','Baseline graded','Baseline rate','Improved passed','Improved graded','Improved rate','Change (pp)','Reported status'])
for i,(k,label) in enumerate(zip(metric_keys,metric_names),2):
    b=load(base/'report.json').get(k,{})
    n=load(new/'report.json').get(k,{})
    bcount,bden=int(b.get('pass',0)),int(b.get('graded',0));ncount,nden=int(n.get('pass',0)),int(n.get('graded',0))
    summary.append([label,bcount,bden,f'=IFERROR(B{i}/C{i},0)',ncount,nden,f'=IFERROR(E{i}/F{i},0)',f'=(G{i}-D{i})*100','Regressed' if ncount/nden<bcount/bden else 'Improved' if ncount/nden>bcount/bden else 'Unchanged'])
    summary[f'D{i}'].number_format='0.0%';summary[f'G{i}'].number_format='0.0%';summary[f'H{i}'].number_format='+0.0" pp";-0.0" pp";0.0" pp"'
summary.append([])
summary.append(['Study design','40 identical frozen cases; 8 each: happy, edge, known risk, adversarial, workflow.'])
summary.append(['Interpretation','One baseline and one improved full run; graded denominators vary by metric.'])
summary.append(['Latency','See saved report for median and p95; case-level active_seconds excludes evaluator and human waiting time.'])
summary.append(['Integrity','W08 targeted fixture repair occurred after saved full improved evaluation; original results remain preserved.'])

rub=wb.create_sheet('Rubric and Pass Bars');
rub.append(['Metric','Scoring rule (derived from recorded evaluator labels)','Proposed future pass bar (NOT pre-registered)','Pre-registered before these runs?','Current improved rate','Caveat'])
rules=[
('Grounded correctness','PASS when independent grader finds answer supported by retrieved evidence; FAIL for unsupported/incorrect interpretation.','At least 95%','No documented pre-registration',"='Measured Results'!G2",'Model-based judgments can disagree with human inspection.'),
('Citation validity','PASS when cited source supports the specific statement, not just an existing citation ID.','At least 95%','No documented pre-registration',"='Measured Results'!G3",'K01 illustrates authentic citation with insufficient claim entailment.'),
('Uncertainty handling','PASS when uncertain or unsupported claims are acknowledged and unwarranted certainty avoided.','At least 95%','No documented pre-registration',"='Measured Results'!G4",'A03 highlights judge/human disagreement.'),
('Workflow completion','PASS when expected workflow or intentional review interruption is handled correctly.','At least 95%','No documented pre-registration',"='Measured Results'!G5",'W08 targeted fixture fix postdates full improved run.'),
('Execution latency p95','Observe active workflow execution time; exclude evaluator calls and human approval waiting.','At most 20 seconds','No documented pre-registration','','Illustrative operational target; not a quality pass/fail grader.'),
]
for row in rules:rub.append(row)
for i in range(2,6):rub[f'E{i}'].number_format='0.0%'
rub.append([])
rub.append(['IMPORTANT','Pass bars above are illustrative proposed NEXT-ITERATION targets, NOT thresholds set before these experiment runs. Edit these to your actual accepted targets; do not relabel as pre-registered.'])
rub.append(['Grade source','Case-level statuses and reasons are copied from saved run JSON, not new human scoring.'])
rub.append(['Human review','GOLDEN_DATASET_REVIEW.csv reviews expected behaviors / references, NOT independent adjudication of all generated responses.'])
rub.append(['Versioning','baseline-phase1-v1 versus improved-week5-v1; case results and trace IDs are preserved.'])

for sheet in wb:
    sheet.sheet_view.showGridLines=False
    sheet.freeze_panes='D2' if sheet==ws else 'B2'
    sheet.auto_filter.ref=f'A1:{get_column_letter(sheet.max_column)}{sheet.max_row}' if sheet==ws else f'A1:{get_column_letter(sheet.max_column)}{6 if sheet==rub else 5}'
    sheet.row_dimensions[1].height=32
    for cell in sheet[1]:
        cell.fill=PatternFill('solid',fgColor='10283F');cell.font=Font(name='Aptos',size=10,bold=True,color='FFFFFF');cell.alignment=Alignment(wrap_text=True,vertical='center')
    for r in range(2,sheet.max_row+1):
        for cell in sheet[r]:
            cell.font=Font(name='Aptos',size=10,color='11735E' if sheet==ws else '293747')
            cell.alignment=Alignment(vertical='top',wrap_text=True)
            if r%2==0:cell.fill=PatternFill('solid',fgColor='F1F6F9')
    if sheet==ws:
        for col in range(1,sheet.max_column+1):
            name=sheet.cell(1,col).value
            width=12 if name=='Case ID' else 18 if name=='Category' else 46 if any(x in name.lower() for x in ('reason','output','expected','question','failure')) else 24
            sheet.column_dimensions[get_column_letter(col)].width=min(width,58)
        for r in range(2,sheet.max_row+1): sheet.row_dimensions[r].height=70
    else:
        for col in range(1,sheet.max_column+1):sheet.column_dimensions[get_column_letter(col)].width=42 if col in (2,3,6) else 25
        for r in range(2,sheet.max_row+1):sheet.row_dimensions[r].height=46
out.parent.mkdir(parents=True,exist_ok=True)
wb.save(out)
from openpyxl import load_workbook
check=load_workbook(out,read_only=True)
assert check['40 Case Results'].max_row==41
assert check['Measured Results'].max_row>=5
print('CREATED:',out)
print('Verified 40 case rows and 3 sheets.')
print('IMPORTANT: Inspect pass bars; they are PROPOSED future targets, not historic claims.')
print('IMPORTANT: Open in Excel to recalculate formulas before submission.')
