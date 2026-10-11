import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const ROOT=path.resolve(import.meta.dirname,'../../..');
const SKILL='C:/Users/Ritesh/.codex/plugins/cache/openai-primary-runtime/presentations/26.1009.11318/skills/presentations';
process.env.RUNTIME_NODE_MODULES='C:/Users/Ritesh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {finalizePresentation,resolvePresentationFont,applyPresentationChartFont}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const FONT=resolvePresentationFont({fontFamily:'Arial'});
const OUT=path.join(ROOT,'outputs/mentor_handoff');
const BUILD=import.meta.dirname;
const SOURCE=path.join(ROOT,'work/adaptive_snn_probe/validation_close/width16/constant_glif_readiness/hardware/power12_glif_mcm_energy_recovery_a0/power_audit.json');
const AUDIT=path.join(ROOT,'work/adaptive_snn_probe/validation_close/width16/constant_glif_readiness/independent_readiness_full_a0.json');
let mcm=null;try{const d=JSON.parse(await fs.readFile(SOURCE,'utf8'));const a=JSON.parse(await fs.readFile(AUDIT,'utf8'));if(d.status==='pass'&&a.status==='pass'&&a.energy_audit?.status==='pass'&&a.energy_audit.estimated_dynamic_energy_pJ_per_scalar_update===d.estimated_dynamic_energy_pJ_per_scalar_update)mcm=d.estimated_dynamic_energy_pJ_per_scalar_update;}catch{}
const p=Presentation.create({slideSize:{width:1280,height:720}});
const navy='#172C42',teal='#007E87',amber='#B06018',gray='#536573';
let notes=[];
function polish(t){
 for(const [a,b]of [['fullsigned16','full signed16'],['oneDSP','one DSP'],['twoDSPs','two DSPs'],['TwoDSP','Two DSP'],['zeroDSP','zero DSP'],['ZeroDSP','Zero DSP'],['scalarDSP','scalar DSP'],['all33','all 33'],['All33','All 33'],['add255','add 255'],['byte255','byte 255'],['field894','field 894'],['result3','result 3'],['field256','field 256'],['into255','into 255'],['quotient0','quotient 0'],['into1','into 1'],['gives117','gives 117'],['give−39','give −39'],['consume1','consume 1'],['or2','or 2'],['same12ns','same 12 ns'],['shared94','shared 94'],['Shared94','Shared 94'],['at25','at 25'],['saves60','saves 60'],['uses2','uses 2'],['use0','use 0']])t=t.replaceAll(a,b);
 return t.replace(/\b(all|full|at|versus|with|of|uses|common|Common|through|their|its|by|from|then|a|and|the|beta|subtracts|quotient|to|computes|but|predeclared|matched|coefficient|Figure|Table|Equation|Equations|bits|bit|adds|are)(?=\d)/g,'$1 ').replace(/(\d)(LUT|FF|DSP|pJ|ns|°C|bits|images|image|cases|operands)/g,'$1 $2').replaceAll('GLIF:1.852','GLIF: 1.852');
}
function text(s,t,x,y,w,h,size=28,color=navy,bold=false){
 const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=polish(t);a.text.style={typeface:FONT,fontSize:size,color,bold,verticalAlignment:'middle'};a.text.insets=0;return a;
}
function slide(title,note){
 const s=p.slides.add();s.background.fill='#FAFBFC';
 text(s,title,66,46,1148,86,44,navy,true);
 text(s,String(p.slides.items.length).padStart(2,'0'),1166,666,50,28,18,gray);
 s.speakerNotes.text=polish(note);notes.push({title,note:polish(note)});return s;
}
function body(s,t,y=175,h=420){return text(s,t,74,y,1120,h,30);}
function caption(s,t,y=626){return text(s,t,74,y,1080,44,20,gray);}
function box(s,label,x,y,w,h,color=teal){
 const a=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:'#FFFFFF',line:{fill:color,width:2}});
 a.text=label;a.text.style={typeface:FONT,fontSize:25,color:navy,bold:false,alignment:'center',verticalAlignment:'middle'};return a;
}
function join(s,a,b,from='right',to='left'){s.shapes.connect(a,b,{kind:'elbow',fromSide:from,toSide:to,line:{fill:teal,width:2},tail:{type:'triangle',width:'sm',length:'sm'}});}
function table(s,values,x=72,y=180,w=1136,h=380,widths=null){
 values=values.map(row=>row.map(value=>typeof value==='string'?polish(value):value));
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,values,...(widths?{columnWidths:widths}:{})});
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({textStyle:{typeface:FONT,fontSize:24,color:navy},fill:'#FFFFFF',margins:{left:12,right:12,top:8,bottom:8}});
 t.cells.block({row:0,column:0,rowCount:1,columnCount:values[0].length}).assign({fill:navy,textStyle:{typeface:FONT,fontSize:24,color:'#FFFFFF',bold:true}});
 return t;
}
function bars(s,categories,values,unit,y=175,h=390){
 const c=s.charts.add('bar',{position:{left:70,top:y,width:1138,height:h},categories,series:[{name:unit,values,fill:teal}],hasLegend:false,barOptions:{direction:'column',grouping:'clustered',gapWidth:70},dataLabels:{showValue:true,position:'outEnd',textStyle:{fontSize:23}},xAxis:{textStyle:{fontSize:23}},yAxis:{title:{text:unit,textStyle:{fontSize:22,typeface:FONT}},numberFormatCode:'0.0',textStyle:{fontSize:23},majorGridlines:{fill:'#DDE5E9',width:1}},chartFill:'#FAFBFC',plotAreaFill:'#FAFBFC'});
 applyPresentationChartFont(c,{fontFamily:FONT});return c;
}
// All diagrams below are requested editable scientific/architecture evidence.
{
 const s=p.slides.add();s.background.fill=navy;
 text(s,'Exact adaptive DSP packing\nfor SNN membrane leakage',74,174,1110,196,58,'#FFFFFF',true);
 text(s,'Mechanism, worked examples and verified trade-offs',78,402,1110,75,30,'#D7EBEE');
 text(s,'Mentor briefing · X · 11 October 2026',78,580,1000,46,24,'#D7EBEE');
 const note='This deck explains the research from the beginning. The evaluated primitive performs exact integer membrane leakage. The project originally explored synaptic accumulation and overflow representations, but the strongest retained mechanism now concerns leakage multiplication. Author X is the user-requested placeholder. No acceptance or proven first-ever claim is implied.';
 s.speakerNotes.text=note;notes.push({title:'Exact adaptive DSP packing for SNN membrane leakage',note});
}
{
 const s=slide('Leakage inside a neuron update','LIF means leaky integrate-and-fire. A neuron stores a membrane U. Incoming weighted spikes provide a current. Leakage decays the old membrane, charge combines with it, and threshold/reset produces the next state and spike. Models differ in reset timing, threshold equality and coefficient selection. This schematic explains the role only. The evaluated adapters preserve each original model ordering. The measured FPGA primitive is only the leakage block, not all blocks shown. Sources: paper Sections II and IV, original GLIF/OTTT/TinyImageNet source manifests.');
 const mem=box(s,'Stored membrane U',74,230,245,100,navy),leak=box(s,'Leakage\nL(U, β)',405,230,225,100),sum=box(s,'Charge / current\ncombination',715,230,220,100,navy),thr=box(s,'Threshold\nand reset',1006,230,210,100,navy);
 join(s,mem,leak);join(s,leak,sum);join(s,sum,thr);
 const inp=box(s,'Weighted input spikes',682,420,280,90,navy);join(s,inp,sum,'top','bottom');
 caption(s,'The teal leakage block is the operation measured in this study');
}
{
 const s=slide('The exact integer contract','Unsigned Q8 beta is an integer code 0 through256. The effective coefficient is beta/256. U uses signed16 units. For every legal input, L=ceil(beta U/256). The signed numerator beta U+255 followed by arithmetic shift8 implements the ceiling for positive and negative values. Quantizing an FP32 neuron into this declared contract is a separate conversion with measured changed predictions. Packing itself adds zero error relative to the integer neuron. Sources: domain_acceptance_glif_v2.json, paper Equation1 and model summaries.');
 text(s,'L(U, β) = ceil(β × U / 256)',74,182,1110,100,46,teal,true);
 body(s,'Membrane U: signed16, −32768 to 32767\nCoefficient code β: 0 to 256\nExample: β = 128 means half leakage\nStored precision stays at 16 bits',330,270);
}
{
 const s=slide('Runtime admission uses actual membranes','E5 receives two available consecutive operands and their individual beta codes. It computes signed9 fit and coefficient equality internally. When both fit and beta matches, it returns take2 and two results. Otherwise it returns take1 and one exact fullsigned16 result. available0 produces no accepted request. No external packing decision is supplied. The queue and memory remain external, while range/equality/mux/correction/valid-ready are counted. Source: rtl/leak_core16.sv, E5 generate branch and take expression.');
 table(s,[['Condition at this request','Action'],['Both U values in [−256,255] and β equal','Pack two operations'],['A membrane is wider or coefficients differ','Execute first as signed16 singleton'],['Only one operand remains in the frame','Execute that singleton']],72,182,1136,290,[770,366]);
 text(s,'Adaptation changes issue occupancy\nIt preserves values, units and stored width',74,518,1100,100,32,teal,true);
}
{
 const s=slide('Worked stream and source advancement','The example uses operands [(-3,128),(5,128),(381,78),(-2,128),(7,128)]. There is no zero filtering in this toy. The core pairs first two, consumes wide381 alone, then pairs remaining two. Outputs are -1,3,117,-1,4. This uses three issues versus five scalar issues. Fixed full-domain split can also use three here because coefficient mismatch prevents its second pair. The example explains correctness and source advancement, not an advantage over all fixed packing. Source: examples/run_examples.py, independently computed integer ceilings.');
 table(s,[['DSP issue','Input(s), β','Count','Exact output(s)'],['1','−3 and 5, β=128','2','−1 and 3'],['2','381, β=78','1','117'],['3','−2 and 7, β=128','2','−1 and 4']],72,180,1136,320,[210,486,130,310]);
 text(s,'The source retains unconsumed operands\nFive scalar updates use three DSP issues in this example',74,536,1100,78,30,teal,true);
}
{
 const s=slide('A compact multiplicand layout','The multiplicand A=(u0+256)+(u1<<16) fits signed25. u0+256 occupies nine low bits and u1 occupies the signed upper nine bits separated by seven zeros. The DSP uses coefficient beta and offset C=255−256beta+255·2^16. After multiplication, the low product x=beta u0+255 can be negative. This is why one borrow crosses the stride16 boundary. The figure shows A fields, not independent product slots. Source: paper Equations2–4 and leak_core16.sv packed9.');
 text(s,'A = (u₀ + 256) + (u₁ << 16)',74,170,1110,68,39,teal,true);
 box(s,'signed9 u₁\nbits24:16',86,282,396,116);
 box(s,'seven zeros\nbits15:9',482,282,308,116,gray);
 box(s,'u₀ + 256\nbits8:0',790,282,396,116);
 body(s,'One coefficient multiplies both lanes\nThe products overlap through a possible signed borrow',452,130);
 caption(s,'C = 255 − 256β + 255 × 2¹⁶ supplies exact ceiling offsets');
}
{
 const s=slide('The low product can borrow one bit','Define x=beta u0+255 and y=beta u1+255. Since -65536<x<65536, floor(x/65536) is either0 or-1. Therefore T=floor(P/65536)=y−n with n=1{x<0}. The known parity of y is r=((beta&1)&(u1&1)) XOR1. Subtracting n toggles that parity, recovering n=bit16(P) XORr. This avoids a broad product reconstruction. Sources: exhaustive stage3_algebra.json and manuscript decoder proof.');
 text(s,'P = x + 2¹⁶ y',74,176,1080,76,46,teal,true);
 body(s,'x = βu₀ + 255 can be negative\nThe upper field becomes y − n, where n is 0 or 1\nKnown parity of y recovers that borrow n\nOnly the rounded output needs correction',320,286);
}
{
 const s=slide('Negative-borrow example','u0=-3,u1=5,beta128 gives x=-129,y895,n1. P=-129+65536×895. The unsigned P15:8 is255 and L0=255−256=-1. T=y−n894 and floor(T/256)=3, so adding back the borrow does not cross a byte boundary and L1=3. The reference gives ceil(-384/256)=-1,ceil(640/256)=3. Source: examples/run_examples.py.');
 table(s,[['Step','u₀ = −3','u₁ = 5'],['β = 128, multiply and add255','x = −129','y = 895'],['Overlapping packed field','quotient byte255','upper field894'],['Exact correction','255 − 256 = −1','no byte crossing, result3'],['Independent integer reference','ceil(−384/256) = −1','ceil(640/256) = 3']],72,180,1136,390,[400,365,371]);
 caption(s,'The recovered borrow corrects the signed lower lane exactly');
}
{
 const s=slide('A byte-boundary correction and wide fallback','For (-256,1,beta1), x=-1,y256,n1,T255. Low result255−256=-1. Upper truncated quotient0 receives +1 because T low byte255, recovering L1. This confirms the upper correction at the boundary. Separately381/beta78 lies outside signed9. Correct ceiling117 differs from unsafe wrapped -39. E5 takes a wide singleton instead. Sources: portable examples and GLIF capture unsafe-wrap check.');
 text(s,'Pair: u₀ = −256, u₁ = 1, β = 1',74,182,1120,72,37,teal,true);
 body(s,'The borrow turns upper field256 into255\nRestoring it changes the upper quotient0 into1\nExact pair output: (−1, 1)',282,220);
 text(s,'Wide singleton: U = 381, β = 78 gives117\nUnsafe signed9 wrapping would give−39',74,542,1110,94,30,amber,true);
}
{
 const s=slide('Counted core and external source','The measured E5 has62LUT44FF1DSP. It includes actual signed9 fit/equality, packed/singleton selection, valid-ready elasticity and exact quotient correction. The source supplies two operands, honors take on acceptance, and retains unconsumed operands. External memory, queue, common zero-filter and integration are unmeasured. The common route/activity fixture adds94FF excluded area but included energy. Native unstalled request latency is two advancing edges. Sources: hardware/route12_e5_a0/hardware.json, rtl/timing16.sv, manuscript Figure1.');
 const a=box(s,'External source\nand zero filter',72,210,240,100,gray);
 const b=box(s,'Range + β tests\nPair / singleton',382,210,254,100);
 const c=box(s,'One DSP48E1\nregistered result',720,210,260,100);
 const d=box(s,'Borrow recovery\nQuotient correction',720,432,260,100);
 const e=box(s,'Ordered signed16\nresults and count',382,432,254,100);
 join(s,a,b);join(s,b,c);join(s,c,d,'bottom','top');join(s,d,e,'left','right');join(s,b,a,'left','right');
 text(s,'consume1 or2 after acceptance',72,330,575,66,24,gray);
 caption(s,'Two advancing edges without stalls. Source memory and complete-neuron scheduling remain external');
}
{
 const s=slide('Strong controls execute the same operation','E1 decomposes U=256h+q,0<=q<=255 and computes beta h+ceil(beta q/256). DSP residue packing and fabric high parts cover fullsigned16 same-beta pairs with oneDSP. E3 uses two scalarDSPs. E4 uses one scalarDSP. E7 exact general LUT has noDSP. E6 halfshift legalonlybeta128. E9 shared MCM accepts all33 trainedGLIF beta codes with independent two lanes and full16. The controls are constructed matched primitives, not measured FireFly complete accelerators. Sources: route and energy manifests.');
 table(s,[['Control','Purpose'],['E1 fixed split, oneDSP','Fullsigned16 pairs with exact fabric high parts'],['E3 / E4 scalarDSP','TwoDSP pair / oneDSP singleton'],['E7 general LUT pair','Exact full domain, zeroDSP'],['E6 half-leakage shift','Exact zeroDSP control for β=128'],['E9 shared GLIF constants','ZeroDSP pair supporting all33 trained codes']],72,177,1136,390,[388,748]);
 caption(s,'Same operation, same12ns route fixture, same operands within each energy comparison');
}
{
 const s=slide('Exactness and protocol validation','Saved exhaustive arithmetic covers67,371,008 signed9 pairs and16,842,752 fullsigned16 scalar/split cases with zeroerror. Main general nativeRTL covers360,487 operations per engine under stalled and unstalled protocols plus representative captures. E9 new check all65536×33=2,162,688 scalarcases and262528 workload operands both stalled and unstalled, independent full rawoutputcheck. These are arithmetic/RTL comparisons, separate from model feedback and physical energy gates. Source: stage3_algebra.json, domain_acceptance_glif_v2.json, native receipts, E9 independent_readiness_native_only_a0.json.');
 body(s,'67,371,008 exhaustive narrow pair cases\n16,842,752 full-domain scalar / split cases\nStalled RTL checks verify order and held outputs\nAll33 GLIF coefficients pass exhaustive new-control RTL',190,355);
 text(s,'Zero differences from the declared integer oracle',74,565,1120,70,35,teal,true);
}
{
 const s=slide('Public neuron model benchmarks','GLIF ResNet18CIFAR10T2 full10k integer94.05vsFP3294.03,371changedpredictions. Packedfeedback64images159383552updates exact. OTTTVGG11CIFAR10T6 full10kpacked93.45vsFP3293.49,104changedpredictions,24576000000updatesexact. TinyImageNetScientificReportsreleasedBNTTstyleVGG11T30 selected64FP3242correct/integer41correct,onepredictionchange,1171783680updatesexact. All observed old/next storedstatesfit16. Different sizes are intentional scope distinctions. Packing exactness does not preserve original floating outputs. Sources: stage2_acceptance, stage3_results, benchmark_acceptance, bntt_acceptance.');
 table(s,[['Model / dataset','Validation scope','Packing result'],['GLIF ResNet18 / CIFAR10 / T2','10k conversion,64 packed','All integer states/spikes/logits agree'],['OTTT VGG11 / CIFAR10 / T6','10k packed feedback','All integer updates agree'],['BNTT-style VGG11 / TinyImageNet / T30','Predeclared64-image subset','All integer states/spikes/logits agree']],72,176,1136,342,[430,305,401]);
 text(s,'FP32-to-integer conversion changes some predictions\nPacking adds no further differences in these checks',74,547,1110,86,29,teal,true);
}
{
 const s=slide('Selected core resource trade-offs','Selected matched routes use a 12 ns clock. E1: 202 LUT, 79 FF, 1 DSP. E5: 62 LUT, 44 FF, 1 DSP. E3: 35 LUT, 56 FF, 2 DSP. E4: 13 LUT, 29 FF, 1 DSP. E7: 330 LUT, 88 FF, 0 DSP. E9: 375 LUT, 82 FF, 0 DSP. The common 94 fixture FFs are excluded. E5 saves 69.31% LUTs and 44.30% FFs against E1 at the same DSP budget. E9 is one checkpoint-restricted shared add/sub implementation, not an optimum bound. Sources: selected hardware.json receipts and E9 hardware/route12_a0/hardware.json.');
 bars(s,['E4 scalar','E3 pair','E5 adaptive','E1 fixed','E7 LUT','E9 constants'],[13,35,62,202,330,375],'Core LUTs',176,360);
 text(s,'E5: 62LUT / 44FF / 1DSP\nE1: 202LUT / 79FF / 1DSP',74,553,1110,77,29,teal,true);
 caption(s,'E3 uses2DSP. E7 and E9 use0DSP. Shared94 fixture FFs excluded from core area',645);
}
{
 const extra=mcm===null?'The E9 energy audit is not accepted yet. No value is plotted.':`The shared33-code E9 accepted estimated energy is${mcm}pJ/scalar.`;
 const s=slide('Representative GLIF dynamic energy',`Same262528nonzerooperands distribution-gated windows. Acceptedfixtureenergy: E321.3710653,E521.5994968,E424.6483755,E155.3083846,E7124.1983064pJ/scalar. E5vsE4 -12.3695%,vsE1 -60.9472%,vsE7 -82.6089%,vsE3 +1.0689% with halfDSP. ${extra} No board/static/memory/full-neuron energy. Sources: explicit selected power map, physical audits, E9 fresh audit when present.`);
 const categories=['E3 pair','E5 adaptive','E4 scalar','E1 fixed','E7 LUT'];const values=[21.371,21.599,24.648,55.308,124.198];
 if(mcm!==null){categories.push('E9 constants');values.push(Number(mcm.toFixed(3)));}
 bars(s,categories,values,'pJ per scalar operand',177,365);
 text(s,'E5 saves60.95% against E1\nE3 remains near energy parity using twoDSPs',74,553,1110,78,29,teal,true);
 caption(s,'Estimated fixture dynamic energy at25°C. Common94 fixture FFs included',645);
}
{
 const s=slide('Pairing opportunity depends on the workload','GLIF nonzero79246135 signed9fit99.0189%, E5issues42785698 E142327032 +1.0836%, E5vsE4 -46.0091%. OTTTfull E515836088695 E110220498016 +54.9444%; TinyImageNet64 E5676214768 E1532325552 +27.0303%. Modelissues exclude commonzerogroups and are not complete-neuron cycles. RepresentativeenergyGLIF captureissuepenalty1.0821% differs slightlyfullstream1.0836%. Sources: stream profiles and Table2.');
 bars(s,['GLIF 64','OTTT 10k','TinyImageNet 64'],[1.0836,54.9444,27.0303],'Extra issues versus E1 (%)',177,365);
 text(s,'GLIF:1.852 useful results per issue\nWider membranes make fixed full-domain pairs more attractive',74,558,1110,82,29,teal,true);
}
{
 const s=slide('Constant leakage defines an important negative case','OTTT beta128 has exactceil(U/2) implemented as arithmeticshiftplusLSB. E6 zeroDSP35LUT70FF13.6576240pJ/scalar. E5OTTT26.5796283 is94.6139% moreenergy. E1general36.8075674. BNTT beta253 exactL=U-floor(3U/256), provenall65536hardwareunmeasured. E9 closes a particular sharedGLIFconstantcontrol rather than proves no other optimizedconstantimplementationcanwin. Sources: OTTT representative acceptedclosure and BNTT exactconstantcheck.');
 bars(s,['OTTT half shift','OTTT E5','OTTT E1'],[13.658,26.580,36.808],'OTTT representative pJ/scalar',178,330);
 text(s,'For β=128, exact shifting wins\nFor β=253, an exact shift/add identity also exists',74,525,1110,96,31,amber,true);
 caption(s,'The β=253 circuit and energy have not been measured');
}
{
 const s=slide('Specific novelty and established ingredients','Mechanism contribution need not inventeverycomponent. Specific economicalroundeddecoder plusactualUadmission andfullsigned16singleton, fixedprecision andmeasuredtradeoffs. Valuebasedoperationpacking BroooksMartonosi2000 DOI10.1145/350853.350856; DSPpacking arXiv2203.11028; exactspillArithmeticPacking2606.11065; runtimeprecisionXtraMAC2605.06052. Inspected UDP DOI10.1145/3748173.3779194 methodsnotactualUpolicy. ThreeunavailableoriginalsOu10.1109/TCSII.2024.3377356Cui10.1109/ICFPT64416.2024.11113473McKeown10.1109/SIPS.2008.4671768. No worldwidefirsteverclaim. Source: paper relatedwork and readinessreview.');
 body(s,'Established: value-based packing and signed correction\nSpecific mechanism: compact exact leakage quotient recovery\nIntegrated contribution: actual-U admission with wide fallback\nEvidence: measured same-operation trade-offs and model exactness',176,365);
 text(s,'A new integrated mechanism can contribute\nA proven worldwide first-ever claim is unnecessary here',74,568,1110,82,29,teal,true);
}
{
 const s=slide('Paper recommendation and remaining limits','Proceed with focusedISCASprimitivepaper supportedbyexactmathnativeRTLpublicmodelsroutesandcertifiedfixtureenergy. Acceptance/strongnessreviewdecision. Do notclaimwholeacceleratorthroughput,boardenergy,burstlatency,accuracylift,allworkloadwin. ExistingE2timedCARRY4 discrepancy localized withpreciseeventschedulingunresolved, energyexcluded; independentlyacceptedE7comparisonvalid. Threefullmethodsunavailable.BNTTconstanthardwareunmeasured.Variableconsumptionsourceintegrationexcluded. Xplaceholderauthorizedfinalauthordetailsneededbeforesubmission. Source: currentpaperandreadinessreport.');
 body(s,'Proceed with a focused leakage-primitive submission\nKeep the exact decoder and membrane admission as one contribution\nReport positive GLIF trade-offs and constant-leakage negative cases\nKeep external integration and board-level claims outside the evidence',176,344);
 text(s,'Readiness supports submission preparation\nReviewers determine novelty significance and acceptance',74,558,1110,89,29,teal,true);
}
{
 const s=slide('Mentor handoff and reproduction','The repository contains the paper, code, examples, evidence and chat export. Weights, datasets and vendor libraries remain external. The release manifest checks relative file hashes. Historical absolute paths record provenance. Review the neuron equation, reset timing, prior-work equivalence, architectural boundary and claims. Source: README and docs/REPRODUCIBILITY.md. AI disclosure: OpenAI Codex assisted RTL, software, evidence review, drafting and slides. X is the author placeholder.');
 text(s,'github.com/riteshdasari/membrane-leakage-packing',74,176,1110,74,32,teal,true);
 body(s,'README and worked integer examples\nIEEE paper source and editable diagrams in these slides\nFull user-facing chat export and archived research code\nEvidence manifest with accepted results and failed attempts',290,273);
 caption(s,'OpenAI Codex assisted prototyping, validation, analysis, drafting and slides. Author placeholder: X');
}
{
 const s=slide('Appendix: exact decoder equations','The lower quotient takes product bits15:8 as an unsigned byte and subtracts256 times the recovered borrow. The upper quotient interprets bits32:24 as a signed9 value and adds1 only if the borrow exists and product bits23:16 are255. Bits denote positions in the two-complement product. The parity reference needs only coefficient bit0 and upper membrane bit0. Source: manuscript Equations5–6 and examples/leakage_reference.py.');
 text(s,'r = (LSB(β) AND LSB(u₁)) XOR 1\nn = P₁₆ XOR r',74,166,1110,128,35,teal,true);
 body(s,'L₀ = unsigned(P[15:8]) − 256n\nL₁ = signed9(P[32:24]) + (n AND P[23:16] = 255)',332,142);
 text(s,'P[i:j] selects inclusive bits i through j\nLSB denotes the least significant bit (odd/even parity)',74,538,1110,90,28,gray);
}
{
 const s=slide('Appendix: the exact fixed split reference','Fixed E1 writes U = 256h + q, where q lies between 0 and 255 and h = floor(U/256). It computes beta times h in fabric and packed beta times q in the DSP. Since beta times h is an integer, ceil(beta U/256) = beta h + ceil(beta q/256). For U = 381 and beta = 78, h = 1 and q = 125, giving 78 + 39 = 117. For U = -3 and beta = 128, h = -1 and q = 253, giving -128 + 127 = -1. It preserves full-domain pair occupancy but pays for the high-part arithmetic. Source: manuscript fixed control equation and leak_core16.sv E1 split branch.');
 text(s,'U = 256h + q, with 0 ≤ q ≤ 255',74,168,1110,62,36,teal,true);
 text(s,'L = βh + ceil(βq / 256)',74,242,1110,65,36,teal,true);
 table(s,[['Input','High part in fabric','Residue in DSP','Exact sum'],['U=381, β=78','78 × 1 = 78','ceil(78 × 125 / 256) = 39','117'],['U=−3, β=128','128 × (−1) = −128','ceil(128 × 253 / 256) = 127','−1']],72,349,1136,223,[235,285,426,190]);
 caption(s,'Fixed E1 keeps full-domain pair occupancy and pays for the high-part fabric');
}
const explanations=[
 'This briefing begins with the neuron operation, then explains runtime packing and its exact decoder. The retained contribution concerns membrane leakage multiplication. Earlier accumulation and overflow candidates appear in the archived conversation, but they are not the measured contribution in this paper.',
 'A leaky integrate-and-fire neuron stores membrane potential U. Leakage decays the previous membrane. Input current charges it, and threshold/reset rules produce the next state and spike. Different source models order these steps differently. The evaluation adapters preserve each original ordering. Only the highlighted leakage primitive has measured FPGA costs.',
 'Beta is an integer Q8 coefficient code. Its effective leakage factor is beta/256. Ceiling rounds toward positive infinity, so ceil(-1.5) is -1. The circuit preserves this declared integer operation. Converting an original floating neuron to integer units is separate and can change predictions.',
 'Admission checks actual values, not only configured operand types. Two small membranes with the same coefficient share a DSP issue. A wide membrane or coefficient mismatch causes an exact singleton. The membrane remains stored at16bits. The returned count determines source advancement.',
 'This example uses five ordered operands. The source advances by2, then1, then2, preserving the unconsumed next operand. Results are -1,3,117,-1,4. Three DSP issues replace five scalar issues in this toy. Fixed full-domain packing also uses three here, so this example illustrates mechanics rather than a universal fixed-packing win.',
 'The lower membrane receives a256 bias and occupies nine low multiplicand bits. The upper signed membrane begins at bit16, leaving seven zeros between them. This fits the25-bit DSP input. The offset C removes the bias after multiplication and supplies both ceiling offsets. A signed borrow can cross the product boundary.',
 'The lower term x can be negative, but its bounded range permits at most one negative borrow. The upper field then equals y minus that borrow. The known odd/even bit of y recovers the borrow with an XOR. This enables a small rounded-result correction instead of general spill reconstruction.',
 'For membranes -3 and5 with beta128, x=-129 and y=895. The lower quotient byte255 becomes -1 when the borrow correction subtracts256. The upper field894 still has quotient3. The independent integer ceilings agree with both results.',
 'The pair (-256,1) with beta1 exercises the upper correction boundary. A borrow changes upper field256 to255, so restoring it increases the upper quotient from0 to1. Separately,381 with beta78 lies outside signed9. E5 computes117 in a wide singleton. Unsafe narrowing would produce -39.',
 'The measured core includes range tests, coefficient equality, operand selection, the DSP, quotient correction and the elastic interface. Its source queue, operand memory and common zero filter remain external. Core latency is two advancing edges without stalls. Neither source integration nor complete-neuron latency has been measured.',
 'All general controls compute the same signed16 leakage contract. E1 retains full-domain pairs using DSP residue products and fabric high parts. E3 uses two scalar DSPs, E4 one, and E7 uses general LUT arithmetic. E6 is legal only for half leakage. E9 supports the33 trained GLIF coefficient codes using shared add/sub logic. These are matched constructed primitives rather than reproduced FireFly accelerators.',
 'Exhaustive arithmetic checks cover every stated narrow pair and full-domain scalar/split case. Native RTL checks also verify consumption, ordering and held outputs under stalls. The added GLIF constant control passes all65536 signed16 values for each of its33 coefficients and the entire representative workload, both stalled and unstalled.',
 'GLIF uses a full10000-image conversion reference but64-image packed feedback. OTTT uses full10000-image packed feedback. The independent TinyImageNet model uses a predeclared64-image subset. Exact agreement refers to packed versus scalar integer states/spikes/logits. Floating-to-integer conversion changes some network predictions, and those changes are reported separately.',
 'Bars show core LUT counts at selected matched12ns routes. The common94 fixture FFs are excluded from these core resources. E5 and E1 both use one DSP. E3 uses two DSPs. E7 and E9 use zero DSPs. E9 is one shared implementation covering all trained GLIF coefficient codes, not a lower bound for every possible constant design.',
 `Bars show representative GLIF fixture dynamic energy per scalar operand. Every compared engine receives the same declared operands. E5 uses 21.599 pJ, E1 fixed split 55.308 pJ, one-DSP scalar 24.648 pJ, two-DSP scalar 21.371 pJ and general LUT 124.198 pJ. ${mcm===null?'E9 has no accepted value.':`The independently audited GLIF constant control uses ${mcm.toFixed(3)} pJ.`} Energy excludes chip static power, operand memory and whole-neuron integration.`,
 'These values show E5 extra leakage issues relative to fixed E1. GLIF small membranes allow nearly full pair occupancy, whereas the wider OTTT and TinyImageNet streams cause many singletons. Leakage issue counts do not establish complete-network runtime or burst latency.',
 'Half leakage has a cheap exact shift control. It beats E5 on OTTT energy. The TinyImageNet coefficient253 also has an exact shift/add identity, although its hardware and energy remain unmeasured. This bounds the useful conditions for a general DSP primitive.',
 'Operation packing, actual-value narrowness detection and signed correction have established ancestry. The specific contribution is the compact exact rounded-leakage decoder integrated with actual-membrane admission and a wide singleton contract. The available review has not identified an equivalent implementation, but three original full methods remain unavailable. A worldwide first-ever claim is not established.',
 'The evidence supports preparation of a focused circuit submission. The paper should report exactness, measured resources, conditional energy benefits and negative cases. It should avoid claims about a complete accelerator, board energy, improved accuracy or universal burst latency. Reviewers determine the significance of the contribution and acceptance.',
 'The public repository packages the paper, slides, executable examples, research-authored source archive, lightweight evidence receipts and user-facing conversation export. Large weights, datasets and vendor artifacts remain external. The reading guide helps the mentor assess the final mechanism without following every discarded experiment.'
];
for(let i=0;i<20;i++){
 const original=notes[i].note;const pos=original.indexOf('Source');let sources=pos>=0?original.slice(pos):'Source: current manuscript and release evidence index.';
 for(const [a,b]of [['acceptedclosure','accepted closure'],['exactconstantcheck','exact constant check'],['relatedwork','related work'],['readinessreview','readiness review'],['currentpaperandreadinessreport','current paper and readiness report'],['fresh audit when present','independent_readiness_full_a0.json']])sources=sources.replaceAll(a,b);
 notes[i].note=polish(explanations[i])+'\n\n'+sources;
 p.slides.items[i].speakerNotes.text=notes[i].note;
}
await fs.mkdir(OUT,{recursive:true});
await fs.writeFile(path.join(OUT,'slide-notes.md'),'# Mentor briefing slide notes\n\n'+notes.map((x,i)=>`## ${i+1}. ${x.title}\n\n${x.note}\n`).join('\n'));
const candidate=path.join(BUILD,'candidate.pptx');
await(await PresentationFile.exportPptx(p)).save(candidate);
const final=path.join(OUT,'mentor_briefing_v4.pptx');
await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:final,
 pythonExecutable:'C:/Users/Ritesh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...[4,5,8,11,13,22].flatMap(n=>['--require-native-table-slide',String(n)])],
 requiredNativeTableOwnerSlides:[4,5,8,11,13,22],requiredNativeChartOwnerSlides:[14,15,16,17],
 materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,
 receiptPath:path.join(BUILD,'validation_v4.json')});
await fs.mkdir(path.join(BUILD,'rendered'),{recursive:true});
for(const [i,s]of p.slides.items.entries()){
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(BUILD,'rendered',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const montage=await p.export({format:'webp',montage:true});
await fs.writeFile(path.join(BUILD,'montage.webp'),new Uint8Array(await montage.arrayBuffer()));
console.log(JSON.stringify({status:'exported',slides:p.slides.items.length,font:FONT,accepted_MCM_energy:mcm,final},null,2));
