use zvision::{Connectivity, ZImage, ZRect, ZResult};

fn main() -> ZResult<()> {
    let source = ZImage::from_vec_gray8(3, 1, vec![9, 10, 11])?;
    assert_eq!(source.threshold(10.0)?.to_packed_vec()?, vec![0, 255, 255]);
    let float = ZImage::from_vec_grayf32(3, 1, vec![9.0, 10.0, 11.0])?;
    assert_eq!(float.threshold(10.0)?.to_packed_vec()?, vec![0, 255, 255]);
    assert!(ZImage::from_vec_grayf32(1, 1, vec![f32::NAN])?.threshold(10.0).is_err());
    assert!(ZImage::new_rgb8(1, 1, [0, 0, 0])?.threshold(10.0).is_err());
    println!("{{\"case\":\"rust-threshold\",\"mask\":[0,255,255],\"nan_error\":true,\"color_error\":true}}");

    let roi = source.roi(ZRect::new(1, 0, 2, 1))?;
    let share = roi.share();
    let deep = roi.clone_deep()?;
    assert!(roi.shares_storage_with(&source));
    assert!(share.shares_storage_with(&source));
    assert!(!deep.shares_storage_with(&source));
    assert_eq!(roi.origin(), (1, 0));
    let base = roi.query()?;
    let lower = base.clone().threshold(10)?.execute()?;
    assert_eq!(lower.output().to_packed_vec()?, vec![255,255]);
    let plan = base.threshold(11)?.capture("mask")?;
    drop(roi); drop(source);
    let execution = plan.execute()?;
    assert_eq!(execution.output().to_packed_vec()?, vec![0,255]);
    let captured = execution.get_image("mask")?;
    drop(execution); drop(plan);
    assert_eq!(captured.to_packed_vec()?, vec![0,255]);
    println!("{{\"case\":\"rust-roi-query\",\"origin\":[1,0],\"capture\":[0,255],\"deep_independent\":true,\"clone_branch\":[255,255]}}");

    let diagonal = ZImage::from_vec_gray8(2,2,vec![255,0,0,255])?;
    let four = diagonal.query()?.find_blobs(Connectivity::Four).execute()?;
    let eight = diagonal.query()?.find_blobs(Connectivity::Eight).execute()?;
    assert_eq!(four.output().blobs().len(), 2);
    assert_eq!(eight.output().blobs().len(), 1);
    println!("{{\"case\":\"rust-blob-connectivity\",\"four\":2,\"eight\":1}}");
    more_cases()?;
    Ok(())
}


fn more_cases() -> zvision::ZResult<()> {
    use zvision::*;
    let image = ZImage::new_gray8(2, 2, 1)?;
    let spectrum = image.general_dft(2, 2, FftNormalization::Backward)?;
    for (actual, expected) in spectrum.parts().0.iter().zip([4.0, 0.0, 0.0, 0.0]) {
        assert!((actual - expected).abs() < 1e-10);
    }
    let (_, _, restored, imaginary) = spectrum.inverse_complex(true)?;
    assert!(restored.iter().all(|v| (v - 1.0).abs() < 1e-10));
    assert!(imaginary.iter().all(|v| v.abs() < 1e-10));
    println!("{{\"case\":\"rust-dft\",\"dc\":4,\"inverse\":[1,1,1,1]}}");

    let p = |x, y| Point2 { x, y };
    let pixels = [p(100.,200.),p(120.,200.),p(100.,240.),p(120.,240.)];
    let world = [p(11.,38.),p(13.,38.),p(11.,46.),p(13.,46.)];
    let cal = PlanarCalibration::fit(&pixels, &world, LengthUnit::Millimeter)?;
    let held = cal.pixel_to_world(p(110.,220.), LengthUnit::Millimeter)?;
    assert!((held.x - 12.).abs() < 1e-7 && (held.y - 42.).abs() < 1e-7);
    let report = cal.evaluate(&[p(110.,220.)], &[p(12.3,42.4)], LengthUnit::Millimeter, 0.6)?;
    assert_eq!(report.residuals().len(), 1);
    assert!((report.residuals()[0].error_world - 0.5).abs() < 1e-7);
    assert!(report.metrics().passed);
    println!("{{\"case\":\"rust-calibration-heldout\",\"predicted\":[12,42],\"world_residual\":0.5}}");

    let pt = |x,y,z| Point3 {x,y,z};
    let depth = DepthMap::new(3,2,vec![Some(1.),None,Some(3.),Some(4.),Some(5.),Some(6.)],2.,3.,pt(10.,20.,30.),LengthUnit::Millimeter,7)?;
    let roi = depth.roi(ZRect::new(1,0,2,2))?;
    assert_eq!(roi.origin(), pt(12.,20.,30.));
    let cloud = roi.to_point_cloud()?;
    assert_eq!(cloud.valid_count(), 3);
    assert_eq!(cloud.points()[1], Some(pt(14.,20.,33.)));
    let transform = RigidTransform3 {rotation:[1.,0.,0.,0.,1.,0.,0.,0.,1.], translation:pt(1.,2.,3.), unit:LengthUnit::Millimeter,from_frame:7,to_frame:8};
    let moved = cloud.transform(&transform)?;
    assert_eq!(moved.points()[1], Some(pt(15.,22.,36.)));
    let plane_points = (0..5).flat_map(|y| (0..5).map(move |x| Some(pt(x as f64,y as f64,2.*x as f64-3.*y as f64+4.)))).collect();
    let plane = PointCloud::new(plane_points, LengthUnit::Millimeter, 7)?.fit_plane(0.001)?;
    assert_eq!((plane.inliers,plane.total),(25,25));
    println!("{{\"case\":\"rust-depth-cloud\",\"roi_origin\":[12,20,30],\"point\":[14,20,33],\"transformed\":[15,22,36],\"plane_inliers\":25}}");

    let template = ZImage::from_vec_gray8(3,2,vec![3,17,1,8,2,25])?;
    let scene = ZImage::from_vec_gray8(4,2,vec![0,3,17,1,0,8,2,25])?;
    let mask = ZImage::from_vec_gray8(3,2,vec![255,255,0,255,0,255])?;
    let model = MatchModel::train_ncc(&template,Some(&mask))?;
    assert_eq!(model.info().sample_count,4);
    let spec = MatchSpec {angle_min:0.,angle_max:0.,angle_step:1.,scale_min:1.,scale_max:1.,scale_step:1.,min_score:0.99,min_distance:0.,max_matches:1};
    let found = model.find(&scene,&spec)?;
    let best = found.best().expect("fixture match");
    assert!((best.position.x-2.).abs()<1e-9 && (best.position.y-0.5).abs()<1e-9 && (best.score-1.).abs()<1e-9);
    assert!(model.find(&ZImage::new_gray8(4,2,0)?,&spec)?.best().is_none());
    let path = std::env::temp_dir().join(format!("zvision-manual-{}.zvm",std::process::id()));
    model.save(&path).expect("save model");
    let restored = MatchModel::load(&path).expect("load model");
    std::fs::remove_file(&path).expect("remove temporary model");
    assert_eq!(restored.info().sample_count,4);
    assert!((restored.find(&scene,&spec)?.best().expect("restored match").score-1.).abs()<1e-9);
    println!("{{\"case\":\"rust-matching\",\"position\":[2,0.5],\"score\":1,\"mask_samples\":4,\"empty\":true,\"restored\":true}}");

    let rgb = ZImage::new_rgb8(1,1,[255,0,0])?;
    let hsv = rgb.to_hsv()?;
    let lab = rgb.to_lab()?;
    assert_eq!(hsv.to_rgb(PixelFormat::Rgb8)?.pixel_rgb8(0,0)?, [255,0,0]);
    let rgb2 = lab.to_rgb(PixelFormat::Rgb8)?.pixel_rgb8(0,0)?;
    assert!(rgb2[0] >= 254 && rgb2[1] <= 1 && rgb2[2] <= 1);
    println!("{{\"case\":\"rust-color\",\"hsv_roundtrip\":[255,0,0],\"lab_roundtrip_tolerance\":1}}");

    let constant = ZImage::new_gray8(3,3,7)?;
    assert_eq!(constant.gaussian_blur(3,1.)?.to_packed_vec()?, vec![7;9]);
    assert!(constant.gaussian_blur(2,1.).is_err());
    println!("{{\"case\":\"rust-gaussian\",\"values\":[7,7,7,7,7,7,7,7,7],\"invalid_kernel\":true}}");
    let edges = ZImage::from_vec_gray8(2,2,vec![0,255,0,255])?;
    assert_eq!(edges.canny(3,1.,10.,20.)?.to_packed_vec()?, vec![0;4]);
    assert!(edges.canny(3,1.,20.,10.).is_err());
    println!("{{\"case\":\"rust-canny\",\"mask\":[0,0,0,0],\"invalid_thresholds\":true}}");

    let mut camera = SimulatedCamera::new(CameraSpec {source_id:1,clock_domain:2,tick_hz:1000,capacity:2,trigger_mode:TriggerMode::Software})?;
    camera.connect()?; camera.start()?; camera.trigger(1,100)?;
    assert_eq!(camera.offer_frame(&rgb,1,10,101,1)?,OfferDisposition::Accepted);
    let frame = camera.try_get_frame()?.expect("frame");
    assert_eq!(frame.info().frame_id,1);
    assert!(camera.try_get_frame()?.is_none());
    let mut plc = SimulatedPlc::new(10)?;
    assert_eq!(plc.command(PlcOperation::Request,4,0,100)?,PlcDisposition::Applied);
    assert_eq!(plc.command(PlcOperation::Publish,4,7,111)?,PlcDisposition::Applied);
    assert_eq!(plc.command(PlcOperation::Ack,4,0,113)?,PlcDisposition::Applied);
    assert_eq!(plc.info().state,PlcState::Idle);
    println!("{{\"case\":\"rust-simulated-io\",\"frame_id\":1,\"queue_empty\":true,\"plc_idle\":true}}");

    let fixtures: [(AiTask, usize, &[u8]);4] = [
        (AiTask::Classification,2,include_bytes!("models/demo-classification.rten")),
        (AiTask::Detection,1,include_bytes!("models/demo-detection.rten")),
        (AiTask::Segmentation,2,include_bytes!("models/demo-segmentation.rten")),
        (AiTask::Anomaly,1,include_bytes!("models/demo-anomaly.rten")),
    ];
    let dark = ZImage::new_gray8(8,8,0)?;
    let bright = ZImage::new_gray8(8,8,255)?;
    for (task,classes,bytes) in fixtures {
        let engine = AiEngine::from_bytes(bytes.to_vec(), AiModelSpec {task,width:8,height:8,channels:1,classes,model_version:7}).expect("fixture model");
        let result = engine.run(&dark,ZRect::new(0,0,8,8),AiRunOptions::default()).expect("fixture inference");
        match task {
            AiTask::Classification => {
                assert_eq!(result.classification().unwrap().1,0);
                assert_eq!(engine.run(&bright,ZRect::new(0,0,8,8),AiRunOptions::default()).unwrap().classification().unwrap().1,1);
            }
            AiTask::Detection => { let d = result.detections().unwrap(); assert_eq!(d.len(),1); assert_eq!((d[0].x_min,d[0].y_min,d[0].x_max,d[0].y_max,d[0].class_id),(1.,1.,6.,6.,0)); },
            AiTask::Segmentation => assert_eq!(result.acquire_map().unwrap().pixel_grayu32(0,0)?,0),
            AiTask::Anomaly => { assert_eq!(result.anomaly().unwrap().0,0.); assert!(result.acquire_map().is_some()); }
        }
    }
    println!("{{\"case\":\"rust-ai-fixtures\",\"dark_class\":0,\"bright_class\":1,\"detection\":true,\"segmentation_map\":true,\"anomaly_map\":true}}");

    let options = FontOcrOptions {threshold:100,light_text:false,closing_radius:0,min_width:1,max_width:10,min_height:1,max_height:10,split_touching:false,allowed_chars:"A".into(),position_chars:vec![],min_glyph_score:0.9,min_string_score:0.9};
    let glyph = ZImage::from_vec_gray8(3,5,vec![255,0,255,0,255,0,0,0,0,0,255,0,0,255,0])?;
    let model = FontOcrModel::train(&[FontSample {label:'A',image:glyph.share(),cell:ZRect::new(0,0,3,5)}],FontTrainingAlgorithm::NearestExample,&options).expect("train synthetic font");
    let read = model.read(&glyph,&options).expect("read synthetic font");
    assert!(read.accepted());
    assert_eq!(read.lines().next().unwrap()[0].label,'A');
    println!("{{\"case\":\"rust-font-ocr\",\"label\":\"A\",\"accepted\":true}}");

    let strip = ZImage::from_vec_gray8(7,1,vec![0,0,0,100,100,100,100])?;
    let profile = ProfileSpec {start:p(0.,0.),end:p(6.,0.),samples:7,width:1};
    let samples = strip.query()?.profile(&profile)?.execute()?;
    assert_eq!(samples.output().samples().iter().map(|v| v.value).collect::<Vec<_>>(),vec![0.,0.,0.,100.,100.,100.,100.]);
    let edge = strip.query()?.caliper(&CaliperSpec {profile,polarity:EdgePolarity::Rising,threshold:10.})?.execute()?;
    assert_eq!(edge.output().edges().len(),1);
    assert!((edge.output().edges()[0].position.x-2.5).abs()<1e-9);
    println!("{{\"case\":\"rust-profile-caliper\",\"profile\":[0,0,0,100,100,100,100],\"edge_x\":2.5}}");

    let line = LineMeasurementModel::new(p(8.,24.),p(40.,24.),0.,default_measurement_probes())?;
    let step = ZImage::from_vec_gray8(48,48,(0..48).flat_map(|y| (0..48).map(move |_| if y<24 {0} else {200})).collect())?;
    let fit = line.measure(&step)?;
    assert_eq!(fit.status(),ModelFitStatus::Fit);
    assert!((fit.fit().unwrap().point.y-23.5).abs()<0.1);
    let circle = CircleMeasurementModel::new(p(30.,30.),15.,0.,std::f64::consts::TAU,default_measurement_probes())?;
    let disk = ZImage::from_vec_gray8(61,61,(0..61).flat_map(|y| (0..61).map(move |x| if (x-30)*(x-30)+(y-30)*(y-30)<=225 {200} else {0})).collect())?;
    let cf = circle.measure(&disk)?;
    assert_eq!(cf.status(),ModelFitStatus::Fit);
    assert!((cf.fit().unwrap().center.x-30.).abs()<0.5 && (cf.fit().unwrap().center.y-30.).abs()<0.5 && (cf.fit().unwrap().radius-15.).abs()<1.0);
    println!("{{\"case\":\"rust-measurement-models\",\"line_y\":23.5,\"circle_center\":[30,30],\"circle_radius_approx\":15}}");

    let binary = ZImage::new_gray8(3,3,255)?;
    assert_eq!(binary.erode(3)?.to_packed_vec()?,vec![0,0,0,0,255,0,0,0,0]);
    println!("{{\"case\":\"rust-morphology\",\"eroded\":[0,0,0,0,255,0,0,0,0]}}");

    let reference = ZImage::from_vec_gray8(3,3,vec![4,1,7,2,9,5,8,6,3])?;
    let alignment_spec = AlignmentSpec {reference_roi:ZRect::new(0,0,3,3),search:MatchSpec {angle_min:0.,angle_max:0.,angle_step:1.,scale_min:1.,scale_max:1.,scale_step:1.,min_score:0.999,min_distance:0.,max_matches:1},interpolation:Interpolation::Nearest,min_valid_fraction:1.};
    let alignment = reference.query()?.align_reference(&reference,&alignment_spec)?.execute()?;
    let aligned = alignment.output().acquire_aligned().expect("found");
    let valid = alignment.output().acquire_valid_mask().expect("valid mask");
    assert_eq!(aligned.pixel_format(), PixelFormat::GrayF64);
    assert_eq!(aligned.to_packed_vec_grayf64()?,vec![4.,1.,7.,2.,9.,5.,8.,6.,3.]);
    assert_eq!(valid.to_packed_vec()?,vec![255;9]);
    let blank = ZImage::new_gray8(3,3,0)?;
    let missed = blank.query()?.align_reference(&reference,&alignment_spec)?.execute()?;
    assert!(missed.output().acquire_aligned().is_none());
    println!("{{\"case\":\"rust-alignment\",\"found\":true,\"valid_count\":9,\"blank_found\":false}}");

    let path = std::env::temp_dir().join(format!("zvision-manual-pages-{}.tiff",std::process::id()));
    let first = ZImage::from_vec_gray8(2,1,vec![1,2])?;
    let second = ZImage::from_vec_gray8(2,1,vec![3,4])?;
    ZImage::save_tiff_pages(&[first,second],&path,TiffSaveOptions::default()).expect("save pages");
    assert_eq!(ZImage::load_tiff_page(&path,1).expect("page 1").to_packed_vec()?,vec![3,4]);
    assert!(ZImage::load_tiff_page(&path,2).is_err());
    std::fs::remove_file(&path).expect("remove temporary TIFF");
    println!("{{\"case\":\"rust-tiff-pages\",\"page_1\":[3,4],\"page_2_error\":true}}");

    let fft = image.fft(FftOptions {width:2,height:2,normalization:FftNormalization::Backward})?;
    for (v,expected) in fft.parts().0.iter().zip([4.,0.,0.,0.]) { assert!((v-expected).abs()<1e-10); }
    assert!(fft.inverse_values(true)?.2.iter().all(|v| (v-1.).abs()<1e-10));
    println!("{{\"case\":\"rust-fft\",\"dc\":4,\"inverse\":[1,1,1,1]}}");

    // These two required option enums are provided by zvision-ops in this release.
    use zvision_ops::{DifferencePolarity,PhotometricCorrection};
    let diff = aligned.query()?.inspection_difference(&reference,Some(&valid),&DifferenceSpec {threshold:2.,correction:PhotometricCorrection::None,polarity:DifferencePolarity::Absolute,texture_kernel:1,texture_weight:0.})?.execute()?;
    assert_eq!(diff.output().acquire_mask().to_packed_vec()?,vec![0;9]);
    use zvision::bridge::Value;
    assert_eq!(diff.output().value().inspected_count,9);
    let modified_reference = ZImage::from_vec_gray8(3,3,vec![4,1,7,2,12,5,8,6,3])?;
    let changed = aligned.query()?.inspection_difference(&modified_reference,Some(&valid),&DifferenceSpec {threshold:2.,correction:PhotometricCorrection::None,polarity:DifferencePolarity::Absolute,texture_kernel:1,texture_weight:0.})?.execute()?;
    assert_eq!(changed.output().acquire_mask().to_packed_vec()?,vec![0,0,0,0,255,0,0,0,0]);
    println!("{{\"case\":\"rust-aligned-difference\",\"inspected\":9,\"defect_pixels\":1}}");
    Ok(())
}
