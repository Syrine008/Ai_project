"""Parse pickle opcodes into inert data; never import or call saved globals."""
import pickletools
from pathlib import Path
class Node:
 def __init__(self,kind,target=None,args=None):
  self.kind,self.target,self.args,self.state=kind,target,args,None
  self.items={};self.sequence=[]
 def __repr__(self):return f'Node({self.kind}, {self.target if isinstance(self.target,(str,tuple)) else type(self.target).__name__})'
def parse(path):
 stack=[];memo={};MARK=object()
 def popmark():
  index=next(i for i in range(len(stack)-1,-1,-1) if stack[i] is MARK)
  result=stack[index+1:];del stack[index:];return result
 def mapping(obj):return obj.items if isinstance(obj,Node) else obj
 with Path(path).open('rb') as f:
  for op,arg,pos in pickletools.genops(f):
   n=op.name
   if n in ('PROTO','FRAME'):continue
   if n in ('SHORT_BINUNICODE','BINUNICODE','BINUNICODE8','SHORT_BINBYTES','BINBYTES','BINBYTES8','BININT','BININT1','BININT2','LONG1','LONG4','BINFLOAT','INT','FLOAT','UNICODE','STRING'):stack.append(arg)
   elif n=='NONE':stack.append(None)
   elif n=='NEWTRUE':stack.append(True)
   elif n=='NEWFALSE':stack.append(False)
   elif n=='MARK':stack.append(MARK)
   elif n=='EMPTY_DICT':stack.append({})
   elif n=='EMPTY_LIST':stack.append([])
   elif n=='EMPTY_TUPLE':stack.append(())
   elif n=='EMPTY_SET':stack.append(set())
   elif n=='MEMOIZE':memo[len(memo)]=stack[-1]
   elif n in ('BINGET','LONG_BINGET','GET'):stack.append(memo[int(arg)])
   elif n in ('BINPUT','LONG_BINPUT','PUT'):memo[int(arg)]=stack[-1]
   elif n=='GLOBAL':stack.append(Node('global',tuple(arg.split(' '))))
   elif n=='STACK_GLOBAL':
    name=stack.pop();module=stack.pop();stack.append(Node('global',(module,name)))
   elif n in ('REDUCE','NEWOBJ'):
    args=stack.pop();target=stack.pop();stack.append(Node(n,target,args))
   elif n=='BUILD':
    state=stack.pop();obj=stack[-1]
    if not isinstance(obj,Node):raise ValueError(('Unexpected BUILD',pos,type(obj)))
    obj.state=state
   elif n=='TUPLE':stack.append(tuple(popmark()))
   elif n in ('TUPLE1','TUPLE2','TUPLE3'):
    count=int(n[-1]);args=tuple(stack[-count:]);del stack[-count:];stack.append(args)
   elif n=='SETITEMS':
    pairs=popmark();obj=mapping(stack[-1]);obj.update(zip(pairs[::2],pairs[1::2]))
   elif n=='SETITEM':
    value=stack.pop();key=stack.pop();mapping(stack[-1])[key]=value
   elif n=='APPENDS':
    values=popmark();obj=stack[-1];(obj.sequence if isinstance(obj,Node) else obj).extend(values)
   elif n=='APPEND':
    value=stack.pop();obj=stack[-1];(obj.sequence if isinstance(obj,Node) else obj).append(value)
   elif n=='ADDITEMS':
    values=popmark();stack[-1].update(values)
   elif n=='POP':stack.pop()
   elif n=='STOP':return stack[-1]
   else:raise ValueError(('Unsupported opcode',n,pos))


def mapping(value):
 return value.items if isinstance(value, Node) else value

def tensor(value):
 """Decode only known tensor/storage reducers, never arbitrary Python globals."""
 import io
 import torch
 if not isinstance(value,Node) or not isinstance(value.target,Node):
  raise ValueError("Expected an inert tensor reducer")
 target=value.target.target
 if target == ('torch._utils','_rebuild_parameter'):
  return tensor(value.args[0])
 if target != ('torch._utils','_rebuild_tensor_v2'):
  raise ValueError(f"Unsupported tensor reducer: {target}")
 storage,offset,shape,stride,*_=value.args
 if storage.target.target != ('torch.storage','_load_from_bytes'):
  raise ValueError("Unsupported storage reducer")
 raw=torch.load(io.BytesIO(storage.args[0]),map_location='cpu',weights_only=True)
 return torch.empty(0,dtype=raw.dtype).set_(raw,offset,shape,stride).clone()

def model_state(model):
 result={}
 def visit(module,prefix=''):
  for group in ('_parameters','_buffers'):
   for name,value in mapping(module.state.get(group,{})).items():
    if value is not None:result[prefix+name]=tensor(value)
  for name,child in mapping(module.state.get('_modules',{})).items():
   visit(child,prefix+name+'.')
 visit(model)
 return result

def ndarray(node):
 """Decode the numeric ndarray state preserved by dill, without unpickling."""
 import numpy as np
 state=node.args[2] if node.state is None else node.state
 version,shape,dtype,fortran,data=state
 if version!=1 or dtype.target.target != ('numpy','dtype'):
  raise ValueError('Unexpected ndarray encoding')
 dt=np.dtype(dtype.args[0]).newbyteorder(dtype.state[1])
 if dt.kind not in 'fiu' or len(data)!=int(np.prod(shape))*dt.itemsize:
  raise ValueError('Expected bounded numeric ndarray data')
 return np.frombuffer(data,dtype=dt).reshape(shape,order='F' if fortran else 'C').copy()
