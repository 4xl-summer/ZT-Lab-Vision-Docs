from pathlib import Path
import json, math
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
font_manager.fontManager.addfont('/mnt/c/Windows/Fonts/malgun.ttf')
plt.rcParams['font.family'] = font_manager.FontProperties(fname='/mnt/c/Windows/Fonts/malgun.ttf').get_name()
plt.rcParams['axes.unicode_minus'] = False
from matplotlib.patches import Rectangle
import zvision as zv

ROOT=Path(__file__).resolve().parent
M=ROOT.parent/'assets/measurement'
OUT=ROOT.parent/'assets/visuals/plots'
OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':18,'axes.titlesize':18,'axes.labelsize':17,'xtick.labelsize':15,'ytick.labelsize':15,'figure.facecolor':'white','savefig.facecolor':'white'})
def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=160,bbox_inches='tight');plt.close(fig)
def im(ax,a,title):
    ax.imshow(a,cmap='gray',vmin=0,vmax=255,interpolation='nearest');ax.set_title(title);ax.set_axis_off()
camera=np.array(Image.open(M/'input/camera.png').convert('L'))
measure=json.loads((M/'measurements.json').read_text(encoding='utf8'))
profile=next(x for x in measure['cases'] if x['id']=='camera-profile')
edge=next(x['value'] for x in profile['metrics'] if x['label']=='에지 x')
y=next(x['value'] for x in profile['parameters'] if x['name']=='row')
# Recheck SDK profile, as the plotted values must come directly from SDK.
h,w=camera.shape
with zv.ZImage.from_gray8(w,h,camera.tobytes()) as image:
    ps=zv.ProfileSpec(zv.Point2(0.,float(y)),zv.Point2(float(w-1),float(y)),w,1)
    values=np.array([s.value for s in image.profile(ps).samples])
    assert np.allclose(values,camera[y,:],atol=1e-9)
    for low,high in [(30.,80.),(80.,160.)]:
        with image.canny(5,1.,low,high) as out:
            out.save(str(OUT/f'canny-{int(low)}-{int(high)}.png'))
# Histogram: explicit edge inclusion: synthetic values in [0,4).
v=np.array([0,0,1,3]); counts,edges=np.histogram(v,bins=np.arange(5));assert counts.tolist()==[2,1,0,1]
fig,ax=plt.subplots(layout='constrained',figsize=(8,4));ax.bar(edges[:-1],counts,width=1,align='edge',edgecolor='white',color='#2264a5');ax.set_xticks([.5,1.5,2.5,3.5],['[0,1)','[1,2)','[2,3)','[3,4]']);ax.set_yticks([0,1,2]);ax.set(xlim=(0,4),ylim=(0,2.5),xlabel='밝기 구간',ylabel='빈도 (표본 수)',title='합성 표본: 0, 0, 1, 3')
for i,n in enumerate(counts):ax.text(i+.5,n+.08,str(n),ha='center')
save(fig,'histogram-bins')
# Explicit Gaussian 3x3 sigma=1 normalized kernel, centered impulse 1, no border involved.
a=np.arange(-1,2);k=np.exp(-(a[:,None]**2+a[None,:]**2)/2);k/=k.sum(); assert np.isclose(k.sum(),1)
fig,axs=plt.subplots(1,2,layout='constrained',figsize=(8.5,4));imp=np.zeros((3,3));imp[1,1]=1
for ax,data,title in zip(axs,[imp,k],['입력: 중앙 임펄스','출력 = 정규화 커널']):
    ax.imshow(data,cmap='Blues',vmin=0,vmax=1 if ax is axs[0] else k.max());ax.set_title(title);ax.set_xticks([]);ax.set_yticks([])
    for (r,c),val in np.ndenumerate(data):ax.text(c,r,f'{val:.3f}',ha='center',va='center',color='white' if val>.7*data.max() else 'black',fontsize=16)
fig.suptitle('설명용 3×3 가우시안, σ = 1; 가중치 합 = 1',fontsize=18);save(fig,'gaussian-filter')
# Canny actual photo + actual SDK masks.
c1=np.array(Image.open(OUT/'canny-30-80.png').convert('L'));c2=np.array(Image.open(OUT/'canny-80-160.png').convert('L'))
fig,axs=plt.subplots(1,3,layout='constrained',figsize=(11,4));im(axs[0],camera,'공개 camera 사진');im(axs[1],c1,f'SDK 낮은값 30 / 높은값 80\n{np.count_nonzero(c1):,} 경계 픽셀');im(axs[2],c2,f'SDK 낮은값 80 / 높은값 160\n{np.count_nonzero(c2):,} 경계 픽셀');fig.suptitle('Canny: 커널 5, σ = 1 (Gray8)',fontsize=18);save(fig,'canny-edges')
# Mathematical NCC: valid placement, explicit nonconstant patch and seeded background.
rng=np.random.default_rng(17);image=rng.normal(0,.3,(12,16));pattern=np.array([[0,1,0],[1,3,1],[0,1,0]],float);image[5:8,9:12]=pattern
p=pattern-pattern.mean();score=np.empty((10,14))
for yy in range(score.shape[0]):
    for xx in range(score.shape[1]):
        q=image[yy:yy+3,xx:xx+3];q=q-q.mean();score[yy,xx]=(p*q).sum()/np.sqrt((p*p).sum()*(q*q).sum())
best=np.unravel_index(score.argmax(),score.shape);assert best==(5,9) and np.isclose(score[best],1)
fig,axs=plt.subplots(1,3,layout='constrained',figsize=(11,3.8));axs[0].imshow(pattern,cmap='gray');axs[0].set_title('모델 3×3');axs[1].imshow(image,cmap='gray');axs[1].add_patch(Rectangle((8.5,4.5),3,3,fill=False,color='red',linewidth=2));axs[1].set_title('검색: 좌상단 (9, 5)');im3=axs[2].imshow(score,vmin=-1,vmax=1,cmap='coolwarm');axs[2].plot(9,5,'kx',ms=10,mew=2);axs[2].set_title('NCC 최고점 1.00');fig.colorbar(im3,ax=axs[2],shrink=.7);fig.suptitle('정규화 상관의 합성 예 (SDK 결과 아님)',fontsize=18);save(fig,'ncc-matching')
# Lab difference lies in the delta-b=0 plane: a 2D right triangle is sufficient.
fig,ax=plt.subplots(figsize=(8,5),layout='constrained');ax.plot([0,3],[0,4],color='#733b8c',linewidth=3,label='ΔE76 = 5');ax.plot([0,3,3],[0,0,4],ls='--',color='#52718e',linewidth=2);ax.scatter([0,3],[0,4],s=70,color=['#2465ac','#d94332'],zorder=3);ax.annotate('A: (0, 0)',(0,0),xytext=(10,14),textcoords='offset points');ax.annotate('B: (3, 4)',(3,4),xytext=(-110,10),textcoords='offset points');ax.text(1.5,-.35,'ΔL* = 3',ha='center');ax.text(3.15,2,'Δa* = 4',va='center');ax.set(xlabel='ΔL*',ylabel='Δa*',xlim=(-.5,4.2),ylim=(-.7,4.7),title='Lab 차이 벡터: Δb* = 0인 합성 예');ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.2);ax.text(.1,3.6,'ΔE76 = 5',color='#733b8c');save(fig,'lab-distance')
# Fourier demonstration is NumPy mathematics; spectrum shown shifted for readability.
x=np.arange(64);stripe=np.tile(np.cos(2*np.pi*8*x/64),(64,1));freq=np.fft.fft2(stripe);back=np.fft.ifft2(freq).real;error=float(np.max(np.abs(back-stripe)));assert error<1e-12
fig,axs=plt.subplots(1,3,layout='constrained',figsize=(10.5,3.7));axs[0].imshow(stripe,cmap='gray');axs[0].set_title('입력: 가로 8주기');bins=np.arange(-32,32);section=np.abs(np.fft.fftshift(freq[0,:]))/(64*64);assert np.isclose(section[bins==-8][0],.5) and np.isclose(section[bins==8][0],.5);axs[1].stem(bins,section,basefmt=' ');axs[1].set(xlabel='가로 주파수 bin kx',ylabel='|F(kx, 0)| / 64²',title='세로 주파수 ky = 0',xlim=(-32,31));axs[1].set_xticks([-32,-8,0,8,31]);axs[1].set_yticks([0,.5]);axs[2].imshow(back,cmap='gray');axs[2].set_title(f'역변환, 최대 오차\n{error:.2g}');
axs[0].set_axis_off();axs[2].set_axis_off()
fig.suptitle('2D 줄무늬의 FFT 단면과 역변환: 합성 예',fontsize=18);save(fig,'frequency-roundtrip')
# Directly reuse the verified actual SDK controlled-difference images.
modified=np.array(Image.open(M/'stage/camera-controlled-modification.png').convert('L'));mask=np.array(Image.open(M/'stage/camera-difference-mask.png').convert('L'));assert np.count_nonzero(mask)==384
fig,axs=plt.subplots(1,3,layout='constrained',figsize=(11,4));im(axs[0],camera,'기준 사진');im(axs[1],modified,'인위적 변경 24×16');axs[1].add_patch(Rectangle((219.5,179.5),24,16,fill=False,color='red',linewidth=2));im(axs[2],mask,'SDK 차분 마스크: 384 px');fig.suptitle('512×512 전체 검사, 임계값 32',fontsize=18);save(fig,'difference-inspection')
# Show the exact SDK samples alongside their sampling line.
fig,axs=plt.subplots(1,2,layout='constrained',figsize=(10.8,4));im(axs[0],camera,'camera 사진: 표본 선');axs[0].axhline(y,color='#edbc22',lw=2);axs[0].plot(edge,y,'rx',ms=9,mew=2);axs[1].plot(np.arange(w),values,color='#245ea8',lw=1);axs[1].axvline(edge,color='#c33',ls='--',label=f'SDK 에지 x={edge:.2f} px');axs[1].set(xlabel='x (px)',ylabel='Gray8 강도',xlim=(0,w-1),ylim=(0,255),title=f'SDK 512 표본 · 에지 x={edge:.2f} px');axs[1].grid(alpha=.2);save(fig,'caliper-profile')
print(json.dumps({'canny_nonzero':[int(np.count_nonzero(c1)),int(np.count_nonzero(c2))],'ncc_peak_xy':[9,5],'fft_max_error':error,'difference_pixels':int(np.count_nonzero(mask)),'profile_edge_x':edge}))
