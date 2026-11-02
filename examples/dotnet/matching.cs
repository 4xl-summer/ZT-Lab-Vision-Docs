using System;
using ZVision;

namespace ManualExamples;
public static class Matching
{
    public static void Run()
    {
        using var image = ZImage.FromGray8(2, 2, new byte[] { 0, 13, 29, 61 });
        var search = new MatchSpec(0, 0, 1, 1, 1, 1, .999, 0, 1);
        using var model = MatchModel.TrainNcc(image, null);
        using var matches = image.FindMatches(model, search);
        if (matches.Matches.Length != 1) throw new Exception("Expected one match");
        using var alignment = image.AlignReference(image, new AlignmentSpec(new InspectionRect(0, 0, 2, 2), search, Interpolation.Nearest, 1));
        if (!alignment.Found || alignment.Info.ValidCount != 4) throw new Exception("Alignment failed");
        using var aligned = alignment.Aligned;
        using var valid = alignment.ValidMask;
        using var difference = aligned.InspectionDifference(image, valid, new DifferenceSpec(1));
        using var mask = difference.Mask;
        using var score = difference.Score;
        using var defects = mask.SurfaceDefects(score, new DefectSpec(8, 1, 8, 2, 4));
        using var decision = defects.Judge(new DecisionSpec(0, 0, 0, new InspectionRect(0, 0, 2, 2)));
        if (!decision.Passed) throw new Exception("Expected pass");
        Console.WriteLine("Match count: " + matches.Matches.Length + "; decision: " + decision.Passed);
    }
}
