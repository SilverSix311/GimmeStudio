import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';

app.registerExtension({
  name: 'LocalStoryStudio.VisibleWorkflow',
  async setup() {
    const panel=document.createElement('div');
    Object.assign(panel.style,{position:'fixed',bottom:'18px',left:'24px',zIndex:'9999',background:'#192a31',color:'#edf1e9',padding:'12px',borderRadius:'10px',maxWidth:'380px',font:'13px sans-serif'});
    const button=document.createElement('button');button.textContent='Load studio shot';
    Object.assign(button.style,{background:'#e8bf77',color:'#17212a',padding:'9px',borderRadius:'6px',cursor:'pointer'});
    const status=document.createElement('div');status.style.marginTop='8px';status.textContent='Save your current canvas before loading. Run and edit here.';
    const followLabel=document.createElement('label');followLabel.style.display='block';followLabel.style.marginTop='8px';
    const follow=document.createElement('input');follow.type='checkbox';follow.checked=localStorage.getItem('studio.follow')==='true';
    follow.onchange=()=>localStorage.setItem('studio.follow',String(follow.checked));
    followLabel.append(follow,document.createTextNode(' Follow new studio workflows'));
    const progress=document.createElement('div');progress.style.marginTop='8px';let lastStage=null,loading=false;
    async function load(data){
      loading=true;
      try{const saved=await api.fetchApi('/local-story-studio/backup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(app.graph.serialize())});if(!saved.ok)throw Error('Could not back up the current canvas. Restart idle ComfyUI to load the updated studio bridge.');await app.loadGraphData(data.workflow,true,true,data.title);lastStage=data.stage_id;status.textContent=data.title+' â€” ready. Edit nodes, then use Run.';}
      finally{loading=false;}
    }
    button.onclick=async()=>{
      button.disabled=true;
      try {
        const response=await api.fetchApi('/local-story-studio/staged');
        const data=await response.json();if(!response.ok)throw Error(data.error);
        await load(data);
      } catch(error){status.textContent=error.message;}
      finally{button.disabled=false;}
    };
    panel.append(button,followLabel,status,progress);document.body.append(panel);
    setInterval(async()=>{
      try{
        if(follow.checked&&!loading){const r=await api.fetchApi('/local-story-studio/staged');if(r.ok){const data=await r.json();if(data.stage_id&&data.stage_id!==lastStage)await load(data);}}
        const r=await api.fetchApi('/local-story-studio/lab-progress');if(r.ok){const p=await r.json();progress.textContent=p.message||'';}
      }catch(error){progress.textContent='Studio bridge: '+error.message;}
    },2500);
  }
});
