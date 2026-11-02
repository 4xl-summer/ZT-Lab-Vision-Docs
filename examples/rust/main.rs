use zvision_core::{ZImage, ZRect, ZResult};
use zvision_ops::threshold_image;
use zvision_query::ImageQuery;

fn main() -> ZResult<()> {
    let image = ZImage::from_vec_gray8(3, 2, vec![9, 0, 128, 9, 127, 255])?;
    let roi = image.roi(ZRect::new(1, 0, 2, 2))?;
    drop(image); // ROI shares ownership of the pixel storage.
    let direct = threshold_image(&roi, 128.0)?;
    assert_eq!(direct.row(0)?, &[0, 255]);
    assert_eq!(direct.row(1)?, &[0, 255]);
    let plan = ImageQuery::new(&roi)?.threshold(128)?;
    drop(roi); // The plan owns a shared source.
    let result = plan.run()?;
    assert_eq!(result.output.row(0)?, &[0, 255]);
    assert_eq!(result.output.row(1)?, &[0, 255]);
    println!("0 255 / 0 255");
    Ok(())
}
