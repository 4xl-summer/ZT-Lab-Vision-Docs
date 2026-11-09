#!/usr/bin/env python3
"""Generate measurement schema v1 from public photographs and real ZVision results.

Run from the root-managed SDK runtime, not from a product checkout. All output is
written below --output. No network or SDK build is performed by this program.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import ndimage
from skimage import data

import zvision as zv

SDK_REVISION = 'ce902e85c3405eb63df40c699ddbdf70ee1d03bd'
SOURCE_BASE = 'https://scikit-image.org/docs/stable/api/skimage.data#skimage.data.'
SOURCES = {
    'coins': {'label':'scikit-image coins — Brooklyn Museum collection', 'url':SOURCE_BASE+'coins',
              'license':'no known copyright restrictions', 'author':'Brooklyn Museum'},
    'camera': {'label':'scikit-image camera — cameraman', 'url':SOURCE_BASE+'camera',
               'license':'CC0', 'author':'Lav Varshney'},
    'text': {'label':'scikit-image text — Wikipedia Corner.png', 'url':SOURCE_BASE+'text',
             'license':'public domain / no known restrictions', 'author':'Wikipedia Corner.png contributors'},
    'coffee': {'label':'scikit-image coffee', 'url':SOURCE_BASE+'coffee',
               'license':'CC0', 'author':'Rachel Michetti'},
}
WARNINGS = [
    '공개 예제 사진을 입력으로 사용한 재현 예시입니다. 사용자 생산 영상이 아닙니다.',
    '길이와 면적은 픽셀 및 픽셀 제곱입니다. 실제 치수·장비 정확도·생산 합격 판정이 아닙니다.',
]

def save_photo(root: Path, name: str, arr: np.ndarray) -> str:
    rel = f'input/{name}.png'
    Image.fromarray(np.ascontiguousarray(arr)).save(root / rel)
    return rel

def gray_image(arr: np.ndarray):
    arr = np.ascontiguousarray(arr, dtype=np.uint8)
    return zv.ZImage.from_gray8(arr.shape[1], arr.shape[0], arr.tobytes())

def rgb_image(arr: np.ndarray):
    arr = np.ascontiguousarray(arr, dtype=np.uint8)
    return zv.ZImage.from_rgb8(arr.shape[1], arr.shape[0], arr.tobytes())

def sdk_mask_png(image, root: Path, rel: str) -> np.ndarray:
    """Use public SDK save API to read back an SDK-produced Gray8 PNG."""
    image.save(str((root / rel).resolve()))
    a = np.asarray(Image.open(root / rel).convert('L'), dtype=np.uint8)
    return a

def geometry(**kwargs):
    result = {key: [] for key in ('circles','lines','boxes','points')}
    result.update(kwargs)
    return result

def metric(label, value, unit, meaning):
    if isinstance(value, np.generic): value = value.item()
    return {'label':label,'value':value,'unit':unit,'meaning':meaning}

def step(label, api, description, image=None):
    v = {'label':label,'api':api,'description':description}
    if image is not None: v['image'] = image
    return v

def api(label, path): return {'label':label, 'path':path}

def case(case_id,title,description,category,source_name,image_rel,w,h,roi,steps,metrics,geo,params,links,checks):
    return {'id':case_id,'title':title,'description':description,'category':category,
            'source':SOURCES[source_name], 'image':{'original':image_rel,'width':int(w),'height':int(h)},
            'roi':roi,'steps':steps,'metrics':metrics,'geometry':geo,'parameters':params,
            'api_links':links,'status':'SDK 실행 결과 · 독립 계산 확인',
            'warnings':WARNINGS.copy(),'verification':checks}

def write_overlay(root, case_id, image, geo, roi):
    rgb = Image.fromarray(image).convert('RGB'); draw = ImageDraw.Draw(rgb)
    if roi:
        x,y,w,h = (roi[k] for k in ('x','y','width','height'))
        draw.rectangle((x,y,x+w-1,y+h-1), outline=(255,195,0), width=2)
    for box in geo.get('boxes',[]):
        x,y,w,h = (box[k] for k in ('x','y','width','height'))
        draw.rectangle((x,y,x+w-1,y+h-1), outline=(0,255,200), width=2)
    for circle in geo.get('circles',[]):
        x,y,r = circle['cx'],circle['cy'],circle['radius']
        draw.ellipse((x-r,y-r,x+r,y+r),outline=(255,70,60),width=2)
    for line in geo.get('lines',[]):
        draw.line((line['x1'],line['y1'],line['x2'],line['y2']),fill=(0,255,180),width=2)
    for point in geo.get('points',[]):
        x,y=point['x'],point['y'];draw.ellipse((x-3,y-3,x+3,y+3),fill=(255,65,30))
    rel=f'overlay/{case_id}.png';rgb.save(root/rel);return rel

def get_blobs(mask: np.ndarray):
    """Independent 8-connected pixel statistics in the same local frame."""
    labels,n = ndimage.label(mask, structure=np.ones((3,3),dtype=np.uint8))
    result=[]
    for label,sl in enumerate(ndimage.find_objects(labels),1):
        if sl is None: continue
        yy,xx=np.nonzero(labels[sl]==label)
        if not len(xx): continue
        y0,x0=sl[0].start,sl[1].start
        result.append({'label':label,'area':int(len(xx)), 'x':int(x0),'y':int(y0),
                       'width':int(sl[1].stop-x0),'height':int(sl[0].stop-y0),
                       'centroid_x':float(x0+xx.mean()),'centroid_y':float(y0+yy.mean())})
    return labels,result

def verify_sdk_blobs(sdk, expected):
    key=lambda b:(int(b.area),int(b.x),int(b.y),int(b.width),int(b.height))
    truth=lambda b:(b['area'],b['x'],b['y'],b['width'],b['height'])
    actual={key(b):b for b in sdk}; exp={truth(b):b for b in expected}
    assert len(actual)==len(sdk) and len(exp)==len(expected) and actual.keys()==exp.keys(), 'blob component geometry mismatch'
    for k,b in actual.items():
        e=exp[k]
        assert math.isclose(b.centroid_x,e['centroid_x'],abs_tol=1e-9)
        assert math.isclose(b.centroid_y,e['centroid_y'],abs_tol=1e-9)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args();root=args.output.resolve();root.mkdir(parents=True,exist_ok=True)
    for folder in ('input','overlay','stage','plots'): (root/folder).mkdir(exist_ok=True)
    photos={'coins':np.asarray(data.coins()),'camera':np.asarray(data.camera()),
            'text':np.asarray(data.text()),'coffee':np.asarray(data.coffee())}
    assert all(a.dtype==np.uint8 for a in photos.values())
    assert photos['coffee'].ndim==3 and photos['coffee'].shape[2]==3
    paths={name:save_photo(root,name,image) for name,image in photos.items()}
    manifest={'sdk_revision':SDK_REVISION,'datasets':[]}
    for name,arr in photos.items():
        manifest['datasets'].append({'id':name,**SOURCES[name], 'file':paths[name],
            'shape':list(arr.shape),'sha256':hashlib.sha256((root/paths[name]).read_bytes()).hexdigest(),
            'origin':'skimage.data.'+name+'() — unmodified RGB/gray pixel array saved as PNG'})
    cases=[]

    # 1–2: threshold the public coin photo and verify every pixel and component.
    coins=photos['coins']; h,w=coins.shape; threshold=110
    independent=coins>=threshold
    labels, components=get_blobs(independent)
    with gray_image(coins) as image, image.threshold(float(threshold)) as mask:
        saved=sdk_mask_png(mask,root,'stage/coins-threshold.png')
        assert np.array_equal(saved,independent.astype(np.uint8)*255),'coin threshold mismatch'
        blobs=mask.find_blobs(8).blobs
    verify_sdk_blobs(blobs,components)
    # Choose an isolated roughly round component deterministically, based only on
    # the thresholded photograph, not on SDK-fitted values or a physical size.
    candidates=[b for b in components if 400<=b['area']<=5000 and
                0.65<=b['width']/b['height']<=1.45 and b['x']>0 and b['y']>0 and
                b['x']+b['width']<w and b['y']+b['height']<h]
    if not candidates: raise RuntimeError('No eligible isolated coin-like threshold component; inspect input/threshold')
    selected=max(candidates,key=lambda b:(b['area'],-b['y'],-b['x']))
    sdk_selected=next(b for b in blobs if (b.area,b.x,b.y,b.width,b.height)==
                      (selected['area'],selected['x'],selected['y'],selected['width'],selected['height']))
    x0=max(0,selected['x']-4);y0=max(0,selected['y']-4)
    x1=min(w,selected['x']+selected['width']+4);y1=min(h,selected['y']+selected['height']+4)
    roi={'x':x0,'y':y0,'width':x1-x0,'height':y1-y0}
    center={'x':float(sdk_selected.centroid_x),'y':float(sdk_selected.centroid_y),'label':'블롭 중심'}
    box={k:int(getattr(sdk_selected,k)) for k in ('x','y','width','height')};box['label']='연결 성분 경계'
    geo=geometry(boxes=[box],points=[center]);preview=write_overlay(root,'coins-blob',coins,geo,roi)
    cases.append(case('coins-blob','동전 사진의 연결 성분','실제 사진을 고정 문턱으로 이진화한 뒤 8연결 영역의 면적과 경계를 측정합니다.',
        'blob','coins',paths['coins'],w,h,roi,[step('원본','ZImage.from_gray8','공개 동전 사진을 Gray8로 입력합니다.',paths['coins']),
        step('이진화','ZImage.threshold','110 이상인 픽셀을 전경으로 만듭니다.','stage/coins-threshold.png'),
        step('연결 성분','ZImage.find_blobs(8)','후보 중 고립된 대략 원형 성분을 선택합니다.',preview)],
        [metric('면적',int(sdk_selected.area),'px²','선택된 연결 성분의 픽셀 수'),metric('중심 x',center['x'],'px','전체 영상 좌표'),metric('중심 y',center['y'],'px','전체 영상 좌표'),
         metric('경계 폭',box['width'],'px','축 정렬 경계 폭'),metric('경계 높이',box['height'],'px','축 정렬 경계 높이')],geo,
        [{'name':'threshold','value':threshold,'meaning':'이상(≥)이면 전경'}, {'name':'connectivity','value':8,'meaning':'대각선도 연결'}],
        [api('Python ZImage.find_blobs','reference/python/image-zimage.html'),api('Blob 데이터','reference/python/api-blob.html')],
        {'method':'NumPy >= 및 SciPy ndimage 8연결: 모든 마스크 픽셀, 모든 성분의 면적·경계와 중심 대조',
         'mask_exact':True,'all_components_match':True,'component_count':len(blobs)}))

    # Fit a real extracted pixel boundary, then independently recompute SDK inliers/RMS.
    component=labels[y0:y1,x0:x1]==selected['label']; filled=ndimage.binary_fill_holes(component)
    edge=filled & ~ndimage.binary_erosion(filled,structure=np.ones((3,3),dtype=bool),border_value=0)
    yy,xx=np.nonzero(edge)
    if len(xx)<3: raise RuntimeError('coin boundary has fewer than three points')
    points=[zv.Point2(float(x),float(y)) for x,y in zip(xx,yy)]
    tolerance=4.0;fit=zv.fit_circle(points,tolerance)
    residual=np.abs(np.hypot(xx-fit.center.x,yy-fit.center.y)-fit.radius)
    inlier=residual<=tolerance
    assert int(inlier.sum())==fit.stats.inliers,'independent circle inlier count mismatch'
    rms=float(np.sqrt(np.mean(np.square(residual[inlier]))))
    assert math.isclose(rms,fit.stats.rms_error,rel_tol=1e-8,abs_tol=1e-8),'circle RMS mismatch'
    cx,cy=float(fit.center.x+x0),float(fit.center.y+y0); radius=float(fit.radius)
    cg=geometry(circles=[{'cx':cx,'cy':cy,'radius':radius,'label':'SDK 피팅 원'}],
                points=[{'x':cx,'y':cy,'label':'원 중심'}]);cv=write_overlay(root,'coins-circle',coins,cg,roi)
    cases.append(case('coins-circle','동전 경계의 원 피팅','선택 성분의 채워진 픽셀 경계를 ROI 로컬 좌표로 피팅합니다.',
        'circle','coins',paths['coins'],w,h,roi,[step('경계 추출','SciPy binary_fill_holes / binary_erosion','이진 성분의 경계 픽셀 중심을 만듭니다.','stage/coins-threshold.png'),
        step('원 피팅','zvision.fit_circle','ROI 로컬 점으로 원을 적합하고 전체 영상 좌표로 표시합니다.',cv)],
        [metric('중심 x',cx,'px','ROI 원점을 더한 글로벌 중심'),metric('중심 y',cy,'px','ROI 원점을 더한 글로벌 중심'),
         metric('반경',radius,'px','피팅 원 반경'),metric('직경',2*radius,'px','반경의 두 배'),metric('채택 수',int(fit.stats.inliers),'points','SDK 허용 잔차 안의 점'),metric('RMS',float(fit.stats.rms_error),'px','SDK가 반환한 채택점 반경 잔차')],cg,
        [{'name':'inlier_threshold','value':tolerance,'meaning':'반경 잔차 한계(픽셀)'},{'name':'boundary_points','value':len(points),'meaning':'경계 픽셀 중심 수'}],
        [api('Python fit_circle','reference/python/api-fit_circle.html')],
        {'method':'NumPy로 각 경계점의 |hypot(x−cx,y−cy)−r|와 채택 수 및 RMS 재계산',
         'independent_inliers':int(inlier.sum()),'independent_rms_px':rms,'sdk_rms_px':float(fit.stats.rms_error)}))

    # 3: real camera profile, exact raw sample comparison and SDK caliper edge.
    camera=photos['camera'];h,w=camera.shape;y=h//2
    ps=zv.ProfileSpec(zv.Point2(0.0,float(y)),zv.Point2(float(w-1),float(y)),w,1)
    with gray_image(camera) as image:
        samples=image.profile(ps).samples
        edges=image.caliper(zv.CaliperSpec(ps,zv.EdgePolarity.ANY,5.0)).edges
    sample_values=np.array([s.value for s in samples]);assert np.allclose(sample_values,camera[y,:],atol=1e-9),'profile samples differ'
    if not edges:raise RuntimeError('camera row has no caliper edge at threshold 5')
    strongest=max(edges,key=lambda e:abs(e.strength));ex=float(strongest.position.x)
    assert 0<=ex<=w-1 and abs(strongest.position.y-y)<1e-8
    grad=(camera[y,2:].astype(float)-camera[y,:-2].astype(float))/2
    nearest=int(np.clip(round(ex),1,w-2)); near_gradient=float(grad[nearest-1])
    pg=geometry(lines=[{'x1':0,'y1':y,'x2':w-1,'y2':y,'label':'프로파일'}],points=[{'x':ex,'y':float(y),'label':'최강 검출 에지'}]);pv=write_overlay(root,'camera-profile',camera,pg,{'x':0,'y':0,'width':w,'height':h})
    cases.append(case('camera-profile','실제 사진의 프로파일과 에지','중앙 가로 줄의 강도 표본과 SDK의 부호 있는 에지 위치를 확인합니다.',
        'profile','camera',paths['camera'],w,h,{'x':0,'y':0,'width':w,'height':h},[step('프로파일','ZImage.profile','폭 1, 양 끝 포함 표본을 원본 배열과 대조합니다.',pv),
        step('에지','ZImage.caliper','양쪽 극성의 에지 중 강도 절댓값이 가장 큰 결과를 표시합니다.')],
        [metric('표본 수',len(samples),'samples','양 끝 포함'),metric('에지 수',len(edges),'edges','SDK가 찾은 후보 수'),
         metric('에지 x',ex,'px','전체 영상의 보간 위치'),metric('에지 거리',float(strongest.distance),'px','프로파일 시작점부터의 거리'),
         metric('에지 강도',float(strongest.strength),'intensity/px','부호 있는 보간 기울기')],pg,
        [{'name':'row','value':y,'meaning':'가로 프로파일의 영상 y'},{'name':'width','value':1,'meaning':'수직 횡단 표본 수'},{'name':'threshold','value':5,'meaning':'기울기 한계'}],
        [api('Python ZImage.profile','reference/python/image-zimage.html'),api('CaliperSpec','reference/python/api-caliperspec.html')],
        {'method':'NumPy 원본 행과 SDK 전체 표본을 요소별 비교; 선택 위치 부근 중앙차분을 별도 기록',
         'profile_exact':True,'nearest_discrete_gradient':near_gradient,'nearest_sample_x':nearest}))
    # Plot the actual SDK samples, marking its returned subpixel edge location.
    fig, ax = plt.subplots(figsize=(10, 3.6), layout='constrained')
    ax.plot(np.arange(len(sample_values)), sample_values, color='#245ea8', linewidth=1)
    ax.axvline(ex, color='#c23623', linestyle='--', linewidth=1.5, label=f'SDK edge x={ex:.2f} px')
    ax.set(xlabel='Sample x (px)', ylabel='Gray8 intensity', xlim=(0, w-1), ylim=(0, 255), title='Camera: SDK profile samples')
    ax.legend(loc='upper right'); ax.grid(alpha=0.25)
    fig.savefig(root/'plots/camera-profile.png', dpi=140); plt.close(fig)
    cases[-1]['plots']=[{'image':'plots/camera-profile.png', 'title':'SDK 강도 프로파일과 에지',
        'description':'SDK가 반환한 512개 강도 표본과 가장 강한 SDK 에지 위치를 표시합니다. 에지 위치의 독립적인 정확도 검증은 아닙니다.'}]

    # 4: text dark pixels through SDK invert+threshold, independently labelled.
    text=photos['text'];h,w=text.shape;text_threshold=160;expected_text=(255-text.astype(np.uint16))>=text_threshold
    _,text_components=get_blobs(expected_text)
    with gray_image(text) as image, image.invert() as inv, inv.threshold(float(text_threshold)) as text_mask:
        tsaved=sdk_mask_png(text_mask,root,'stage/text-mask.png');text_blobs=text_mask.find_blobs(8).blobs
    assert np.array_equal(tsaved,expected_text.astype(np.uint8)*255),'text mask mismatch'
    verify_sdk_blobs(text_blobs,text_components)
    eligible=[b for b in text_components if b['area']>=10]
    if not eligible:raise RuntimeError('text threshold produced no component with area >= 10')
    tb=max(eligible,key=lambda b:b['area']); sdk_tb=next(b for b in text_blobs if (b.area,b.x,b.y,b.width,b.height)==(tb['area'],tb['x'],tb['y'],tb['width'],tb['height']))
    tg=geometry(boxes=[{k:int(getattr(sdk_tb,k)) for k in ('x','y','width','height')}],points=[{'x':float(sdk_tb.centroid_x),'y':float(sdk_tb.centroid_y),'label':'중심'}]);tv=write_overlay(root,'text-components',text,tg,{'x':0,'y':0,'width':w,'height':h})
    cases.append(case('text-components','텍스트 사진의 어두운 연결 성분','텍스트 사진의 어두운 부분을 반전하고 임계값을 적용해 연결 성분을 측정합니다. 여러 획이나 선이 이어질 수 있으며 OCR이나 문자 단위 분할이 아닙니다.','blob',
        'text',paths['text'],w,h,{'x':0,'y':0,'width':w,'height':h},[step('반전과 이진화','ZImage.invert / ZImage.threshold','반전값 160 이상을 전경으로 만듭니다.','stage/text-mask.png'),
        step('성분 분석','ZImage.find_blobs(8)','면적 10 이상 중 가장 큰 성분을 표시합니다. 여러 획이나 선이 하나의 성분으로 이어질 수 있습니다.',tv)],
        [metric('전경 픽셀',int(np.count_nonzero(tsaved)),'px','SDK 마스크의 선택 픽셀 수'),metric('전체 성분',len(text_blobs),'components','8연결 성분 수'),metric('선택 면적',int(sdk_tb.area),'px²','선택된 성분 픽셀 수'),metric('중심 x',float(sdk_tb.centroid_x),'px','영상 로컬 좌표'),metric('중심 y',float(sdk_tb.centroid_y),'px','영상 로컬 좌표')],tg,
        [{'name':'threshold','value':text_threshold,'meaning':'반전 Gray8에서 이상인 값을 선택'},{'name':'connectivity','value':8,'meaning':'대각 포함 연결'}],
        [api('Python 이미지 API','reference/python/image-zimage.html')],{'method':'NumPy 반전·임계와 SciPy 8연결의 전 픽셀 및 성분 대조','mask_exact':True,'all_components_match':True}))

    # 5: public RGB photo, raw encoded RGB stats; compare to independent NumPy.
    coffee=photos['coffee'];h,w,_=coffee.shape;rx,ry,rw,rh=160,100,160,120
    crop=coffee[ry:ry+rh,rx:rx+rw,:];assert crop.shape==(rh,rw,3)
    with rgb_image(coffee) as image, image.roi(rx,ry,rw,rh) as view:
        st=view.color_statistics()
    expected=crop.astype(np.float64)/255.0;mean=expected.mean(axis=(0,1));std=expected.std(axis=(0,1))
    assert st.count==rw*rh and np.allclose(st.mean,mean,rtol=1e-9,atol=1e-9) and np.allclose(st.std_dev,std,rtol=1e-8,atol=1e-8),'RGB statistics mismatch'
    c_roi={'x':rx,'y':ry,'width':rw,'height':rh};cgeo=geometry();co=write_overlay(root,'coffee-color',coffee,cgeo,c_roi)
    cases.append(case('coffee-color','커피 사진 ROI의 RGB 통계','고정 ROI의 정규화 인코딩 RGB 평균과 모집단 표준편차를 비교합니다.',
        'color','coffee',paths['coffee'],w,h,c_roi,[step('ROI 선택','ZImage.roi','원본 컬러 영상의 실제 픽셀을 선택합니다.',co),
        step('RGB 통계','ZImage.color_statistics','채널별 정규화 인코딩 RGB 통계를 계산합니다.')],
        [metric('픽셀 수',int(st.count),'px','ROI 내부 표본 수')]+[metric(f'{ch} 평균',float(st.mean[i]),'0–1','정규화 인코딩 sRGB') for i,ch in enumerate('RGB')]+[metric(f'{ch} 표준편차',float(st.std_dev[i]),'0–1','모집단 표준편차') for i,ch in enumerate('RGB')],
        cgeo,[{'name':'ROI','value':f'({rx}, {ry}, {rw}, {rh})','meaning':'(x,y,width,height) 픽셀'}],
        [api('Python 색 통계','reference/python/api-colorstatistics.html')],
        {'method':'NumPy RGB/255 평균 및 ddof=0 표준편차와 비교','numpy_mean':mean.tolist(),'numpy_population_std':std.tolist()}))

    # 6: actual camera photo with explicitly disclosed controlled alteration.
    camera=photos['camera'];h,w=camera.shape;rx,ry,rw,rh=220,180,24,16
    modified=camera.copy(); patch=modified[ry:ry+rh,rx:rx+rw]; patch[:]=np.where(patch<=127,255,0).astype(np.uint8)
    Image.fromarray(modified).save(root/'stage/camera-controlled-modification.png')
    with gray_image(camera) as reference, gray_image(modified) as image:
        with image.inspection_difference(reference,None,zv.DifferenceSpec(32.0)) as diff:
            info=diff.info
            with diff.mask as mask: dm=sdk_mask_png(mask,root,'stage/camera-difference-mask.png')
    expected_diff=(np.abs(modified.astype(np.int16)-camera.astype(np.int16))>=32)
    assert np.array_equal(dm,expected_diff.astype(np.uint8)*255),'controlled difference mismatch'
    assert int(expected_diff.sum())==rw*rh and info.inspected_count==w*h
    d_roi={'x':rx,'y':ry,'width':rw,'height':rh};dg=geometry(boxes=[{'x':rx,'y':ry,'width':rw,'height':rh,'label':'통제 수정 영역'}]);dv=write_overlay(root,'camera-controlled-difference',modified,dg,d_roi)
    cases.append(case('camera-controlled-difference','사진에 통제 변화를 넣은 차분','실제 사진의 지정 24×16 영역을 인위적으로 바꿔 차분 마스크를 검증합니다.','inspection',
        'camera',paths['camera'],w,h,d_roi,[step('통제 수정','NumPy 조건부 반전','명시된 24×16 영역만 0 또는 255로 바꾼 합성 결함입니다.','stage/camera-controlled-modification.png'),
        step('SDK 차분','ZImage.inspection_difference','보정 없음, 절댓값 및 한계 32를 사용합니다.','stage/camera-difference-mask.png'),step('결과 위치','SDK 마스크 / 독립 픽셀 비교','삽입 영역과 검출 마스크를 비교합니다.',dv)],
        [metric('통제 수정 면적',rw*rh,'px²','의도적으로 변경한 픽셀 수'),metric('검출 픽셀',int(np.count_nonzero(dm)),'px','SDK 차분 마스크 전경'),metric('검사 픽셀',int(info.inspected_count),'px','전체 입력'),metric('최대 점수',float(info.max_score),'ratio','절대 차이를 32로 나눈 점수')],dg,
        [{'name':'threshold','value':32,'meaning':'원시 밝기 허용치'},{'name':'correction','value':'NONE','meaning':'전역 밝기 보정 없음'},{'name':'injected_region','value':f'({rx}, {ry}, {rw}, {rh})','meaning':'인위적 변화; 실제 결함 아님'}],
        [api('Python DifferenceSpec','reference/python/api-differencespec.html'),api('검사 차분','guides/difference-inspection.html')],
        {'method':'NumPy int16 절대 차이 >=32와 SDK 마스크의 전 픽셀 일치; 24×16=384','mask_exact':True,'expected_changed_pixels':384}))

    # 7: independent whole-photo gray statistics.
    camera=photos['camera'];h,w=camera.shape
    with gray_image(camera) as image: stat=image.statistics()
    expected_mean=float(camera.astype(np.float64).mean());expected_var=float(camera.astype(np.float64).var())
    assert stat.count==w*h and stat.min==int(camera.min()) and stat.max==int(camera.max())
    assert math.isclose(stat.mean,expected_mean,abs_tol=1e-9) and math.isclose(stat.variance,expected_var,abs_tol=1e-7)
    gg=geometry();gv=write_overlay(root,'camera-statistics',camera,gg,{'x':0,'y':0,'width':w,'height':h})
    cases.append(case('camera-statistics','사진의 전체 밝기 통계','실제 Gray8 영상의 픽셀 수·최소·최대·평균·분산을 원본 배열과 비교합니다.','statistics',
        'camera',paths['camera'],w,h,{'x':0,'y':0,'width':w,'height':h},[step('전체 영상','ZImage.from_gray8','공개 사진을 원본 Gray8 픽셀로 전달합니다.',gv),step('통계','ZImage.statistics','전체 보이는 픽셀의 통계를 구합니다.')],
        [metric('픽셀 수',int(stat.count),'px','폭×높이'),metric('최솟값',int(stat.min),'intensity','Gray8 원시 강도'),metric('최댓값',int(stat.max),'intensity','Gray8 원시 강도'),metric('평균',float(stat.mean),'intensity','모집단 평균'),metric('분산',float(stat.variance),'intensity²','모집단 분산')],gg,[],
        [api('Python 이미지 통계','reference/python/image-zimage.html')],{'method':'원본 NumPy 배열의 count/min/max/mean/var(ddof=0) 대조','numpy_mean':expected_mean,'numpy_variance':expected_var}))

    # The drawn rectangle is not always the region passed to the SDK.
    region_labels = {
        'coins-blob': ('선택 성분 표시 영역', '전체 원본 영상에서 이진화와 8연결 성분 분석을 수행합니다. 사각형은 선택 성분 주변 표시 영역이며 분석 ROI가 아닙니다.'),
        'coins-circle': ('피팅 점 추출 영역', '선택 성분 주변 영역의 경계 점을 ROI 로컬 좌표로 원 피팅하고, 결과 중심에 영역 원점을 더해 전체 영상 좌표로 표시합니다.'),
        'camera-profile': ('전체 영상 표시 범위', '전체 영상에 중앙 가로 한 줄의 양 끝과 표본 수를 지정하여 프로파일과 에지를 계산합니다. 사각형은 전체 영상 표시 범위입니다.'),
        'text-components': ('전체 영상 표시 범위', '전체 원본 영상의 반전과 이진화 결과에서 8연결 성분을 분석합니다. 선택 성분의 경계는 별도 검출 상자로 표시합니다.'),
        'coffee-color': ('색상 통계 ROI', '원본의 (160, 100)을 원점으로 하는 160×120 ROI를 SDK에 전달하여 색상 통계를 계산합니다.'),
        'camera-controlled-difference': ('인위적 수정 영역', '표시된 24×16 사각형만 인위적으로 수정했습니다. SDK 차분 검사는 마스크 없이 512×512 전체 영상에서 수행합니다.'),
        'camera-statistics': ('통계 입력 범위', 'ROI를 따로 자르지 않고 전체 원본 영상의 밝기 통계를 계산합니다.'),
    }
    for item in cases:
        item['roi_label'], item['processing_region'] = region_labels[item['id']]
    assert len(cases)==7
    result={'version':1,'sdk_revision':SDK_REVISION,'cases':cases}
    (root/'measurements.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (root/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(root),'cases':len(cases),'ids':[c['id'] for c in cases]},ensure_ascii=False))

if __name__=='__main__':main()
