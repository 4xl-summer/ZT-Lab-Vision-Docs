using System;
using System.IO;
using ZVision;

namespace ManualExamples;
public static class Core
{
    public static void Run()
    {
        using (var image = ZImage.FromGray8(3, 2, new byte[] { 1, 2, 3, 4, 5, 6 }))
        using (var roi = image.Roi(1, 0, 2, 2))
        {
            if (roi.Info.PixelFormat != PixelFormat.Gray8 || roi.Origin.X != 1) throw new Exception("ROI metadata");
            using (var view = roi.ReadPixels())
            using (var row = view.OpenRow(1))
                if (row.ReadByte() != 5 || row.ReadByte() != 6) throw new Exception("row");
            using (var clone = roi.CloneDeep())
                if (clone.ToArrayGray8()[2] != 5) throw new Exception("clone");
            using (var crop = image.CropCopy(0, 1, 2, 1))
                if (crop.ToArrayGray8()[0] != 4) throw new Exception("crop");
            using (var shared = image.Share())
                if (shared.ToArrayGray8()[5] != 6) throw new Exception("share");
            string path = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".png");
            try
            {
                image.Save(path);
                using (var loaded = ZImage.Load(path))
                    if (loaded.ToArrayGray8()[5] != 6) throw new Exception("PNG");
            }
            finally { if (File.Exists(path)) File.Delete(path); }
        }
        Console.WriteLine("core examples passed");
    }
}
