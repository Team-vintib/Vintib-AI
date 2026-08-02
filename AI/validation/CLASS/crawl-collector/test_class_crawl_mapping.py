"""카테고리 매핑 엔진·색상 힌트·스펙 검증의 순수 로직 테스트.

네트워크 I/O 없음, 무거운 의존성 없음 — `fetcher`/`parser`/`downloader`(httpx·selectolax·
playwright)는 여기서 건드리지 않으므로 CI(`requirements-dev.txt`만 설치)에서 그대로 돈다.

여기서 고정하려는 것은 **매핑 규칙이 실제로 어려운 케이스를 맞히는가**다. 규칙을 늘리다 보면
"후드집업이 후드로 떨어지는" 류의 회귀가 조용히 생기는데, 그건 라벨 오염이라 학습셋 전체를
버리게 된다.
"""

from __future__ import annotations

import pytest
from color_hint import extract_color_hints, is_color_ambiguous
from labels import ALL_SUBCATEGORIES, is_valid_subcategory
from mapping import map_category, match_text, normalize, split_alternatives, split_path
from site_spec import SpecError, spec_from_dict


class TestNormalize:
    def test_strips_separators_and_case(self):
        assert normalize("아우터 > Zip-Up 후드!") == "아우터zipup후드"

    def test_fullwidth_is_folded(self):
        assert normalize("ＴＯＰ") == "top"

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("아우터 > 자켓 > 블루종", ["아우터", "자켓", "블루종"]),
            ("홈 >> 가방 | 백팩", ["홈", "가방", "백팩"]),
            # "/"는 계층이 아니라 병렬 나열로 본다 — split_alternatives의 몫.
            ("상의/니트", ["상의/니트"]),
        ],
    )
    def test_split_path(self, raw, expected):
        assert split_path(raw) == expected

    def test_split_alternatives(self):
        assert split_alternatives("숄더백/토트백") == ["숄더백", "토트백"]
        assert split_alternatives("니트") == ["니트"]


class TestLongestKeywordWins:
    """규칙 나열 순서가 아니라 키워드 길이로 이겨야 한다."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("후드집업", "HOODIE_ZIP_UP"),
            ("후드 집업", "HOODIE_ZIP_UP"),
            ("후드티", "HOODIE"),
            ("티셔츠", "T_SHIRT"),
            ("셔츠", "SHIRT"),
            ("스웨트셔츠", "SWEATSHIRT"),
            ("맨투맨", "SWEATSHIRT"),
            ("스웨터", "KNIT"),
        ],
    )
    def test_confusable_terms(self, text, expected):
        assert match_text(text).subcategory_code == expected


class TestExclusions:
    def test_denim_jacket_is_not_denim(self):
        result = match_text("데님 자켓")
        assert result.subcategory_code == "JACKET"

    def test_denim_skirt_is_skirt(self):
        assert match_text("데님 스커트").subcategory_code == "SKIRT"

    def test_best_seller_nav_is_not_vest(self):
        """쇼핑몰 네비게이션의 '베스트상품'이 조끼(VEST)로 들어가면 라벨이 오염된다."""
        assert match_text("베스트상품").subcategory_code != "VEST"

    def test_real_vest_still_maps(self):
        assert match_text("아우터 > 베스트").subcategory_code == "VEST"


class TestAmbiguousGoesToReview:
    def test_bare_pants_is_review(self):
        result = match_text("하의 > 팬츠")
        assert result.subcategory_code == "SLACKS"
        assert result.status == "needs_review"
        assert result.needs_human

    def test_suit_jacket_is_review(self):
        """브리핑 §5.4 예시 — 정장 자켓은 사진을 봐야 정해진다."""
        result = match_text("정장 자켓")
        assert result.status == "needs_review"

    def test_knit_vest_resolves_to_vest_by_exclusion(self):
        """'니트 베스트'는 소재(니트)가 아니라 아이템 형태(베스트)가 이겨야 한다."""
        assert match_text("니트베스트").subcategory_code == "VEST"

    @pytest.mark.parametrize(
        "raw", ["가방 > 숄더백/토트백", "상의 > 니트/맨투맨", "아우터 > 자켓/코트"]
    )
    def test_merged_site_category_is_review(self, raw):
        """사이트가 우리보다 뭉뚱그린 1:N 카테고리(브리핑 §5.2)는 자동 확정하지 않는다."""
        result = map_category(raw)
        assert result.status == "needs_review"
        assert result.runner_up_code is not None

    def test_alternatives_converging_to_one_code_are_mapped(self):
        """ "/"를 계층·동의어로 쓰는 사이트까지 검수로 보내면 검수량만 늘어난다."""
        assert map_category("상의 > 니트/스웨터").status == "mapped"
        assert map_category("상의/니트").subcategory_code == "KNIT"


class TestUnmappedIsPreserved:
    """우리 taxonomy에 없는 카테고리를 비슷한 코드에 욱여넣지 않는다(브리핑 §5.5)."""

    @pytest.mark.parametrize("text", ["원피스", "여성 > 드레스", "잡화 > 양말", "안경"])
    def test_out_of_taxonomy_is_unmapped(self, text):
        result = map_category(text)
        assert result.subcategory_code is None
        assert result.status == "unmapped"


class TestMapCategory:
    def test_site_table_exact_match_wins(self):
        result = map_category(
            "상의 > 니트/스웨터",
            site_table={"상의 > 니트/스웨터": "SWEATSHIRT"},
        )
        assert result.subcategory_code == "SWEATSHIRT"  # 규칙이라면 KNIT였을 텍스트
        assert result.method == "site_table"
        assert result.confidence == 1.0

    def test_site_table_ignores_spacing_differences(self):
        result = map_category("아우터>자켓", site_table={"아우터 > 자켓": "JACKET"})
        assert result.method == "site_table"

    def test_deepest_segment_wins(self):
        """'아우터'(대분류)가 아니라 '블루종'(소분류)으로 매핑돼야 한다."""
        result = map_category("홈 > 아우터 > 자켓 > 블루종")
        assert result.subcategory_code == "JACKET"
        assert result.matched_text == "블루종"

    def test_falls_back_to_product_name(self):
        result = map_category("전체상품", product_name="오버핏 트렌치 코트 베이지")
        assert result.subcategory_code == "COAT"
        assert "상품명" in result.reason

    def test_product_name_fallback_is_penalized(self):
        from_category = map_category("아우터 > 코트")
        from_name = map_category("전체상품", product_name="트렌치 코트")
        assert from_name.confidence < from_category.confidence

    def test_empty_category_without_name_is_unmapped(self):
        assert map_category("").status == "unmapped"


class TestRulesCoverTaxonomy:
    def test_every_subcategory_has_a_rule(self):
        """30종 중 하나라도 규칙이 없으면 그 코드는 영원히 수집되지 않는다."""
        from mapping_rules import RULES

        covered = {rule.code for rule in RULES}
        assert covered == set(ALL_SUBCATEGORIES)

    def test_all_rule_codes_are_valid(self):
        from mapping_rules import RULES

        assert all(is_valid_subcategory(rule.code) for rule in RULES)


class TestColorHints:
    def test_extracts_palette_candidates(self):
        assert extract_color_hints("오버핏 블랙 니트") == ["BLACK"]

    def test_charcoal_maps_to_gray(self):
        assert extract_color_hints("차콜 맨투맨") == ["GRAY"]

    def test_multiple_options_are_all_kept(self):
        hints = extract_color_hints("[3color] 니트 (블랙/아이보리)")
        assert set(hints) == {"BLACK", "IVORY"}

    def test_pattern_adds_multi(self):
        assert "MULTI" in extract_color_hints("체크 셔츠")

    def test_ambiguous_when_multiple_or_option_marker(self):
        assert is_color_ambiguous(["BLACK", "IVORY"], "니트")
        assert is_color_ambiguous(["BLACK"], "[3COLOR] 니트")
        assert not is_color_ambiguous(["BLACK"], "블랙 니트")

    def test_no_color_word_gives_empty(self):
        assert extract_color_hints("베이직 티셔츠") == []


class TestSiteSpec:
    def _minimal(self, **overrides):
        data = {
            "site": "m",
            "follow_detail": False,
            "listing": {
                "item_selector": "li",
                "image_selector": "img",
                "category": "아우터 > 코트",
            },
        }
        data.update(overrides)
        return data

    def test_minimal_listing_only_spec(self):
        spec = spec_from_dict(self._minimal())
        assert spec.site == "m"
        assert spec.listing is not None

    def test_unknown_top_level_key_raises(self):
        with pytest.raises(SpecError, match="모르는 키"):
            spec_from_dict(self._minimal(rendor="static"))

    def test_unknown_listing_key_raises(self):
        data = self._minimal()
        data["listing"]["item_selectors"] = "li"
        with pytest.raises(SpecError, match="모르는 키"):
            spec_from_dict(data)

    def test_bad_subcategory_code_in_map_raises(self):
        with pytest.raises(SpecError, match="taxonomy에 없는"):
            spec_from_dict(self._minimal(category_map={"아우터": "OUTERWEAR"}))

    def test_follow_detail_requires_detail_section(self):
        data = self._minimal(follow_detail=True)
        data["listing"]["link_selector"] = "a"
        with pytest.raises(SpecError, match="detail"):
            spec_from_dict(data)

    def test_listing_only_requires_category_source(self):
        data = self._minimal()
        del data["listing"]["category"]
        with pytest.raises(SpecError, match="카테고리"):
            spec_from_dict(data)

    def test_category_urls_satisfies_category_requirement(self):
        """카테고리가 URL로만 구분되는 사이트(번개장터 등)의 기본 구성."""
        data = self._minimal()
        del data["listing"]["category"]
        data["listing"]["category_urls"] = [
            {"url": "https://m.example.com/categories/1", "category": "아우터 > 코트"}
        ]
        spec = spec_from_dict(data)
        assert spec.listing is not None
        assert spec.listing.category_urls[0]["category"] == "아우터 > 코트"

    def test_category_urls_entry_missing_key_raises(self):
        data = self._minimal()
        data["listing"]["category_urls"] = [{"url": "https://m.example.com/c/1"}]
        with pytest.raises(SpecError, match="category_urls"):
            spec_from_dict(data)

    def test_invalid_shot_type_raises(self):
        with pytest.raises(SpecError, match="shot_type_default"):
            spec_from_dict(self._minimal(shot_type_default="studio"))

    def test_invalid_render_raises(self):
        with pytest.raises(SpecError, match="render"):
            spec_from_dict(self._minimal(render="selenium"))
