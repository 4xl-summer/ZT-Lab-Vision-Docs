using System;
using ZVision;
namespace ManualExamples;
public static class RecognitionAcq
{
    public static void Run()
    {
        var pixels = new byte[64]; for (int i = 0; i < pixels.Length; i++) pixels[i] = 127;
        using var image = ZImage.FromGray8(8, 8, pixels);
        var read = image.ReadBarcode(new BarcodeSpec(BarcodeFormat.QrCode));
        if (read.Status != ReadStatus.NoRead || read.Reasons != ReadReason.NotFound) throw new Exception("Expected no barcode");
        using var camera = SimulatedCamera.Create(new CameraSpec(1, 2, 1000, 2, TriggerMode.Software));
        camera.Connect(); camera.Start(); camera.Trigger(1, 100);
        if (camera.OfferFrame(image, 1, 10, 101, 1) != OfferDisposition.Accepted) throw new Exception("Offer failed");
        using (var frame = camera.TryGetFrame() ?? throw new Exception("Missing frame"))
        {
            if (frame.Info.FrameId != 1) throw new Exception("Wrong frame");
            using var captured = frame.Image;
        }
        if (camera.TryGetFrame() != null) throw new Exception("Queue was not empty");
        using var plc = SimulatedPlc.Create(10);
        if (plc.Command(PlcOperation.Request, 1, 0, 100) != PlcDisposition.Applied ||
            plc.Command(PlcOperation.Publish, 1, 42, 101) != PlcDisposition.Applied ||
            plc.Command(PlcOperation.Ack, 1, 0, 102) != PlcDisposition.Applied || plc.Info.Stats.Acks != 1) throw new Exception("PLC handshake failed");
        Console.WriteLine("No barcode; simulated frame and PLC handshake succeeded");
    }
}
