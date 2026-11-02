using System;
using ZVision;

namespace ManualExamples;
public static class Processing
{
    public static void Run()
    {
        using var image = ZImage.FromGray8(3, 1, new byte[] { 0, 10, 20 });
        using var mask = image.Threshold(10);
        var pixels = mask.ToArrayGray8();
        if (pixels[0] != 0 || pixels[1] != 255 || pixels[2] != 255)
            throw new Exception("threshold");
        Statistics stats = image.Statistics();
        if (stats.Count != 3 || stats.Mean != 10.0) throw new Exception("statistics");
        var hist = image.Histogram(256, 0, 256);
        if (hist[0][10] != 1) throw new Exception("histogram");
        using var shifted = image.Shift(1, 0);
        var shiftedPixels = shifted.Image.ToArrayGray8();
        var valid = shifted.ValidMask.ToArrayGray8();
        if (shiftedPixels[2] != 10 || valid[0] != 0 || valid[1] != 255)
            throw new Exception("shift");
        Console.WriteLine($"mean: {stats.Mean}, histogram[10]: {hist[0][10]}");
    }
}
