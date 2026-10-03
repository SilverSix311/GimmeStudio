'use strict';
async function loraPage(){
  const library=await api('/api/studio/loras');
  $('#content').innerHTML=`<div class="panel"><span class="eyebrow">MODELS · MOTION · IDENTITY</span><h2>LoRA library</h2><p>Manage previews, trigger words and reusable stacks in the installed ComfyUI LoRA Manager. Start ComfyUI using the header if it is stopped.</p><div class="toolbar"><a class="primary" href="http://127.0.0.1:8188/loras" target="_blank" rel="noopener">Open visual LoRA Manager ↗</a><a href="#cinema">Shot LoRA controls →</a><a href="#dataset">Training datasets →</a></div><p>Manager metadata and recipes are workspace-local. Shared SFW weights are reused in Incognito; moving or deleting a shared weight affects both workspaces.</p></div><div class="grid">${library.items.map(r=>`<article class="card"><span class="pill">${r.shared?'Shared SFW weight':'Workspace weight'}</span><h3>${esc(r.name)}</h3><p>${(r.bytes/1024**3).toFixed(2)} GB</p></article>`).join('')||'<p>Add compatible .safetensors files to Models/loras.</p>'}</div><div class="panel"><h2>Design recipes</h2><p>Start a reference sheet, expression study or material study with Krea 2. Review results before adding them to character canon or a training dataset. Choose Anima Turbo in the generation dialog for illustration studies. Reference sheets are generated drafts; review consistency before approving.</p><div id="design-recipes" class="toolbar"></div><h2>Motion studies</h2><p>H3 shots support first and last project-image keyframes. Keep each LoRA matched to its base-model family. The 360-orbit community recipe uses 28 steps and matching end frames; select its separate experimental recipe in the generation dialog. It replaces the turbo LoRA and uses silent output.</p><a href="https://huggingface.co/pablodawson/MiniMax-H3-360-Orbit-LoRA" target="_blank" rel="noopener">Orbit model and published settings ↗</a></div>`;
  for(const [label,prompt] of [['Character turnaround','Character reference sheet: front, three-quarter, side and back views of the same original character. Consistent proportions, outfit, colors and neutral studio lighting. Plain background.'],['Expression study','Expression sheet of the same original character: happy, uncertain, curious and determined. Preserve facial structure, hairstyle, clothing and colors. Plain background.'],['Prop study','Production design sheet of one original prop, front, side and three-quarter views. Consistent materials, colors and proportions. Plain studio background.']])
    $('#design-recipes').append(button(label,()=>generation({prompt})));
}

async function shotLoras(shot){
  const library=await api('/api/studio/loras');
  let stack=structuredClone(shot.loras||[]);
  const images=live('assets').filter(a=>a.kind==='image');
  modal('Shot LoRAs & keyframes',select('first_frame','First frame',options(images,shot.first_frame))+select('last_frame','Last frame (H3 only)',options(images,shot.last_frame))+`<div class="field wide"><p>Ordered model-only LoRA stack. Declare the family from its model card; filename alone cannot prove compatibility. The H3 turbo LoRA is already in its preset.</p><div id="lora-stack"></div><button type="button" id="append-lora">＋ Add LoRA</button></div>`,async v=>{
    await command('put',{kind:'shots',id:shot.id,value:{...shot,...v,loras:stack}});
  });
  function draw(){
    $('#lora-stack').innerHTML=stack.map((r,i)=>`<div class="panel" data-lora="${i}">${select('lname-'+i,'Installed file',`<option value="">Choose weight</option>`+library.items.map(a=>`<option value="${esc(a.name)}" ${r.name===a.name?'selected':''}>${esc(a.name)}</option>`).join(''))}${select('lfamily-'+i,'Base family',['krea2','minimax-h3','anima'].map(f=>`<option ${r.family===f?'selected':''}>${f}</option>`).join(''))}${field('lstrength-'+i,'Model strength',r.strength,'number','min="-2" max="2" step="0.05"')}<div class="actions"></div></div>`).join('');
    stack.forEach((r,i)=>{
      for(const [prefix,key] of [['lname','name'],['lfamily','family'],['lstrength','strength']])$(`[name=${prefix}-${i}]`).onchange=e=>r[key]=key==='strength'?Number(e.target.value):e.target.value;
      addButtons($(`[data-lora="${i}"] .actions`),[['↑',()=>{if(i)[stack[i-1],stack[i]]=[stack[i],stack[i-1]];draw();}],['Remove',()=>{stack.splice(i,1);draw();}]]);
    });
  }
  bind('#append-lora',()=>{if(stack.length>=8)throw Error('Maximum eight shot LoRAs');stack.push({name:'',family:'krea2',strength:1});draw();});draw();
}

function mountTimelineMonitor(clips){
  const host=$('#timeline-monitor');if(!host)return;
  host.innerHTML=`<div class="edit-monitor"><div id="edit-screen" aria-label="Timeline source monitor"></div><div><span class="eyebrow">ASSEMBLY MONITOR</span><h2 id="edit-name">No clips</h2><p>Scrub source frames and jump between clips. Transitions, grading and the soundtrack are applied in Render local preview.</p><output id="edit-time">0.00 s</output><input id="edit-scrub" aria-label="Timeline playhead" type="range" min="0" max="0" step="0.01" value="0"><div id="edit-ruler" class="toolbar"></div></div></div>`;
  let spans=[],end=0;
  const overlap=Number($('[name=transition_seconds]').value)||0;
  clips.forEach((c,i)=>{const duration=Math.max(0,Number(c.out)-Number(c.in));spans.push({start:end,end:end+duration,clip:c});end+=duration-(i<clips.length-1?overlap:0);});
  const total=Math.max(0,end),slider=$('#edit-scrub');slider.max=String(total);
  if($('#edit-total'))$('#edit-total').textContent=total.toFixed(2)+'s';
  let active=-1;
  function seek(time){
    const index=spans.findLastIndex(s=>s.start<=time);const span=spans[index];
    $('#edit-time').textContent=`${time.toFixed(2)} / ${total.toFixed(2)} s`;
    if(!span)return;
    const asset=find('assets',span.clip.asset);if(!asset)return;
    if(active!==index){active=index;$('#edit-screen').innerHTML=media(asset);$('#edit-name').textContent=`${index+1}. ${asset.name}`;}
    const video=$('#edit-screen video');
    if(video){const target=Math.min(Number(span.clip.out),Number(span.clip.in)+Math.max(0,time-span.start));video.pause();if(video.readyState)video.currentTime=target;else video.onloadedmetadata=()=>{video.currentTime=target;};}
  }
  slider.oninput=()=>seek(Number(slider.value));
  spans.forEach((s,i)=>$('#edit-ruler').append(button(`${i+1} · ${s.start.toFixed(1)}s`,()=>{slider.value=String(s.start);seek(s.start);})));seek(0);
}
