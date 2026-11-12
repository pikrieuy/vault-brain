import pytest
from vaultbrain.ontology import (
    validate_triple,
    ValidationError,
    ENTITY_TYPES,
    RELATION_TYPES,
    Triple,
)

def test_ontology_constants():
    assert "NOTE" in ENTITY_TYPES
    assert "CONCEPT" in ENTITY_TYPES
    assert "PROJECT" in ENTITY_TYPES
    assert "TOOL" in ENTITY_TYPES
    assert "PERSON" in ENTITY_TYPES

    assert "DEPENDS_ON" in RELATION_TYPES
    assert "IMPLEMENTS" in RELATION_TYPES
    assert "RELATES_TO" in RELATION_TYPES
    assert "PART_OF" in RELATION_TYPES
    assert "OWNS" in RELATION_TYPES
    assert "MENTIONED_IN" in RELATION_TYPES

def test_valid_triples():
    t1 = Triple(
        src="Beemate",
        src_type="PROJECT",
        rel="DEPENDS_ON",
        dst="FastAPI",
        dst_type="TOOL",
        confidence=1.0,
        evidence="Beemate depends on FastAPI"
    )
    assert validate_triple(t1) is True

    t2 = Triple(
        src="Pikri",
        src_type="PERSON",
        rel="OWNS",
        dst="Beemate",
        dst_type="PROJECT",
        confidence=1.0
    )
    assert validate_triple(t2) is True

def test_invalid_relation_type():
    t = Triple(
        src="Beemate",
        src_type="PROJECT",
        rel="LOVES",  # Not in allowed relations
        dst="FastAPI",
        dst_type="TOOL"
    )
    with pytest.raises(ValidationError, match="Invalid relation"):
        validate_triple(t)

def test_invalid_entity_type():
    t = Triple(
        src="Beemate",
        src_type="UNKNOWN_TYPE",
        rel="DEPENDS_ON",
        dst="FastAPI",
        dst_type="TOOL"
    )
    with pytest.raises(ValidationError, match="Invalid entity type"):
        validate_triple(t)

def test_invalid_edge_signature():
    # PERSON cannot DEPEND_ON TOOL according to strict schema
    t = Triple(
        src="Pikri",
        src_type="PERSON",
        rel="DEPENDS_ON",
        dst="FastAPI",
        dst_type="TOOL"
    )
    with pytest.raises(ValidationError, match="Invalid edge signature"):
        validate_triple(t)
