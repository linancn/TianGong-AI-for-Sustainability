from __future__ import annotations

from tiangong_ai_for_sustainability.adapters.api.kaggle import KaggleAdapter, KaggleAPIError


def test_kaggle_adapter_verify_success():
    class DummyClient:
        def __init__(self):
            self.calls = []

        def dataset_view(self, dataset_ref: str):
            self.calls.append(dataset_ref)
            assert dataset_ref == "zynicide/wine-reviews"
            return {"ref": dataset_ref, "title": "Wine Reviews"}

    adapter = KaggleAdapter(client=DummyClient())

    result = adapter.verify()

    assert result.success is True
    assert result.details["dataset"] == "zynicide/wine-reviews"
    assert result.details["title"] == "Wine Reviews"


def test_kaggle_adapter_verify_failure():
    class FailingClient:
        def dataset_view(self, dataset_ref: str):
            raise KaggleAPIError("authentication failed")

    adapter = KaggleAdapter(client=FailingClient())

    result = adapter.verify()

    assert result.success is False
    assert "authentication failed" in result.message
