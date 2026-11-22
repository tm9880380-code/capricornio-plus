let runtime;
async function start(){
  if(runtime)return runtime;
  importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js");
  runtime=await loadPyodide({indexURL:"https://cdn.jsdelivr.net/pyodide/v0.27.7/full/"});
  self.fetch=()=>Promise.reject(new Error("El acceso a internet está desactivado durante los ejercicios."));
  self.importScripts=()=>{throw new Error("No se permite cargar scripts externos desde los ejercicios.");};
  self.XMLHttpRequest=undefined;
  return runtime;
}
self.onmessage=async event=>{
  const {id,code}=event.data||{};
  try{
    const py=await start();
    await py.runPythonAsync(`
import sys
class _CapricornioLimitedWriter:
    def __init__(self, limit):
        self.limit = limit
        self.parts = []
        self.size = 0
        self.truncated = False
    def write(self, value):
        value = str(value)
        remaining = self.limit - self.size
        if remaining > 0:
            piece = value[:remaining]
            self.parts.append(piece)
            self.size += len(piece)
        if len(value) > remaining:
            self.truncated = True
        return len(value)
    def getvalue(self):
        result = "".join(self.parts)
        return result + ("\\n[Salida recortada por el límite de Capricornio.]" if self.truncated else "")
    def flush(self):
        return None
_cap_out = _CapricornioLimitedWriter(10000)
_cap_err = _CapricornioLimitedWriter(4000)
sys.stdout = _cap_out
sys.stderr = _cap_err
`);
    await py.runPythonAsync(code);
    const stdout=py.runPython("_cap_out.getvalue()");
    const stderr=py.runPython("_cap_err.getvalue()");
    self.postMessage({id,ok:true,stdout:String(stdout).slice(0,10000),stderr:String(stderr).slice(0,4000)});
  }catch(error){
    self.postMessage({id,ok:false,error:String(error)});
  }
};