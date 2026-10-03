"""Short-lived, offline GPU worker; isolated dependencies never alter ComfyUI."""
import json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Tools/advanced-python'))
sys.path.insert(0,str(ROOT/'Tools/sources/MuseTalk'))
action=sys.argv[1];source=Path(sys.argv[2]);folder=source.parent
data=json.loads(source.read_text(encoding='utf-8'))
import torch
import numpy as np
import soundfile as sf
import imageio_ffmpeg

if action=='speak':
 from qwen_tts import Qwen3TTSModel
 voice=data['voice'];torch.manual_seed(voice['seed'])
 model=Qwen3TTSModel.from_pretrained(str(ROOT/'Models/voices/qwen3-custom'),device_map='cuda:0',dtype=torch.bfloat16,attn_implementation='sdpa')
 waves,rate=model.generate_custom_voice(text=data['text'],language=voice['language'],speaker=voice['speaker'],instruct=voice['instruct'],max_new_tokens=2048)
 output=folder/'voice.wav';sf.write(output,waves[0],rate)
 result=dict(file=str(output),text=data['text'],voice=voice,sample_rate=rate,duration=len(waves[0])/rate)
elif action=='lipsync':
 import cv2
 from transformers import WhisperModel
 from musetalk.models.vae import VAE
 from musetalk.models.unet import UNet,PositionalEncoding
 from musetalk.utils.audio_processor import AudioProcessor
 torch.manual_seed(42)
 base=ROOT/'Models/lipsync';device=torch.device('cuda:0');dtype=torch.float16
 audio=folder/'speech.wav'
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-i',data['audio'],'-vn','-ar','16000','-ac','1',str(audio)],check=True)
 frame=cv2.imread(data['image']);h,w=frame.shape[:2]
 x0,y0,x1,y1=[round(v*s) for v,s in zip(data['box'],[w,h,w,h])]
 if x1-x0<32 or y1-y0<32:raise ValueError('Face rectangle must be at least 32 pixels wide and high')
 vae=VAE(model_path=str(base/'sd-vae'),use_float16=True);vae.vae.to(device)
 unet=UNet(unet_config=str(base/'musetalkV15/musetalk.json'),model_path=str(base/'musetalkV15/unet.pth'),use_float16=True,device=device)
 pe=PositionalEncoding(d_model=384).to(device,dtype)
 whisper=WhisperModel.from_pretrained(str(base/'whisper')).to(device,dtype).eval()
 processor=AudioProcessor(str(base/'whisper'))
 with torch.inference_mode():
  samples,rate=sf.read(audio,dtype='float32');length=len(samples)
  features=[processor.feature_extractor(samples,return_tensors='pt',sampling_rate=rate).input_features.to(dtype)]
  chunks=processor.get_whisper_chunk(features,device,dtype,whisper,length,fps=25)
  crop=cv2.resize(frame[y0:y1,x0:x1],(256,256))
  latent=vae.get_latents_for_unet(crop).to(device,dtype)
  frames=folder/'frames';frames.mkdir(exist_ok=True)
  # Limit blending to the mouth/chin; preserve the source eyes and glasses.
  mask=np.zeros((256,256),np.float32);cv2.ellipse(mask,(128,206),(90,42),0,0,360,1,-1);mask=cv2.GaussianBlur(mask,(21,21),0)
  mask=cv2.resize(mask,(x1-x0,y1-y0))[...,None]
  for start in range(0,len(chunks),4):
   batch=chunks[start:start+4].to(device,dtype)
   prediction=unet.model(latent.repeat(len(batch),1,1,1),torch.tensor([0],device=device),encoder_hidden_states=pe(batch)).sample
   decoded=vae.decode_latents(prediction)
   for offset,face in enumerate(decoded):
    output_frame=frame.copy();face=cv2.resize(face,(x1-x0,y1-y0))
    output_frame[y0:y1,x0:x1]=(face*mask+frame[y0:y1,x0:x1]*(1-mask)).astype(np.uint8)
    cv2.imwrite(str(frames/f'{start+offset:06d}.png'),output_frame)
   print(f'Frames {min(start+4,len(chunks))}/{len(chunks)}',flush=True)
 output=folder/'lipsync.mp4'
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-framerate','25','-i',str(frames/'%06d.png'),'-i',str(audio),'-c:v','libx264','-pix_fmt','yuv420p','-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:a','aac','-shortest',str(output)],check=True)
 result=dict(file=str(output),frames=len(chunks),fps=25,mode='Still portrait with manually selected face region; review identity and articulation')
else:raise ValueError('Unknown media worker')
(folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
