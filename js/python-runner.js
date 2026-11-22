let runtime;
async function start(){
  if(runtime)return runtime;
  importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js");
  runtime=await loadPyodide({indexURL:"https://cdn.jsdelivr.net/pyodide/v0.27.7/full/"});
  return runtime;
}
self.onmessage=async event=>{
  const {id,code}=event.data||{};
  try{
    const py=await start();
    await py.runPythonAsync("import sys, io\n_cap_out=io.StringIO()\n_cap_err=io.StringIO()\nsys.stdout=_cap_out\nsys.stderr=_cap_err");
    await py.runPythonAsync(code);
    const stdout=py.runPython("_cap_out.getvalue()");
    const stderr=py.runPython("_cap_err.getvalue()");
    self.postMessage({id,ok:true,stdout:String(stdout),stderr:String(stderr)});
  }catch(error){
    self.postMessage({id,ok:false,error:String(error)});
  }
};