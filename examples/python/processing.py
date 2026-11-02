from zvision import ZImage

with ZImage.from_gray8(3, 1, bytes([0, 10, 20])) as image:
    with image.threshold(10) as mask:
        assert list(mask.to_array_gray8()) == [0, 255, 255]
    stats = image.statistics()
    assert stats.count == 3 and stats.mean == 10.0
    hist = image.histogram(256, 0, 256)
    assert hist[0][10] == 1
    with image.shift(1, 0) as shifted:
        assert list(shifted.image.to_array_gray8()) == [0, 0, 10]
        assert list(shifted.valid_mask.to_array_gray8()) == [0, 255, 255]
    print('mean:', stats.mean, 'histogram[10]:', hist[0][10])
