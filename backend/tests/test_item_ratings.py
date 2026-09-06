from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.item import ItemCreate, ItemUpdate


@pytest.mark.parametrize("score", [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0])
def test_item_scores_accept_half_star_values(score: float):
    item = ItemCreate(fit_score=score, style_score=score)

    assert item.fit_score == Decimal(str(score))
    assert item.style_score == Decimal(str(score))


@pytest.mark.parametrize("score", [0, 5.25, -1, 3.2])
def test_item_scores_reject_out_of_range_or_non_half_values(score: float):
    with pytest.raises(ValidationError):
        ItemUpdate(fit_score=score)

