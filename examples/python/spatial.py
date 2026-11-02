from zvision import DepthMap, PointCloud, Point3, LengthUnit, DepthCalibration, RigidTransform3
import math

P = Point3
U = LengthUnit.MILLIMETER
with DepthMap.from_values(3, 2, [1, None, 3, 4, 5, 6], 2, 3, P(10, 20, 30), U, 7) as depth:
    with depth.roi(1, 0, 2, 2) as roi, roi.to_point_cloud() as cloud:
        assert roi.info.origin == P(12, 20, 30)
        assert cloud.to_points()[1] == P(14, 20, 33)
    with depth.fill_holes(3, 1) as filled, depth.median(3, 1) as median:
        assert filled.to_values()[1] == 4 and median.to_values()[1] is None
    cal = DepthCalibration.fit([0, 1, 2, 3], [1, 3, 5, 7], U)
    with cal.apply(depth) as corrected:
        assert corrected.to_values()[0] == 3
    assert abs(cal.evaluate([4, 5], [9.5, 10.5]).rms_error - 0.5) < 1e-9
points = [P(x, y, 2*x-3*y+4) for y in range(-2, 3) for x in range(-2, 3)]
with PointCloud.from_points(points + [None], U, 1) as cloud:
    plane = cloud.fit_plane(1e-7)
    assert plane.inliers == plane.total == 25
    assert cloud.estimate_normals(5, P(0, 0, 100))[-1] is None
q = 1/math.sqrt(2)
cylinder = [P(3+t*q+2*math.cos(a)*q, -1+t*q-2*math.cos(a)*q, 5+2*math.sin(a))
            for t in (-3,-1,1,3) for a in (2*math.pi*i/16 for i in range(16))]
with PointCloud.from_points(cylinder, U, 2) as cloud:
    assert abs(cloud.fit_cylinder(1e-5).radius - 2) < 1e-4
src = [P(0,0,0), P(1,0,0), P(0,1,0), P(0,0,1)]
dst = [P(2-p.y, 3+p.x, 4+p.z) for p in src]
t = RigidTransform3.fit(src, dst, U, 8, 9)
held = [P(2,3,4), P(-1,2,5)]
truth = [P(2-p.y, 3+p.x, 4+p.z) for p in held]
assert t.evaluate(held, truth).max_error < 1e-8
with PointCloud.from_points(held + [None], U, 8) as cloud, cloud.transform(t) as moved:
    assert moved.info.frame == 9 and moved.to_points()[-1] is None
print('spatial examples passed')
