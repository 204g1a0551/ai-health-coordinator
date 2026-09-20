from app.services.ddi_service import DDIService, NOT_VERIFIED_MESSAGE


def test_duplicate_normalized_medicines_are_checked_once(monkeypatch):
    service = DDIService()
    calls = []

    def normalize(name):
        return {"rxcui": "1" if "brand" in name.lower() else "2", "name": "Drug A" if "brand" in name.lower() else "Drug B"}

    def get_json(path, params):
        calls.append((path, params))
        if path == "interaction/list.json":
            return {"fullInteractionTypeGroup": [{"sourceName": "RxNorm", "fullInteractionType": [{"fullInteraction": [{"description": "Potential interaction", "severity": "moderate"}]}]}]}
        return {}

    monkeypatch.setattr(service, "normalize_medicine", normalize)
    monkeypatch.setattr(service, "_get_json", get_json)
    monkeypatch.setattr("app.services.ddi_service.list_medical_documents", lambda user_id=None: [
        {"id": "doc-1", "extracted_data": {"medicines": [{"name": "Brand A"}]}},
        {"id": "doc-2", "extracted_data": {"medicines": [{"name": "Brand A"}, {"name": "Drug B"}]}},
    ])

    result = service.check_documents()

    assert len(result.medicines) == 2
    assert len(result.interactions) == 1
    assert result.database_status == "VERIFIED"
    assert result.medicines[0].source_document_ids == ["doc-1", "doc-2"]


def test_unavailable_database_is_not_reported_as_no_interaction(monkeypatch):
    service = DDIService()
    def unavailable(path, params):
        service._source_unavailable = True
        return None

    monkeypatch.setattr(service, "_get_json", unavailable)
    monkeypatch.setattr("app.services.ddi_service.list_medical_documents", lambda user_id=None: [
        {"id": "doc-1", "extracted_data": {"medicines": [{"name": "Aspirin"}, {"name": "Warfarin"}]}},
    ])
    monkeypatch.setattr(service, "normalize_medicine", lambda name: {"rxcui": name, "name": name})

    result = service.check_documents()

    assert result.database_status == "UNAVAILABLE"
    assert result.message == NOT_VERIFIED_MESSAGE


def test_unresolved_medicine_is_explicit(monkeypatch):
    service = DDIService()
    monkeypatch.setattr(service, "normalize_medicine", lambda name: None)
    monkeypatch.setattr("app.services.ddi_service.list_medical_documents", lambda user_id=None: [
        {"id": "doc-1", "extracted_data": {"medicines": [{"name": "Unreadable name"}]}},
    ])

    result = service.check_documents()

    assert result.database_status == "NO_VERIFIED_MEDICINES"
    assert result.unresolved_medicines == ["Unreadable name"]
    assert result.message == NOT_VERIFIED_MESSAGE
