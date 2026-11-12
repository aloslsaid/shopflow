import pytest
from fastapi import HTTPException

from security import Ctx, need


def test_unknown_signed_role_is_rejected_with_forbidden():
    dependency = need("owner")
    with pytest.raises(HTTPException) as caught:
        dependency(Ctx(uid=1, sid=1, role="unknown"))
    assert caught.value.status_code == 403


def test_unknown_required_role_is_rejected_with_forbidden():
    dependency = need("not-a-role")
    with pytest.raises(HTTPException) as caught:
        dependency(Ctx(uid=1, sid=1, role="owner"))
    assert caught.value.status_code == 403
