"""Independent synthetic SDK examples; emits one JSON object after all checks pass."""
import os
import json
import socket
import struct
import threading
import tempfile
from pathlib import Path
from zvision import (ZImage, Point2, MatchModel, MatchSpec, AlignmentSpec, DifferenceSpec,
                     DefectSpec, DecisionSpec, Interpolation, PhotometricCorrection, ProfileSpec, CaliperSpec,
                     EdgePolarity, DepthMap, Point3, LengthUnit, SimulatedCamera, CameraSpec,
                     TriggerMode, OfferDisposition, SimulatedPlc, PlcOperation, PlcDisposition, PointCloud, RigidTransform3, PlanarCalibration, ModbusTcp, fit_line, fit_circle, AiEngine, AiModelSpec, AiTask, FontOptions, FontSample, FontModel)

out = {}
with ZImage.from_gray8(4, 1, bytes([0, 6, 7, 8])) as image:
    with image.threshold(7) as mask:
        assert list(mask.to_array_gray8()) == [0, 0, 255, 255]
        out['threshold-gray8'] = [0, 0, 255, 255]
with ZImage.from_grayf32(4, 1, [-1, 6.5, 7, 9]) as image:
    with image.threshold(7.0) as mask:
        assert list(mask.to_array_gray8()) == [0, 0, 255, 255]
        out['threshold-grayf32'] = [0, 0, 255, 255]
with ZImage.from_gray8(3, 2, bytes([10, 20, 30, 40, 50, 60])) as image:
    with image.roi(1, 0, 2, 2) as roi, roi.share() as shared, roi.clone_deep() as clone:
        assert (roi.origin.x, roi.origin.y) == (1, 0)
        assert shared.to_array_gray8() == clone.to_array_gray8() == bytes([20, 30, 50, 60])
        with roi.query() as plan:
            plan.capture('source')
            with plan.region_topology(4) as terminal, terminal.execute() as result, result.get_image('source') as captured:
                assert captured.to_array_gray8() == bytes([20, 30, 50, 60])
        out['roi-query'] = {'origin': [1, 0], 'pixels': [20, 30, 50, 60]}
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'image.png'
        image.save(path)
        with ZImage.load(path) as loaded:
            assert loaded.to_array_gray8() == image.to_array_gray8()
    out['image-io'] = True
with ZImage.from_gray8(3, 3, bytes([1,1,1,1,0,1,1,1,1])) as mask:
    moments = mask.region_moments(4)
    assert len(moments.moments) == 1 and moments.moments[0].blob.area == 8
    out['blob'] = {'count': 1, 'area': 8}
with ZImage.from_gray8(2, 2, bytes([2,17,41,93])) as image:
    spec = MatchSpec(0, 0, 1, 1, 1, 1, .999, 0, 1)
    with MatchModel.train_ncc(image) as model:
        matches = model.find(image, spec)
        assert len(matches.matches) == 1
    with image.align_reference(image, AlignmentSpec((0,0,2,2),spec,Interpolation.NEAREST)) as alignment:
        assert alignment.found and alignment.valid_count == 4
        with alignment.aligned as aligned, alignment.valid_mask as valid:
            with aligned.inspection_difference(image,valid,DifferenceSpec(1)) as difference:
                with difference.mask as mask, difference.score as score:
                    with mask.surface_defects(score,DefectSpec()) as defects:
                        with defects.judge(DecisionSpec(0,0,0,(0,0,2,2))) as decision:
                            assert decision.passed
    out['match-inspection'] = {'matches':1, 'valid':4, 'passed':True}
with ZImage.from_gray8(9,1,bytes([0,0,0,80,80,80,0,0,0])) as image:
    spec = ProfileSpec(Point2(0,0),Point2(8,0),9,1)
    profile = image.profile(spec)
    caliper = image.caliper(CaliperSpec(spec,EdgePolarity.ANY,0))
    assert len(profile.samples)==9 and len(caliper.edges)==2 and abs(caliper.edges[0].distance-2.5)<1e-6
    out['profile-caliper'] = {'samples':9,'edges':2,'first':2.5}
with ZImage.from_rgb8(2,1,bytes([255,0,0,0,0,255])) as image:
    with image.to_hsv() as hsv, hsv.get_channel(0) as hue:
        assert hue.to_array_grayf64() == [0.0,240.0]
    with image.to_lab() as lab, lab.get_channel(0) as lightness:
        assert len(lightness.to_array_grayf64()) == 2
    out['color'] = {'hue':[0,240], 'labPixels':2}
with DepthMap.from_values(2,2,[1,None,3,4],2,3,Point3(10,20,30),LengthUnit.MILLIMETER,7) as depth:
    with depth.roi(1,0,1,2) as roi, roi.to_point_cloud() as cloud:
        assert roi.info.origin.x==12 and cloud.to_points()[0] is None and cloud.to_points()[1].z==34
        out['spatial-depth'] = {'originX':12,'secondZ':34}
with ZImage.from_gray8(2,2,bytes([11,22,33,44])) as image:
    with SimulatedCamera.create(CameraSpec(1,2,1000,2,TriggerMode.SOFTWARE)) as camera:
        camera.connect(); camera.start(); camera.trigger(1,100)
        assert camera.offer_frame(image,1,10,101,1)==OfferDisposition.ACCEPTED
        with camera.try_get_frame() as frame, frame.image as acquired:
            assert acquired.to_array_gray8()==image.to_array_gray8()
    with SimulatedPlc.create(10) as plc:
        assert plc.command(PlcOperation.REQUEST,1,0,100)==PlcDisposition.APPLIED
        assert plc.command(PlcOperation.PUBLISH,1,42,101)==PlcDisposition.APPLIED
        assert plc.command(PlcOperation.ACK,1,0,102)==PlcDisposition.APPLIED and plc.info.stats.acks==1
    out['camera-plc'] = {'frame':1,'acks':1}
with ZImage.from_gray8(3,2,bytes([3,17,1,8,2,25])) as template, ZImage.from_gray8(4,2,bytes([0,3,17,1,0,8,2,25])) as source, ZImage.from_gray8(3,2,bytes([255,255,0,255,0,255])) as mask:
    spec = MatchSpec(0,0,1,1,1,1,.99,0,1)
    with MatchModel.train_ncc(template) as full_model:
        full_match = full_model.find(source,spec).best
        assert full_model.info.sample_count==6 and full_match is not None and full_match.sample_count==6
        assert abs(full_match.position.x-2)<1e-9 and abs(full_match.position.y-.5)<1e-9 and abs(full_match.score-1)<1e-9
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'model.bin'
        with MatchModel.train_ncc(template,mask) as model:
            assert model.info.sample_count == 4
            snapshot = model.find(source,spec)
            model.save(path)
        assert snapshot.best is not None and abs(snapshot.best.position.x-2)<1e-9
        with MatchModel.load(path) as loaded, ZImage.from_gray8(4,2,bytes(8)) as blank:
            assert len(loaded.find(source,spec).matches)==1 and loaded.find(blank,spec).best is None
    out['ncc-literal'] = {'x':2,'y':0.5,'samples':6,'maskedSamples':4,'empty':True}
with ZImage.from_gray8(2,2,bytes([1,1,1,1])) as image, image.general_dft(2,2) as spectrum:
    real, imaginary = spectrum.parts()
    assert abs(real[0]-4)<1e-9 and all(abs(v)<1e-9 for v in real[1:]+imaginary)
    width,height,inverse,imaginary_inverse = spectrum.inverse_complex()
    assert (width,height)==(2,2) and all(abs(v-1)<1e-9 for v in inverse)
    out['dft'] = {'dc':4,'inverse':1}
points = [Point3(x,y,x+2*y+3) for y in range(-2,3) for x in range(-2,3)]
with PointCloud.from_points(points,LengthUnit.MILLIMETER,1) as cloud:
    plane = cloud.fit_plane(1e-7)
    assert plane.inliers == plane.total == 25
src = [Point3(0,0,0),Point3(1,0,0),Point3(0,1,0),Point3(0,0,1)]
dst = [Point3(p.x+2,p.y-3,p.z+4) for p in src]
transform = RigidTransform3.fit(src,dst,LengthUnit.MILLIMETER,1,2)
assert transform.evaluate([Point3(2,3,4)],[Point3(4,0,8)]).max_error < 1e-8
out['spatial-fit'] = {'planeInliers':25,'heldOutMaxErrorBelow':1e-8}
pixels = [Point2(100,200),Point2(120,200),Point2(100,240),Point2(120,240)]
world = [Point2(11,38),Point2(13,38),Point2(11,46),Point2(13,46)]
cal = PlanarCalibration.fit(pixels,world,LengthUnit.MILLIMETER)
held, expected = [Point2(110,220)], [Point2(12.3,42.4)]
failed = cal.evaluate(held,expected,LengthUnit.MILLIMETER,.49)
passed = cal.evaluate(held,expected,LengthUnit.MILLIMETER,.51)
assert not failed.metrics.passed and passed.metrics.passed
assert abs(passed.metrics.max_world-.5)<1e-8 and abs(passed.metrics.max_pixel-13**.5)<1e-7
out['planar-heldout'] = {'worldResidual':.5,'pixelResidual':13**.5,'failedAt':.49,'passedAt':.51}
# A tiny loopback FC06/FC03 peer models one holding register; no external PLC is used.
def modbus_peer(listener, errors):
    try:
        conn, _ = listener.accept()
        with conn:
            conn.settimeout(3)
            value = 0
            for _ in range(2):
                def receive(n):
                    data = b''
                    while len(data) < n:
                        part = conn.recv(n-len(data))
                        if not part: raise EOFError('Modbus connection closed')
                        data += part
                    return data
                header = receive(7)
                transaction, protocol, length, unit = struct.unpack('>HHHB', header)
                assert protocol == 0 and unit == 1
                body = receive(length-1)
                function, address, arg = struct.unpack('>BHH', body)
                assert address == 5
                if function == 6:
                    value = arg
                    response = body
                else:
                    assert function == 3 and arg == 1
                    response = struct.pack('>BBH',3,2,value)
                conn.sendall(struct.pack('>HHHB',transaction,0,len(response)+1,unit)+response)
    except Exception as error:
        errors.append(error)
with socket.socket() as listener:
    listener.bind(('127.0.0.1',0)); listener.listen(1); listener.settimeout(3)
    errors = []
    server = threading.Thread(target=modbus_peer,args=(listener,errors),daemon=True); server.start()
    with ModbusTcp.connect('127.0.0.1:%d' % listener.getsockname()[1],1,1000) as plc:
        plc.write_single_register(5,1234)
        assert plc.read_holding_registers(5,1)==[1234]
    server.join(4)
    assert not server.is_alive() and not errors, errors
    out['modbus-loopback'] = {'address':5,'value':1234}
line = fit_line([Point2(0,2),Point2(1,2),Point2(2,2),Point2(3,2)],.1)
circle = fit_circle([Point2(12,10),Point2(10,12),Point2(8,10),Point2(10,8)],.1)
assert abs(line.point.y-2)<1e-8 and abs(circle.center.x-10)<1e-8 and abs(circle.center.y-10)<1e-8 and abs(circle.radius-2)<1e-8
out['line-circle'] = {'lineY':2,'center':[10,10],'radius':2}
with ZImage.from_gray8(2,2,bytes([255,0,0,255])) as diagonal:
    four, eight = diagonal.find_blobs(4), diagonal.find_blobs(8)
    assert len(four.blobs)==2 and len(eight.blobs)==1
    b = eight.blobs[0]
    assert (b.area,b.centroid_x,b.centroid_y)==(2,.5,.5)
    out['blob-connectivity'] = {'four':2,'eight':1,'area':2,'centroid':[.5,.5]}
with ZImage.from_gray8(2,2,bytes([0,1,2,3])) as image:
    for operation in (lambda: image.roi(2,0,1,1), lambda: image.find_blobs(6), lambda: image.general_dft(0,1)):
        try:
            result = operation()
        except (ValueError, RuntimeError):
            pass
        else:
            if hasattr(result,'close'): result.close()
            raise AssertionError('invalid argument unexpectedly accepted')
    out['invalid-arguments'] = {'roi':True,'connectivity':True,'dft':True}
model_dir = os.environ.get('ZVISION_MANUAL_MODELS')
if model_dir:
    with ZImage.from_gray8(8,8,bytes(64)) as black, ZImage.from_gray8(8,8,bytes([255]*64)) as white:
        def load(name, task, classes):
            return AiEngine.from_bytes((Path(model_dir)/('demo-'+name+'.rten')).read_bytes(),AiModelSpec(task,8,8,1,classes,7))
        with load('classification',AiTask.CLASSIFICATION,2) as engine, engine.run(black,(0,0,8,8)) as zero, engine.run(white,(0,0,8,8)) as full:
            assert zero.info.class_id==0 and full.info.class_id==1
            assert abs(zero.scores[0]-.7310586)<1e-5 and abs(full.scores[1]-.7310586)<1e-5
        with load('detection',AiTask.DETECTION,1) as engine, engine.run(black,(0,0,8,8)) as result:
            d = result.detections
            assert len(d)==1 and all(abs(a-b)<1e-6 for a,b in zip((d[0].x_min,d[0].y_min,d[0].x_max,d[0].y_max,d[0].score),(1,1,6,6,.9)))
        with load('segmentation',AiTask.SEGMENTATION,2) as engine, engine.run(black,(0,0,8,8)) as zero, engine.run(white,(0,0,8,8)) as full, zero.map as z, full.map as f:
            assert all(v==0 for v in z.to_array_grayu32()) and all(v==1 for v in f.to_array_grayu32())
        with load('anomaly',AiTask.ANOMALY,1) as engine, engine.run(black,(0,0,8,8)) as zero, engine.run(white,(0,0,8,8)) as full, zero.map as z, full.map as f:
            assert all(v==0 for v in z.to_array_grayf32()) and all(v==1 for v in f.to_array_grayf32()) and zero.info.score==0 and full.info.score==1
    out['ai-demo'] = {'classification':[0,1],'detection':1,'segmentation':[0,1],'anomaly':[0,1]}

glyph = bytes([255,255,255,255,255, 255,0,0,0,255, 255,255,0,255,255, 255,255,0,255,255, 255,255,255,255,255])
with ZImage.from_gray8(5,5,glyph) as image:
    options = FontOptions('T')
    with FontModel.train([FontSample(image,'T',(1,1,3,3))],options) as model:
        read = model.read(image,options)
        assert read is not None and len(read.glyphs)==1 and read.glyphs[0].label=='T'
        out['font-ocr'] = {'text':'T','glyphs':1}
image = ZImage.from_gray8(3,1,bytes([1,7,9]))
shared, roi = image.share(), image.roi(1,0,2,1)
plan = image.query(); plan.capture('before'); branch = plan.clone()
plan.threshold(7); branch.threshold(9)
run, run2 = plan.execute(), branch.execute()
output, captured, other = run.acquire_output(), run.get_image('before'), run2.acquire_output()
image.close(); run.close(); run2.close(); plan.close(); branch.close()
try:
    assert shared.to_array_gray8()==bytes([1,7,9]) and roi.to_array_gray8()==bytes([7,9])
    assert output.to_array_gray8()==bytes([0,255,255]) and other.to_array_gray8()==bytes([0,0,255]) and captured.to_array_gray8()==bytes([1,7,9])
    try: image.to_array_gray8()
    except ValueError: pass
    else: raise AssertionError('closed image accepted')
finally:
    shared.close(); roi.close(); output.close(); captured.close(); other.close()
out['ownership-query'] = {'threshold7':[0,255,255],'threshold9':[0,0,255],'sourceClosed':True}
# Identical alignment fixture to the C# runner, with explicit missing-alignment handling.
motif = [1,2,7,9,5,3,4,8,6]
reference_pixels = bytearray(25)
for y in range(3):
    for x in range(3): reference_pixels[(y+1)*5+x+1] = motif[y*3+x]
search = MatchSpec(0,0,1,1,1,1,.999999,0,1)
alignment_spec = AlignmentSpec((1,1,3,3),search,Interpolation.NEAREST,1)
with ZImage.from_gray8(5,5,bytes(reference_pixels)) as reference:
    for name in ('normal','moved','lighting','spot','missing'):
        pixels = bytearray(49)
        shift = 1 if name == 'normal' else 2
        if name != 'missing':
            for y in range(3):
                for x in range(3): pixels[(y+shift)*7+x+shift] = motif[y*3+x]
        if name == 'lighting': pixels = bytearray(v+20 for v in pixels)
        if name == 'spot': pixels[1*7+1] = 100
        with ZImage.from_gray8(7,7,bytes(pixels)) as source, source.align_reference(reference,alignment_spec) as alignment:
            if not alignment.found:
                assert name == 'missing'
                continue
            assert name != 'missing' and alignment.valid_count == 25
            with alignment.aligned as aligned, alignment.valid_mask as valid:
                with aligned.inspection_difference(reference,valid,DifferenceSpec(10,PhotometricCorrection.OFFSET)) as difference:
                    with difference.mask as mask, difference.score as score:
                        with mask.surface_defects(score,DefectSpec(8,1,8,2,4)) as defects:
                            with defects.judge(DecisionSpec(0,0,0,(0,0,5,5))) as decision:
                                assert decision.info.defect_count == (1 if name=='spot' else 0)
                                assert decision.passed == (name != 'spot')
out['aligned-inspection'] = {'normal':0,'moved':0,'lighting':0,'spot':1,'missing':'unavailable'}

print(json.dumps(out, sort_keys=True))
