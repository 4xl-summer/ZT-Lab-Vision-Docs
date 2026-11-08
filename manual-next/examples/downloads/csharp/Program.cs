using System.Text.Json;
using ZVision;

static void Check(bool ok, string name) { if (!ok) throw new Exception(name); }
var results = new Dictionary<string, object>();
using (var image = ZImage.FromGray8(4, 1, new byte[]{0,6,7,8})) {
    using var legacy = image.Threshold((byte)7);
    using var real = image.Threshold(7.0);
    Check(legacy.ToArrayGray8().SequenceEqual(new byte[]{0,0,255,255}), "threshold byte");
    Check(real.ToArrayGray8().SequenceEqual(legacy.ToArrayGray8()), "threshold double");
    results["threshold-gray8"] = new[]{0,0,255,255};
}
using (var image = ZImage.FromGrayF32(4, 1, new float[]{-1,6.5f,7,9})) {
    using var mask = image.Threshold(7.0);
    Check(mask.ToArrayGray8().SequenceEqual(new byte[]{0,0,255,255}), "threshold float");
    results["threshold-grayf32"] = new[]{0,0,255,255};
}
using (var image = ZImage.FromGray8(3, 2, new byte[]{10,20,30,40,50,60})) {
    using var roi = image.Roi(1,0,2,2);
    using var share = roi.Share(); using var clone = roi.CloneDeep();
    Check(roi.Origin.X == 1 && roi.Origin.Y == 0 && share.ToArrayGray8().SequenceEqual(new byte[]{20,30,50,60}) && clone.ToArrayGray8().SequenceEqual(share.ToArrayGray8()), "roi");
    using var plan = roi.Query().Capture("source");
    using var terminal = plan.RegionTopology(4); using var result = terminal.Execute(); using var captured = result.GetImage("source");
    Check(captured.ToArrayGray8().SequenceEqual(new byte[]{20,30,50,60}), "capture");
    results["roi-query"] = new { origin = new[]{1,0}, pixels = new[]{20,30,50,60} };
    string path = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".png");
    try { image.Save(path); using var loaded = ZImage.Load(path); Check(loaded.ToArrayGray8().SequenceEqual(image.ToArrayGray8()), "image IO"); }
    finally { if (File.Exists(path)) File.Delete(path); }
    results["image-io"] = true;
}
using (var mask = ZImage.FromGray8(3,3,new byte[]{1,1,1,1,0,1,1,1,1})) {
    var moments = mask.RegionMoments(4);
    Check(moments.Moments.Count == 1 && moments.Moments[0].Blob.Area == 8, "blob");
    results["blob"] = new { count = 1, area = 8 };
}
using (var image = ZImage.FromGray8(2,2,new byte[]{2,17,41,93})) {
    var spec = new MatchSpec(0,0,1,1,1,1,.999,0,1);
    using var model = MatchModel.TrainNcc(image, null); var found = model.Find(image,spec);
    Check(found.Matches.Count == 1, "match");
    using var alignment = image.AlignReference(image,new AlignmentSpec(new InspectionRect(0,0,2,2),spec,Interpolation.Nearest,1));
    Check(alignment.Found && alignment.Info.ValidCount == 4, "alignment");
    using var aligned = alignment.Aligned; using var valid = alignment.ValidMask;
    using var difference = aligned.InspectionDifference(image,valid,new DifferenceSpec(1));
    using var mask = difference.Mask; using var score = difference.Score;
    using var defects = mask.SurfaceDefects(score,new DefectSpec(8,1,8,2,4));
    using var decision = defects.Judge(new DecisionSpec(0,0,0,new InspectionRect(0,0,2,2)));
    Check(decision.Passed, "decision"); results["match-inspection"] = new { matches = 1, valid = 4, passed = true };
}
using (var image = ZImage.FromGray8(9,1,new byte[]{0,0,0,80,80,80,0,0,0})) {
    var spec = new ProfileSpec(new Point2(0,0),new Point2(8,0),9,1);
    var profile = image.Profile(spec); var caliper = image.Caliper(new CaliperSpec(spec,EdgePolarity.Any,0));
    Check(profile.Samples.Count == 9 && caliper.Edges.Count == 2 && Math.Abs(caliper.Edges[0].Distance-2.5)<1e-6, "caliper");
    results["profile-caliper"] = new { samples=9, edges=2, first=2.5 };
}
using (var image = ZImage.FromRgb8(2,1,new byte[]{255,0,0,0,0,255})) {
    using var hsv = image.ToHsv(); using var hue = hsv.GetChannel(0);
    Check(hue.ToArrayGrayF64().SequenceEqual(new double[]{0,240}), "hsv");
    using var lab = image.ToLab(); using var l = lab.GetChannel(0); Check(l.ToArrayGrayF64().Length==2, "lab");
    results["color"] = new { hue = new[]{0,240}, labPixels = 2 };
}
using (var depth = DepthMap.FromValues(2,2,new double?[]{1,null,3,4},2,3,new Point3(10,20,30),LengthUnit.Millimeter,7)) {
    using var roi = depth.Roi(1,0,1,2); using var cloud = roi.ToPointCloud();
    Check(roi.Info.Origin.X == 12 && cloud.ToPoints()[0] == null && cloud.ToPoints()[1]!.Value.Z == 34, "depth");
    results["spatial-depth"] = new { originX=12, secondZ=34 };
}
using (var image = ZImage.FromGray8(2,2,new byte[]{11,22,33,44})) {
    using var camera = SimulatedCamera.Create(new CameraSpec(1,2,1000,2,TriggerMode.Software));
    camera.Connect(); camera.Start(); camera.Trigger(1,100);
    Check(camera.OfferFrame(image,1,10,101,1)==OfferDisposition.Accepted, "offer");
    using var frame = camera.TryGetFrame() ?? throw new Exception("frame"); using var acquired = frame.Image;
    Check(acquired.ToArrayGray8().SequenceEqual(image.ToArrayGray8()), "capture");
    using var plc = SimulatedPlc.Create(10);
    Check(plc.Command(PlcOperation.Request,1,0,100)==PlcDisposition.Applied && plc.Command(PlcOperation.Publish,1,42,101)==PlcDisposition.Applied && plc.Command(PlcOperation.Ack,1,0,102)==PlcDisposition.Applied && plc.Info.Stats.Acks==1, "plc");
    results["camera-plc"] = new { frame=1, acks=1 };
}
using (var template = ZImage.FromGray8(3,2,new byte[]{3,17,1,8,2,25}))
using (var source = ZImage.FromGray8(4,2,new byte[]{0,3,17,1,0,8,2,25}))
using (var mask = ZImage.FromGray8(3,2,new byte[]{255,255,0,255,0,255})) {
    var spec = new MatchSpec(0,0,1,1,1,1,.99,0,1);
    using (var fullModel = MatchModel.TrainNcc(template)) {
        var fullMatch = fullModel.Find(source,spec);
        Check(fullModel.Info.SampleCount==6 && fullMatch.Best.HasValue && fullMatch.Best.Value.SampleCount==6 && Math.Abs(fullMatch.Best.Value.Position.X-2)<1e-9 && Math.Abs(fullMatch.Best.Value.Position.Y-.5)<1e-9 && Math.Abs(fullMatch.Best.Value.Score-1)<1e-9, "unmasked match");
    }
    MatchResult snapshot;
    string path = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".model");
    try {
        using (var model = MatchModel.TrainNcc(template,mask)) {
            Check(model.Info.SampleCount == 4, "masked model");
            snapshot = model.Find(source,spec); model.Save(path);
        }
        Check(snapshot.Best.HasValue && Math.Abs(snapshot.Best.Value.Position.X-2)<1e-9, "snapshot");
        using var loaded = MatchModel.Load(path); Check(loaded.Find(source,spec).Matches.Count == 1, "loaded model");
        using var blank = ZImage.FromGray8(4,2,new byte[8]); Check(loaded.Find(blank,spec).Best == null, "empty match");
    } finally { if (File.Exists(path)) File.Delete(path); }
    results["ncc-literal"] = new { x=2, y=0.5, samples=6, maskedSamples=4, empty=true };
}
using (var image = ZImage.FromGray8(2,2,new byte[]{1,1,1,1})) {
    using var spectrum = image.GeneralDft(2,2); var (real, imaginary) = spectrum.Parts();
    Check(Math.Abs(real[0]-4)<1e-9 && real.Skip(1).All(x=>Math.Abs(x)<1e-9) && imaginary.All(x=>Math.Abs(x)<1e-9), "dft");
    var inverse = spectrum.InverseComplex(); Check(inverse.Real.All(x=>Math.Abs(x-1)<1e-9), "inverse");
    results["dft"] = new { dc=4, inverse=1 };
}
{
    var points = new List<Point3?>();
    for (int y=-2; y<=2; y++) for (int x=-2; x<=2; x++) points.Add(new Point3(x,y,x+2*y+3));
    using var cloud = PointCloud.FromPoints(points.ToArray(),LengthUnit.Millimeter,1);
    var plane = cloud.FitPlane(1e-7); Check(plane.Inliers==25 && plane.Total==25, "plane fit");
    var src = new[]{new Point3(0,0,0),new Point3(1,0,0),new Point3(0,1,0),new Point3(0,0,1)};
    var dst = Array.ConvertAll(src,p=>new Point3(p.X+2,p.Y-3,p.Z+4));
    var transform = RigidTransform3.Fit(src,dst,LengthUnit.Millimeter,1,2);
    var held = new[]{new Point3(2,3,4)}; var truth = new[]{new Point3(4,0,8)};
    Check(transform.Evaluate(held,truth).MaxError<1e-8, "held-out transform");
    results["spatial-fit"] = new { planeInliers=25, heldOutMaxErrorBelow=1e-8 };
}
{
    var pixels = new[]{new Point2(100,200),new Point2(120,200),new Point2(100,240),new Point2(120,240)};
    var world = new[]{new Point2(11,38),new Point2(13,38),new Point2(11,46),new Point2(13,46)};
    var cal = PlanarCalibration.Fit(pixels,world,LengthUnit.Millimeter);
    var held = new[]{new Point2(110,220)}; var expected = new[]{new Point2(12.3,42.4)};
    var failed = cal.Evaluate(held,expected,LengthUnit.Millimeter,.49); var passed = cal.Evaluate(held,expected,LengthUnit.Millimeter,.51);
    Check(!failed.Metrics.Passed && passed.Metrics.Passed && Math.Abs(passed.Metrics.MaxWorld-.5)<1e-8 && Math.Abs(passed.Metrics.MaxPixel-Math.Sqrt(13))<1e-7, "calibration held-out");
    results["planar-heldout"] = new { worldResidual=.5, pixelResidual=Math.Sqrt(13), failedAt=.49, passedAt=.51 };
}
{
    var line = ZVision.Metrology.FitLine(new[]{new Point2(0,2),new Point2(1,2),new Point2(2,2),new Point2(3,2)},.1);
    var circle = ZVision.Metrology.FitCircle(new[]{new Point2(12,10),new Point2(10,12),new Point2(8,10),new Point2(10,8)},.1);
    Check(Math.Abs(line.Point.Y-2)<1e-8 && Math.Abs(circle.Center.X-10)<1e-8 && Math.Abs(circle.Center.Y-10)<1e-8 && Math.Abs(circle.Radius-2)<1e-8, "line circle");
    results["line-circle"] = new { lineY=2, center=new[]{10,10}, radius=2 };
}
using (var diagonal = ZImage.FromGray8(2,2,new byte[]{255,0,0,255})) {
    var four=diagonal.FindBlobs(4); var eight=diagonal.FindBlobs(8);
    Check(four.Blobs.Count==2 && eight.Blobs.Count==1 && eight.Blobs[0].Area==2 && eight.Blobs[0].CentroidX==.5 && eight.Blobs[0].CentroidY==.5,"blob connectivity");
    results["blob-connectivity"] = new { four=2, eight=1, area=2, centroid=new[]{.5,.5} };
}
{
    byte[] motif = { 1,2,7, 9,5,3, 4,8,6 };
    byte[] referencePixels = new byte[25];
    for (int y=0; y<3; y++) for (int x=0; x<3; x++) referencePixels[(y+1)*5+x+1] = motif[y*3+x];
    using var reference = ZImage.FromGray8(5, 5, referencePixels);
    var search = new MatchSpec(0, 0, 1, 1, 1, 1, .999999, 0, 1);
    var alignmentSpec = new AlignmentSpec(new InspectionRect(1,1,3,3), search, Interpolation.Nearest, 1);
    foreach (string name in new[]{"normal", "moved", "lighting", "spot", "missing"}) {
        byte[] pixels = new byte[49];
        int shift = name == "normal" ? 1 : 2;
        if (name != "missing") for (int y=0; y<3; y++) for (int x=0; x<3; x++) pixels[(y+shift)*7+x+shift] = motif[y*3+x];
        if (name == "lighting") for (int i=0; i<pixels.Length; i++) pixels[i] += 20;
        if (name == "spot") pixels[1*7+1] = 100;
        using var source = ZImage.FromGray8(7, 7, pixels);
        using var alignment = source.AlignReference(reference, alignmentSpec);
        if (!alignment.Found) { Check(name=="missing", "unexpected alignment failure"); continue; }
        Check(name!="missing" && alignment.Info.ValidCount==25, "alignment valid");
        using var aligned = alignment.Aligned; using var valid = alignment.ValidMask;
        using var difference = aligned.InspectionDifference(reference, valid, new DifferenceSpec(10, PhotometricCorrection.Offset));
        using var mask = difference.Mask; using var score = difference.Score;
        using var defects = mask.SurfaceDefects(score, new DefectSpec(8,1,8,2,4));
        using var decision = defects.Judge(new DecisionSpec(0,0,0, new InspectionRect(0,0,5,5)));
        Check(decision.Info.DefectCount==(name=="spot" ? 1UL : 0UL) && decision.Passed==(name!="spot"), "inspection "+name);
    }
    results["aligned-inspection"] = new { normal=0,moved=0,lighting=0,spot=1,missing="unavailable" };
}
using (var image = ZImage.FromGray8(2,2,new byte[]{0,1,2,3})) {
    bool badRoi=false, badConnectivity=false, badDft=false;
    try { using var invalid=image.Roi(2,0,1,1); } catch (Exception) { badRoi=true; }
    try { _=image.FindBlobs(6); } catch (Exception) { badConnectivity=true; }
    try { using var invalid=image.GeneralDft(0,1); } catch (Exception) { badDft=true; }
    Check(badRoi && badConnectivity && badDft,"invalid arguments");
    results["invalid-arguments"] = new { roi=true, connectivity=true, dft=true };
}
string? modelDir = Environment.GetEnvironmentVariable("ZVISION_MANUAL_MODELS");
if (!string.IsNullOrWhiteSpace(modelDir)) {
    using var black=ZImage.FromGray8(8,8,new byte[64]); using var white=ZImage.FromGray8(8,8,Enumerable.Repeat((byte)255,64).ToArray());
    AiEngine Load(string name,AiTask task,ulong classes) => AiEngine.FromBytes(File.ReadAllBytes(Path.Combine(modelDir,$"demo-{name}.rten")),new AiModelSpec(task,8,8,1,classes,7));
    using (var engine=Load("classification",AiTask.Classification,2)) using (var zero=engine.Run(black,new Rect(0,0,8,8),AiRunOptions.Default)) using (var full=engine.Run(white,new Rect(0,0,8,8),AiRunOptions.Default)) {
        Check(zero.Info.ClassId==0 && full.Info.ClassId==1 && Math.Abs(zero.Scores[0]-0.7310586)<1e-5 && Math.Abs(full.Scores[1]-0.7310586)<1e-5,"AI classification");
    }
    using (var engine=Load("detection",AiTask.Detection,1)) using (var result=engine.Run(black,new Rect(0,0,8,8),AiRunOptions.Default)) {
        var d=result.Detections; Check(d.Length==1 && Math.Abs(d[0].XMin-1)<1e-6 && Math.Abs(d[0].YMin-1)<1e-6 && Math.Abs(d[0].XMax-6)<1e-6 && Math.Abs(d[0].YMax-6)<1e-6 && Math.Abs(d[0].Score-.9)<1e-6,"AI detection");
    }
    using (var engine=Load("segmentation",AiTask.Segmentation,2)) using (var zero=engine.Run(black,new Rect(0,0,8,8),AiRunOptions.Default)) using (var full=engine.Run(white,new Rect(0,0,8,8),AiRunOptions.Default)) using (var z=zero.Map) using (var f=full.Map) {
        Check(z.ToArrayGrayU32().All(x=>x==0) && f.ToArrayGrayU32().All(x=>x==1),"AI segmentation");
    }
    using (var engine=Load("anomaly",AiTask.Anomaly,1)) using (var zero=engine.Run(black,new Rect(0,0,8,8),AiRunOptions.Default)) using (var full=engine.Run(white,new Rect(0,0,8,8),AiRunOptions.Default)) using (var z=zero.Map) using (var f=full.Map) {
        Check(z.ToArrayGrayF32().All(x=>x==0) && f.ToArrayGrayF32().All(x=>x==1) && zero.Info.Score==0 && full.Info.Score==1,"AI anomaly");
    }
    results["ai-demo"] = new { classification=new[]{0,1}, detection=1, segmentation=new[]{0,1}, anomaly=new[]{0,1} };
}

{
    using var listener = new System.Net.Sockets.TcpListener(System.Net.IPAddress.Loopback,0);
    listener.Start(); int port=((System.Net.IPEndPoint)listener.LocalEndpoint).Port;
    var server = Task.Run(() => {
        using var client=listener.AcceptTcpClient(); client.ReceiveTimeout=3000; client.SendTimeout=3000;
        using var stream=client.GetStream(); ushort register=0;
        for(int i=0;i<2;i++) {
            byte[] header=new byte[7]; stream.ReadExactly(header);
            int length=(header[4]<<8)|header[5]; Check(length==6 && header[6]==1,"modbus header");
            byte[] body=new byte[length-1]; stream.ReadExactly(body);
            int address=(body[1]<<8)|body[2], arg=(body[3]<<8)|body[4]; Check(address==5,"modbus address");
            byte[] response;
            if(body[0]==6) { register=(ushort)arg; response=body; }
            else { Check(body[0]==3 && arg==1,"modbus read"); response=new byte[]{3,2,(byte)(register>>8),(byte)register}; }
            header[4]=0; header[5]=(byte)(response.Length+1); stream.Write(header); stream.Write(response);
        }
    });
    using (var plc=ModbusTcp.Connect($"127.0.0.1:{port}",1,1000)) {
        plc.WriteSingleRegister(5,1234); Check(plc.ReadHoldingRegisters(5,1).SequenceEqual(new ushort[]{1234}),"modbus roundtrip");
    }
    Check(server.Wait(4000),"modbus server timeout");
    results["modbus-loopback"] = new { address=5,value=1234 };
}
{
    byte[] glyph={255,255,255,255,255, 255,0,0,0,255, 255,255,0,255,255, 255,255,0,255,255, 255,255,255,255,255};
    using var image=ZImage.FromGray8(5,5,glyph);
    var options=new FontOcrOptions { AllowedChars="T" };
    using var model=FontOcrModel.Train(new[]{new FontOcrSample(image,'T',1,1,3,3)},options);
    var read=model.Read(image,options,new[]{0.0});
    Check(read!=null && read.Glyphs.Length==1 && read.Glyphs[0].Codepoint=='T',"font ocr");
    results["font-ocr"] = new { text="T", glyphs=1 };
}
{
    var image=ZImage.FromGray8(3,1,new byte[]{1,7,9});
    using var shared=image.Share(); using var roi=image.Roi(1,0,2,1);
    using var plan=image.Query().Capture("before"); using var branch=plan.Clone();
    plan.Threshold(7.0); branch.Threshold(9.0);
    using var run=plan.Execute(); using var run2=branch.Execute();
    using var output=run.AcquireOutput(); using var captured=run.GetImage("before"); using var other=run2.AcquireOutput();
    image.Dispose(); run.Dispose(); run2.Dispose();
    Check(shared.ToArrayGray8().SequenceEqual(new byte[]{1,7,9}) && roi.ToArrayGray8().SequenceEqual(new byte[]{7,9}),"shared lifetime");
    Check(output.ToArrayGray8().SequenceEqual(new byte[]{0,255,255}) && other.ToArrayGray8().SequenceEqual(new byte[]{0,0,255}) && captured.ToArrayGray8().SequenceEqual(new byte[]{1,7,9}),"query lifetime");
    bool closed=false; try { _=image.Info; } catch(ObjectDisposedException) { closed=true; }
    Check(closed,"disposed access"); results["ownership-query"] = new { threshold7=new[]{0,255,255}, threshold9=new[]{0,0,255}, sourceClosed=true };
}
Console.WriteLine(JsonSerializer.Serialize(results));
