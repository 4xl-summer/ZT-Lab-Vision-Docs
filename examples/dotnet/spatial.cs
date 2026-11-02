using System;
using ZVision;
namespace ManualExamples;
public static class Spatial {
 public static void Run() {
  var u=LengthUnit.Millimeter;
  using(var d=DepthMap.FromValues(3,2,new double?[]{1,null,3,4,5,6},2,3,new Point3(10,20,30),u,7)) {
   using(var roi=d.Roi(1,0,2,2)) using(var cloud=roi.ToPointCloud()) {
    if(roi.Info.Origin.X!=12 || cloud.ToPoints()[1]!.Value.Z!=33) throw new Exception("ROI");
   }
   using(var filled=d.FillHoles(3,1)) using(var med=d.Median(3,1)) {
    if(filled.ToValues()[1]!=4 || med.ToValues()[1]!=null) throw new Exception("filter");
   }
   var cal=DepthCalibration.Fit(new double[]{0,1,2,3},new double[]{1,3,5,7},u);
   using(var corrected=cal.Apply(d)) { if(corrected.ToValues()[0]!=3) throw new Exception("calibration"); }
   if(Math.Abs(cal.Evaluate(new double[]{4,5},new double[]{9.5,10.5}).RmsError-0.5)>1e-9) throw new Exception("metrics");
  }
  var planePoints=new Point3?[25]; int k=0;
  for(int y=-2;y<=2;y++) for(int x=-2;x<=2;x++) planePoints[k++]=new Point3(x,y,2*x-3*y+4);
  using(var c=PointCloud.FromPoints(planePoints,u,1)) { if(c.FitPlane(1e-7).Inliers!=25 || c.EstimateNormals(5,new Point3(0,0,100)).Length!=25) throw new Exception("plane"); }
  double q=1/Math.Sqrt(2); var cylinder=new Point3?[64]; k=0;
  for(int ti=0;ti<4;ti++) { double z=-3+2*ti; for(int i=0;i<16;i++) { double a=2*Math.PI*i/16; cylinder[k++]=new Point3(3+z*q+2*Math.Cos(a)*q,-1+z*q-2*Math.Cos(a)*q,5+2*Math.Sin(a)); } }
  using(var c=PointCloud.FromPoints(cylinder,u,2)) { if(Math.Abs(c.FitCylinder(1e-5).Radius-2)>1e-4) throw new Exception("cylinder"); }
  var src=new[]{new Point3(0,0,0),new Point3(1,0,0),new Point3(0,1,0),new Point3(0,0,1)};
  var dst=Array.ConvertAll(src,p=>new Point3(2-p.Y,3+p.X,4+p.Z));
  var t=RigidTransform3.Fit(src,dst,u,8,9);
  var held=new[]{new Point3(2,3,4),new Point3(-1,2,5)};
  var truth=Array.ConvertAll(held,p=>new Point3(2-p.Y,3+p.X,4+p.Z));
  if(t.Evaluate(held,truth).MaxError>1e-8) throw new Exception("registration");
  using(var c=PointCloud.FromPoints(new Point3?[]{held[0],held[1],null},u,8)) using(var moved=c.Transform(t)) { if(moved.Info.Frame!=9 || moved.ToPoints()[2]!=null) throw new Exception("transform"); }
  Console.WriteLine("spatial examples passed");
 }
}
