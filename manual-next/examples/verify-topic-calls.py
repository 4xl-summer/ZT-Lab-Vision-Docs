"""Execute the displayed call fragments with independently constructed inputs."""
from pathlib import Path
from contextlib import ExitStack
import json, re, html, hashlib, math, datetime, traceback
import zvision as z

root=Path(__file__).resolve().parents[1]
pages=json.loads((root/'content/pages.json').read_text())
results=[]
for page in pages:
 name=page['path']; namespace={}; oracle=None
 if not name.startswith('reference/python/topics/'):continue
 with ExitStack() as stack:
  if 'depthmap-median-' in name:
   namespace['depth']=stack.enter_context(z.DepthMap.from_values(8,5,[2.0]*40,1.0,1.0,z.Point3(10,20,0),z.LengthUnit.MILLIMETER,1))
   oracle=lambda n: n['values']==[2.0]*40
  elif 'depthmap-roi-' in name:
   namespace['depth']=stack.enter_context(z.DepthMap.from_values(8,5,[2.0]*40,1.0,1.0,z.Point3(10,20,0),z.LengthUnit.MILLIMETER,1))
   oracle=lambda n: (n['info'].width,n['info'].height,n['info'].origin.x,n['info'].origin.y,n['values'])==(4,3,12.0,21.0,[2.0]*12)
  elif 'pointcloud-fit-plane-' in name:
   namespace['cloud']=stack.enter_context(z.PointCloud.from_points([z.Point3(x,y,3)for y in range(4)for x in range(4)],z.LengthUnit.MILLIMETER,1))
   oracle=lambda n: n['fit'].inliers==16 and n['fit'].total==16 and abs(abs(n['fit'].normal.z)-1)<1e-10 and abs(abs(n['fit'].offset)-3)<1e-10 and n['fit'].rms_error<1e-10
  elif 'zimage-ssim-' in name:
   namespace['sample']=stack.enter_context(z.ZImage.from_gray8(16,16,bytes([128])*256))
   namespace['reference']=stack.enter_context(z.ZImage.from_gray8(16,16,bytes([128])*256))
   namespace['options']=z.SsimOptions(1,z.SsimWindow.BOX,z.SsimBorder.REPLICATE,1.0,255.0,0.01,0.03,0.99,z.SsimPolarity.BOTH,1_000_000)
   oracle=lambda n: abs(n['score']-1)<1e-10 and n['defects']==0
  elif 'zimage-polar-unwrap-' in name:
   namespace['image']=stack.enter_context(z.ZImage.from_gray8(64,64,bytes([32])*4096))
   namespace['options']=z.PolarOptions(32,32,0,math.tau,1,20,32,16)
   oracle=lambda n: (n['output_info'].width,n['output_info'].height)==(32,16)
  elif 'zimage-polar-rewrap-' in name:
   namespace['options']=z.PolarOptions(32,32,0,math.tau,1,20,32,16)
   image=stack.enter_context(z.ZImage.from_gray8(64,64,bytes([32])*4096))
   namespace['polar']=stack.enter_context(image.polar_unwrap(namespace['options']))
   oracle=lambda n: (n['restored_info'].width,n['restored_info'].height)==(640,480)
  elif 'zimage-gaussian-with-care-mask-' in name:
   namespace['image']=stack.enter_context(z.ZImage.from_gray8(9,9,bytes([57])*81))
   namespace['mask']=stack.enter_context(z.ZImage.from_gray8(9,9,bytes([255])*81))
   namespace['options']=z.CareGaussianOptions(1,1,1.0,1.0)
   oracle=lambda n: (n['filtered_info'].width,n['filtered_info'].height,n['filtered_info'].pixel_format)==(9,9,z.PixelFormat.GRAYF32)
  elif 'zimage-convolve-grayf64-' in name:
   namespace['image']=stack.enter_context(z.ZImage.from_grayf64(3,3,list(range(1,10))))
   namespace['spec']=z.ConvolutionSpec(1,1,(0,0),[1.0],1.0,0.0,0,z.PixelFormat.GRAYF64,True)
   oracle=lambda n: (n['result_info'].width,n['result_info'].height,n['result_info'].pixel_format)==(3,3,z.PixelFormat.GRAYF64)
  else:continue
  # Declarations have no body; the documented executable fragment starts with with/fit.
  blocks=[html.unescape(m)for m in re.findall(r'<pre><code[^>]*>(.*?)</code></pre>',page['body'],re.S)]
  code=next(c for c in blocks if c.startswith(('with ','fit =')))
  row={'page':name,'decoded_code_sha256':hashlib.sha256(code.encode()).hexdigest(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
  try:
   exec(compile(code,name,'exec'),namespace)
   assert oracle(namespace),'independent expected result did not match'
   row['status']='pass'
  except Exception:
   row.update(status='fail',error=traceback.format_exc())
  results.append(row)
  print(name,row['status'],flush=True)
  if row['status']=='fail':print(row['error'],flush=True)
(Path.cwd()/'topic-call-results.json').write_text(json.dumps(results,indent=2))
assert len(results)==8
assert all(r['status']=='pass'for r in results)
