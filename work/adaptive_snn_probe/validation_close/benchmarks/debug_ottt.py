from run_ottt import *
torch.set_num_threads(2);torch.set_num_interop_threads(1)
cp=torch.load(P/'cifar10_ottta.pth',map_location='cpu',weights_only=True)
i=model(IntegerLIF).eval();p=model(IntegerLIF).eval()
for net in (i,p):net.load_state_dict(cp['net'])
for nd in p.modules():
    if isinstance(nd,IntegerLIF):nd.packed=True
print('params_equal',all(torch.equal(x,y) for x,y in zip(i.parameters(),p.parameters())),flush=True)
d=np.load(P.parents[1]/'public_model_trial'/'full_test10000.npz')
x=torch.from_numpy(d['images'][:1].copy()).permute(0,3,1,2).float()/255
x=(x-torch.tensor([.4914,.4822,.4465])[None,:,None,None])/torch.tensor([.2023,.1994,.2010])[None,:,None,None]
with torch.inference_mode():
    for t in range(6):
        a=i(x,init=t==0);b=p(x,init=t==0)
        print('t',t,'logits',float((a-b).abs().max()),flush=True)
        for (name,ni),(pn,np_) in zip([(n,m) for n,m in i.named_modules() if isinstance(m,IntegerLIF)],[(n,m) for n,m in p.named_modules() if isinstance(m,IntegerLIF)]):
            mask=ni.integer_u!=np_.integer_u
            if mask.any():
                pos=mask.nonzero()[:5]
                print(name,'mismatch',int(mask.sum()),'examples',[(v.tolist(),int(ni.integer_u[tuple(v)]),int(np_.integer_u[tuple(v)])) for v in pos],flush=True)
