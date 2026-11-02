from zvision import (ZImage, MatchModel, MatchSpec, AlignmentSpec, DifferenceSpec,
                     DefectSpec, DecisionSpec, Interpolation)

pattern = bytes([0, 13, 29, 61])
search = MatchSpec(0, 0, 1, 1, 1, 1, .999, 0, 1)
with ZImage.from_gray8(2, 2, pattern) as image:
    with MatchModel.train_ncc(image) as model, image.find_matches(model, search) as matches:
        assert len(matches.matches) == 1
        print("match", matches.matches[0])
    with image.align_reference(image, AlignmentSpec((0, 0, 2, 2), search, Interpolation.NEAREST)) as alignment:
        assert alignment.found and alignment.valid_count == 4
        with alignment.aligned as aligned, alignment.valid_mask as valid:
            with aligned.inspection_difference(image, valid, DifferenceSpec(1)) as difference:
                assert difference.max_score == 0
                with difference.mask as mask, difference.score as score:
                    with mask.surface_defects(score, DefectSpec()) as defects:
                        with defects.judge(DecisionSpec(0, 0, 0, (0, 0, 2, 2))) as decision:
                            assert decision.passed and not decision.rejections
                            print("decision", decision.info)
