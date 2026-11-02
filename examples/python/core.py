from zvision import ZImage, PixelFormat, Point2
from array import array
from tempfile import TemporaryDirectory
from pathlib import Path

with ZImage.from_gray8(3, 2, bytes([1, 2, 3, 4, 5, 6])) as image:
    assert image.info.pixel_format == PixelFormat.GRAY8
    with image.roi(1, 0, 2, 2) as roi:
        assert roi.to_array_gray8() == bytes([2, 3, 5, 6])
        assert (roi.origin.x, roi.origin.y) == (1, 0)
        assert roi.local_to_global(Point2(0, 1)) == Point2(1, 1)
        with roi.read_pixels() as view:
            row = view.row(1)
            assert list(row) == [5, 6] and row.readonly
        assert list(row) == [5, 6]
        row.release()
        with roi.clone_deep() as clone:
            assert clone.to_array_gray8() == bytes([2, 3, 5, 6])
    with image.crop_copy(0, 1, 2, 1) as crop:
        assert crop.to_array_gray8() == bytes([4, 5])
    with image.share() as shared:
        assert shared.to_array_gray8() == image.to_array_gray8()
    with TemporaryDirectory() as directory:
        path = Path(directory) / 'image.png'
        image.save(path)
        with ZImage.load(path) as loaded:
            assert loaded.to_array_gray8() == image.to_array_gray8()
with ZImage.from_buffer_gray16(2, 1, array('H', [0, 65535])) as image16:
    copied = image16.to_buffer_gray16()
    copied[0] = 42
    assert image16.to_array_gray16() == [0, 65535]
print('core examples passed')
