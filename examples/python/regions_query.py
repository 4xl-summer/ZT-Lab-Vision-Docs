from zvision import ZImage

with ZImage.from_gray8(3, 3, bytes([1, 1, 1, 1, 0, 1, 1, 1, 1])) as mask:
    with mask.region_topology(4) as result:
        assert (result.topology.components, result.topology.holes, result.topology.euler) == (1, 1, 0)
    with mask.region_moments(4) as result:
        moment = result.moments[0]
        assert (moment.blob.area, moment.mu20, moment.mu02) == (8, 6.0, 6.0)
    with mask.find_contours(4) as result:
        rings = result.contours
        assert len(rings) == 2 and rings[1].is_hole
    with mask.query() as plan:
        plan.capture('mask')
        with plan.find_blobs(4) as blobs:
            blobs.where(lambda b: b.area >= 8).order_by(lambda b: b.area, descending=True)
            with blobs.run() as result:
                assert len(result.output) == 1
                with result.get_image('mask') as captured:
                    assert captured.info.width == 3
    print('component=1, holes=1, area=8')
