using System;
using ZVision;

namespace ManualExamples;
public static class Color
{
    public static void Run()
    {
        using var image = ZImage.FromRgb8(2, 1, new byte[] {255,0,0, 0,255,0});
        using var hsv = image.ToHsv();
        using var hue = hsv.GetChannel(0);
        var h = hue.ToArrayGrayF64();
        if (h[0] != 0 || h[1] != 120) throw new Exception("HSV");
        using var lab = image.ToLab();
        using var l = lab.GetChannel(0);
        using var a = lab.GetChannel(1);
        using var b = lab.GetChannel(2);
        var target = new LabColor(l.ToArrayGrayF64()[0], a.ToArrayGrayF64()[0], b.ToArrayGrayF64()[0]);
        using var mask = image.ColorSegment(target, 0);
        var pixels = mask.ToArrayGray8();
        if (pixels[0] != 255 || pixels[1] != 0) throw new Exception("segment");
        var stats = image.ColorStatistics(mask);
        if (stats.Count != 1 || stats.Mean.R != 1) throw new Exception("statistics");
        var points = new[] { new ColorRgb(0,0,0), new ColorRgb(1,0,0), new ColorRgb(0,1,0), new ColorRgb(0,0,1), new ColorRgb(1,1,1) };
        var patches = Array.ConvertAll(points, v => new ColorPatch(v,v));
        using var fit = ColorCorrection.Fit(patches);
        if (fit.Info.Count != 5 || fit.Info.AfterMax >= 1e-6) throw new Exception("fit");
        using var corrected = image.ColorCorrect(fit.Info.Correction);
        if (ColorMath.DeltaE76(new LabColor(50,2,3), new LabColor(53,6,3)) != 5) throw new Exception("delta E");
        Console.WriteLine("color example passed");
    }
}
