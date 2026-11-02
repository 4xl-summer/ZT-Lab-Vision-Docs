using System;
using ZVision;
namespace ManualExamples;
public static class Metrology
{
    public static void Run()
    {
        using var image = ZImage.FromGray8(11, 1, new byte[] { 0, 0, 0, 100, 100, 100, 100, 0, 0, 0, 0 });
        var spec = new ProfileSpec(new Point2(0, 0), new Point2(10, 0), 11, 1);
        using var profile = image.Profile(spec);
        using var caliper = image.Caliper(new CaliperSpec(spec, EdgePolarity.Any, 0));
        var samples = profile.ProfileSamples;
        var edges = caliper.CaliperEdges;
        if (samples.Length != 11 || edges.Length != 2 || Math.Abs(edges[0].Distance - 2.5) > 1e-6) throw new Exception("Profile/caliper mismatch");
        using var warped = image.WarpAffine(Affine2.Identity, 11, 1, Interpolation.Nearest, 0);
        var calibration = new PlanarCalibration(new Homography(0.1, 0, 0, 0, 0.1, 0, 0, 0, 1), LengthUnit.Millimeter);
        double distance = image.MeasureDistance(calibration, new Point2(0, 0), new Point2(10, 0), LengthUnit.Millimeter);
        var repeat = ZVision.Metrology.EvaluateRepeatability(new double[] { 9, 10, 11 }, 10, 0, 1);
        if (Math.Abs(distance - 1) > 1e-9 || !repeat.Passed || Math.Abs(repeat.SampleStddev - 1) > 1e-12) throw new Exception("Measurement mismatch");
        Console.WriteLine($"edges: {edges.Length}, distance mm: {distance}, sample standard deviation: {repeat.SampleStddev}");
    }
}
