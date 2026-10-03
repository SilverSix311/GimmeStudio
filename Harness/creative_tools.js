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

function shotDirection(shot){
 const d=structuredClone(shot.direction||{cues:[],references:[],checks:{},notes:''});
 modal('Direction · '+shot.name,`<p class="field wide">Plan timed beats and reference roles for review and export. These records do not automatically condition generation; use the visible ComfyUI guide workflow for that.</p><div class="field wide"><h3>Timed beats</h3><div id="direction-cues"></div><button type="button" id="cue-add">Add timed beat</button></div><div class="field wide"><h3>Reference roles</h3><div id="direction-refs"></div><button type="button" id="ref-add">Add reference</button></div>`+field('notes','Direction notes',d.notes,'textarea'),async v=>{
  await command('put',{kind:'shots',id:shot.id,value:{...shot,direction:{...d,notes:v.notes}}});
 });
 function cues(){
  $('#direction-cues').innerHTML=d.cues.map((c,i)=>`<div class="panel" data-cue="${i}">${field('cue-start-'+i,'Start (seconds)',c.start,'number','min="0" step="0.01"')}${field('cue-end-'+i,'End (seconds)',c.end,'number','min="0" step="0.01"')}${field('cue-text-'+i,'Action / camera / dialogue',c.text,'textarea')}<div class="actions"></div></div>`).join('');
  d.cues.forEach((c,i)=>{for(const k of ['start','end','text'])$(`[name=cue-${k}-${i}]`).oninput=e=>c[k]=k==='text'?e.target.value:Number(e.target.value);$(`[data-cue="${i}"] .actions`).append(button('Remove',()=>{d.cues.splice(i,1);cues();}));});
 }
 function refs(){
  $('#direction-refs').innerHTML=d.references.map((r,i)=>`<div class="panel" data-ref="${i}">${select('ref-role-'+i,'Role',options(['character','environment','motion','voice','guide'].map(id=>({id,name:id})),r.role,null))}${select('ref-asset-'+i,'Project asset',options(live('assets'),r.asset))}${field('ref-at-'+i,'Guide time (seconds)',r.at,'number','min="0" step="0.01"')}<div class="actions"></div></div>`).join('');
  d.references.forEach((r,i)=>{for(const k of ['role','asset','at'])$(`[name=ref-${k}-${i}]`).onchange=e=>r[k]=k==='at'?Number(e.target.value):e.target.value;$(`[data-ref="${i}"] .actions`).append(button('Remove',()=>{d.references.splice(i,1);refs();}));});
 }
 bind('#cue-add',()=>{d.cues.push({start:0,end:Number(shot.duration),text:''});cues();});
 bind('#ref-add',()=>{d.references.push({role:'character',asset:'',at:0});refs();});cues();refs();
}

function reviewTheatre(){
 const shots=live('shots'),videos=live('assets').filter(a=>a.kind==='video');
 $('#content').innerHTML=`<div class="panel"><span class="eyebrow">TAKES · TIMING · CONTINUITY</span><h2>Review theatre</h2><p>Compare local takes at the same time position. Shorter takes hold their last frame. Each video keeps its own framing; wipe comparisons work best with matching aspect ratios.</p><div class="form-grid">${select('review-shot','Shot',options(shots))}${select('review-a','Take A',options(videos))}${select('review-b','Take B',options(videos))}${select('review-mode','Layout','<option value="side">Side by side</option><option value="wipe">Wipe comparison</option>')}</div><div class="toolbar"><button id="review-play">Play both</button><button id="review-pause">Pause</button><button id="review-direction">Edit shot direction</button><button id="review-select">Use take A for this shot</button><button id="review-capture">Capture frame from A</button></div><div id="review-screen" class="review-screen"><div id="review-left"></div><div id="review-right"></div></div><label class="field" id="wipe-field" hidden>Wipe position<input id="review-wipe" type="range" min="0" max="100" value="50"></label><label class="field">Playhead<input id="review-seek" type="range" min="0" max="1" step="0.01" value="0"></label><output id="review-clock">0.00 s</output><label class="field">Audio<select id="review-audio"><option value="none">Muted</option><option value="a">Take A</option><option value="b">Take B</option></select></label></div><div class="columns"><div class="panel"><h3>Timed direction</h3><div id="review-cues"></div></div><div class="panel"><h3>Continuity review</h3><p>These checks are saved against take A. Saving checks does not approve assets.</p><div id="review-checks"></div><button id="review-save">Save review notes</button></div></div>`;
 const host=$('#review-screen');let playing=false,time=0,last=0,frame=0;
 const chosen=()=>find('shots',$('[name=review-shot]').value);
 const videoNodes=()=>[...host.querySelectorAll('video')];
 function limit(){return Math.max(0,...videoNodes().map(v=>Number.isFinite(v.duration)?v.duration:0));}
 function highlight(){
  $('#review-clock').textContent=time.toFixed(2)+' / '+limit().toFixed(2)+' s';
  $('#review-seek').value=time;$('#review-seek').max=Math.max(limit(),1);
  for(const el of $('#review-cues').children)el.classList.toggle('active-cue',time>=Number(el.dataset.start)&&time<Number(el.dataset.end));
 }
 function seek(t){time=t;for(const v of videoNodes())if(v.readyState){v.currentTime=Math.min(t,Math.max(0,v.duration-.001));}highlight();}
 function mute(){videoNodes().forEach((v,i)=>v.muted=$('#review-audio').value!==(i?'b':'a'));}
 function stop(){playing=false;videoNodes().forEach(v=>v.pause());}
 function tick(now){
  if(!host.isConnected){stop();cancelAnimationFrame(frame);return;}
  if(playing){time=Math.min(limit(),time+(now-last)/1000);for(const v of videoNodes())if(v.readyState&&Math.abs(v.currentTime-Math.min(time,v.duration))>.15)v.currentTime=Math.min(time,Math.max(0,v.duration-.001));if(time>=limit())stop();highlight();}
  last=now;frame=requestAnimationFrame(tick);
 }
 function loadMedia(){stop();time=0;for(const [side,key] of [['left','a'],['right','b']]){const a=find('assets',$(`[name=review-${key}]`).value);$('#review-'+side).innerHTML=a?media(a):'<p>Choose a video take</p>';}
  for(const v of videoNodes()){v.controls=false;v.onloadedmetadata=()=>seek(0);}mute();highlight();
 }
 function loadShot(){const s=chosen(),d=s?.direction||{};$('#review-cues').innerHTML=(d.cues||[]).map(c=>`<p data-start="${c.start}" data-end="${c.end}"><b>${c.start}–${c.end}s</b> ${esc(c.text)}</p>`).join('')||'<p>Add timed beats in Direction & cues.</p>';
  $('#review-checks').innerHTML=['identity','wardrobe','props','eyelines','motion','audio','seam'].map(k=>select('check-'+k,k,options(['unchecked','pass','issue'].map(id=>({id,name:id})),d.checks?.[k]||'unchecked',null))).join('')+field('review-notes','Notes',d.notes||'','textarea');highlight();
 }
 $('[name=review-shot]').onchange=loadShot;
 for(const k of ['a','b'])$(`[name=review-${k}]`).onchange=loadMedia;
 $('[name=review-mode]').onchange=()=>{host.classList.toggle('wipe',$('[name=review-mode]').value==='wipe');$('#wipe-field').hidden=$('[name=review-mode]').value!=='wipe';};
 $('#review-wipe').oninput=e=>host.style.setProperty('--wipe',e.target.value+'%');
 $('#review-seek').oninput=e=>{stop();seek(Number(e.target.value));};$('#review-audio').onchange=mute;
 bind('#review-play',async()=>{if(!limit())throw Error('Choose a playable video first');if(time>=limit())seek(0);await Promise.all(videoNodes().filter(v=>time<v.duration).map(v=>v.play()));playing=true;});bind('#review-pause',stop);
 bind('#review-direction',()=>{const s=chosen();if(!s)throw Error('Choose a shot');stop();shotDirection(s);});
 bind('#review-capture',async()=>{const a=find('assets',$('[name=review-a]').value);if(!a)throw Error('Choose take A');stop();await command('extract-frame',{asset:a.id,seconds:Math.min(time,Math.max(0,a.duration-1/24))},false);});
 bind('#review-select',async()=>{const s=chosen(),a=$('[name=review-a]').value;if(!s||!a)throw Error('Choose a shot and take A');stop();await command('put',{kind:'shots',id:s.id,value:{...s,selected:a}},false);});
 bind('#review-save',async()=>{const s=chosen();if(!s)throw Error('Choose a shot');stop();const checks=Object.fromEntries(['identity','wardrobe','props','eyelines','motion','audio','seam'].map(k=>[k,$(`[name=check-${k}]`).value]));await command('put',{kind:'shots',id:s.id,value:{...s,direction:{...s.direction,checks,reviewed_asset:$('[name=review-a]').value,notes:$('[name=review-notes]').value}}},false);});
 loadShot();loadMedia();frame=requestAnimationFrame(tick);
}
