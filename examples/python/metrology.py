from zvision import (ZImage, Point2, Affine2, Interpolation, ProfileSpec, CaliperSpec,
                     EdgePolarity, LengthUnit, PlanarCalibration, Homography,
                     point_distance, evaluate_repeatability)

p = Point2
with ZImage.from_gray8(11, 1, bytes([0, 0, 0, 100, 100, 100, 100, 0, 0, 0, 0])) as image:
    spec = ProfileSpec(p(0, 0), p(10, 0), 11, 1)
    with image.profile(spec) as result:
        samples = result.output
    with image.caliper(CaliperSpec(spec, EdgePolarity.ANY, 0)) as result:
        edges = result.output
    assert len(samples) == 11 and len(edges) == 2
    assert abs(edges[0].distance - 2.5) < 1e-6
    with image.warp_affine(Affine2.identity(), 11, 1, Interpolation.NEAREST, 0) as warped:
        assert warped.info.width == 11
    calibration = PlanarCalibration(Homography(0.1, 0, 0, 0, 0.1, 0, 0, 0, 1), LengthUnit.MILLIMETER)
    distance = image.measure_distance(calibration, p(0, 0), p(10, 0), LengthUnit.MILLIMETER)
    assert abs(distance - 1.0) < 1e-9
assert point_distance(p(0, 0), p(3, 4)) == 5
repeat = evaluate_repeatability([9, 10, 11], 10, 0, 1)
assert repeat.passed and abs(repeat.sample_stddev - 1) < 1e-12
print('edges:', len(edges), 'distance mm:', distance, 'sample standard deviation:', repeat.sample_stddev)
