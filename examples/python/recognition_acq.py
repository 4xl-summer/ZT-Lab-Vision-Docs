from zvision import (ZImage, BarcodeSpec, BarcodeFormat, ReadStatus, ReadReason,
                     SimulatedCamera, CameraSpec, TriggerMode, OfferDisposition,
                     SimulatedPlc, PlcOperation, PlcDisposition)

with ZImage.from_gray8(8, 8, bytes([127] * 64)) as image:
    result = image.read_barcode(BarcodeSpec(BarcodeFormat.QR_CODE))
    assert result.status == ReadStatus.NO_READ and result.reasons == ReadReason.NOT_FOUND
    with SimulatedCamera.create(CameraSpec(1, 2, 1000, 2, TriggerMode.SOFTWARE)) as camera:
        camera.connect(); camera.start(); camera.trigger(1, 100)
        assert camera.offer_frame(image, 1, 10, 101, 1) == OfferDisposition.ACCEPTED
        with camera.try_get_frame() as frame:
            assert frame.info.frame_id == 1
            with frame.image as captured:
                assert captured.to_array_gray8() == bytes([127] * 64)
        assert camera.try_get_frame() is None
    with SimulatedPlc.create(10) as plc:
        assert plc.command(PlcOperation.REQUEST, 1, 0, 100) == PlcDisposition.APPLIED
        assert plc.command(PlcOperation.PUBLISH, 1, 42, 101) == PlcDisposition.APPLIED
        assert plc.command(PlcOperation.ACK, 1, 0, 102) == PlcDisposition.APPLIED
        assert plc.info.stats.acks == 1
print('No barcode; simulated frame and PLC handshake succeeded')
