from zvision import (ZImage, PixelFormat, LabColor, ColorPatch,
                     fit_color_correction, delta_e76)

with ZImage.from_rgb8(2, 1, bytes((255, 0, 0, 0, 255, 0))) as image:
    with image.to_hsv() as hsv:
        with hsv.get_channel(0) as hue:
            assert hue.to_array_grayf64() == [0.0, 120.0]
        with hsv.to_rgb(PixelFormat.RGB8) as restored:
            assert restored.to_array_rgb8() == image.to_array_rgb8()
    with image.to_lab() as lab:
        channels = [lab.get_channel(i) for i in range(3)]
        try:
            target = LabColor(*(c.to_array_grayf64()[0] for c in channels))
        finally:
            for c in channels: c.close()
    with image.color_segment(target, 0) as mask:
        assert mask.to_array_gray8() == bytes((255, 0))
        stats = image.color_statistics(mask)
        assert stats.count == 1 and stats.mean == (1.0, 0.0, 0.0)
    points = [(0,0,0), (1,0,0), (0,1,0), (0,0,1), (1,1,1)]
    with fit_color_correction([ColorPatch(v,v) for v in points]) as fit:
        assert fit.info.count == 5 and fit.info.after_max < 1e-6
        with image.color_correct(fit.info.correction) as corrected:
            assert corrected.to_array_rgb8() == image.to_array_rgb8()
assert delta_e76(LabColor(50,2,3), LabColor(53,6,3)) == 5
print("color example passed")
