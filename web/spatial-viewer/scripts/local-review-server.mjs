import {createReadStream} from 'node:fs';
import {stat} from 'node:fs/promises';
import path from 'node:path';

export function localReviewServer(projectRoot,directory='data/local/web-exports/data221-af7335da'){
  const allowed=path.resolve(projectRoot,'data/local'),root=path.resolve(projectRoot,directory);
  if(!root.startsWith(allowed+path.sep))throw new Error('Local building output must be inside data/local/.');
  const files=new Map([
    ['/__otw_local__/data221-af7335da/manifest.json',['manifest.json','application/json',512*1024]],
    ['/__otw_local__/data221-af7335da/model.glb',['model.glb','model/gltf-binary',5*1024*1024]],
  ]);
  return {name:'otw-local-building-review',apply:'serve',configureServer(server){
    server.middlewares.use(async(request,response,next)=>{
      const pathname=new URL(request.url,'http://localhost').pathname;
      if(!pathname.startsWith('/__otw_local__/'))return next();
      const remote=request.socket.remoteAddress;
      if(!['127.0.0.1','::1','::ffff:127.0.0.1'].includes(remote)){response.writeHead(403).end();return;}
      const file=files.get(pathname);
      if(!file){response.writeHead(404).end();return;}
      if(!['GET','HEAD'].includes(request.method)){response.writeHead(405).end();return;}
      try{
        const destination=path.join(root,file[0]),info=await stat(destination);
        if(!info.isFile()||info.size>file[2]){response.writeHead(413).end();return;}
        response.writeHead(200,{'Content-Type':file[1],'Content-Length':info.size,'Cache-Control':'no-store'});
        if(request.method==='HEAD'){response.end();return;}
        createReadStream(destination).on('error',()=>response.destroy()).pipe(response);
      }catch{response.writeHead(404).end();}
    });
  }};
}
