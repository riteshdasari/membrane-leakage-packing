from pathlib import Path
import re,sys
sys.dont_write_bytecode=True
p=Path(__file__).resolve().parents[3]/'outputs/membrane_leakage_paper_draft.tex'
s=p.read_text()
# Restrict edits to ordinary prose prefixes, retaining identifiers E5/Q8/signed16.
prefixes='achieves|versus|with|All|all|over|on|full|Full|seed|common|Common|adding|of|by|at|and|from|for|is|are|fall|falls|increases|increase|reduces|reduce|below|than|requires|contains|produces|saves|uses|has|given|about|its|complete|exactly|in|a|combined|totaling|energy|predeclared|consumes|FFs'
s=re.sub(r'\b('+prefixes+r')(?=\d)',r'\1 ',s)
s=re.sub(r'(?<=[A-Za-z]),(?=\d)',', ',s)
s=re.sub(r'(\d)(LUT|FF|ns)\b',r'\1~\2',s)
s=s.replace("E5's62","E5's 62").replace("E8's47","E8's 47").replace('oneDSP','one DSP').replace('versus$','versus $')
for a,b in [('Vivado2025.2','Vivado 2025.2'),('FPL2022','FPL 2022'),('FPGA2026','FPGA 2026'),('ICFPT2024','ICFPT 2024'),('SIPS2008','SIPS 2008'),('Aug.2023','Aug. 2023')]:s=s.replace(a,b)
p.write_text(s,encoding='utf-8',newline='\n')
print(p)
