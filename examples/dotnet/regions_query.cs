using System;
using ZVision;

namespace ManualExamples;
public static class RegionsQuery
{
    public static void Run()
    {
        using var mask = ZImage.FromGray8(3, 3, new byte[] { 1, 1, 1, 1, 0, 1, 1, 1, 1 });
        using var topology = mask.RegionTopology(4);
        if (topology.Topology.Components != 1 || topology.Topology.Holes != 1 || topology.Topology.Euler != 0) throw new Exception("topology");
        using var moments = mask.RegionMoments(4);
        if (moments.Moments[0].Blob.Area != 8 || moments.Moments[0].Mu20 != 6) throw new Exception("moments");
        using var contours = mask.FindContours(4);
        if (contours.Contours.Length != 2 || !contours.Contours[1].IsHole) throw new Exception("contours");
        using var plan = mask.Query().Capture("mask");
        using var terminal = plan.RegionTopology(4);
        using var result = terminal.Run();
        using var captured = result.GetImage("mask");
        if (result.Topology.Holes != 1) throw new Exception("query");
        Console.WriteLine("component=1, holes=1, area=8");
    }
}
