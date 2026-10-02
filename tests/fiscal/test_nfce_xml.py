"""Validação de XML de NFC-e. Todos os XMLs são FICTÍCIOS (veja test_data/nfce/)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from lxml import etree

from src.utils.xml_validator import NFE_NS, NFCeValidator, XmlParseError

pytestmark = [pytest.mark.fiscal, pytest.mark.regression]

VALID_KEY = "41261011222333000181650010000012341876543210"


# --------------------------------------------------------------------------- helpers

def _xpath(path: str) -> str:
    """'ide/nNF' -> '//n:ide/n:nNF' (atributos como '@Id' ficam sem prefixo)."""
    return "//" + "/".join(s if s.startswith("@") else f"n:{s}" for s in path.split("/"))


def mutate(xml: bytes, path: str, value: str | None) -> NFCeValidator:
    """Altera o texto (ou atributo) em `path`; value=None remove o elemento/atributo."""
    root = etree.fromstring(xml)
    node = root.xpath(_xpath(path), namespaces=NFE_NS)[0]
    if isinstance(node, str):  # atributo
        if value is None:
            del node.getparent().attrib[node.attrname]
        else:
            node.getparent().set(node.attrname, value)
    elif value is None:
        node.getparent().remove(node)
    else:
        node.text = value
    return NFCeValidator(root)


@pytest.fixture(scope="module")
def valid_xml(nfce_dir) -> bytes:
    return (nfce_dir / "valid_nfce.xml").read_bytes()


@pytest.fixture(scope="module")
def valid_doc(nfce_dir) -> NFCeValidator:
    return NFCeValidator.from_file(nfce_dir / "valid_nfce.xml")


@pytest.fixture(scope="module")
def invalid_doc(nfce_dir) -> NFCeValidator:
    return NFCeValidator.from_file(nfce_dir / "invalid_nfce.xml")


# --------------------------------------------------------------------------- XML bem formado

@pytest.mark.smoke
def test_valid_file_is_well_formed(nfce_dir):
    assert NFCeValidator.from_file(nfce_dir / "valid_nfce.xml") is not None


def test_invalid_file_is_still_well_formed(nfce_dir):
    assert NFCeValidator.from_file(nfce_dir / "invalid_nfce.xml") is not None


@pytest.mark.parametrize(
    "content",
    [b"", b"isto nao e xml", b"<NFe><infNFe></NFe>", b"<NFe>&entidade_indefinida;</NFe>"],
    ids=["empty", "plain_text", "unclosed_tag", "undefined_entity"],
)
def test_malformed_xml_is_rejected(content):
    with pytest.raises(XmlParseError):
        NFCeValidator.from_bytes(content)


def test_document_without_nfe_namespace_has_structural_error():
    report = NFCeValidator.from_bytes(b"<NFe><infNFe Id='NFe1'/></NFe>").validate()

    assert report.has("MISSING_ELEMENT", "infNFe")


# --------------------------------------------------------------------------- validação estrutural

def test_valid_file_has_no_structural_issues(valid_doc):
    assert valid_doc.validate_structure() == []


@pytest.mark.parametrize(
    "path, location",
    [
        ("infNFe/@Id", "infNFe/@Id"),
        ("ide/mod", "ide/mod"),
        ("ide/serie", "ide/serie"),
        ("ide/nNF", "ide/nNF"),
        ("ide/dhEmi", "ide/dhEmi"),
        ("emit/CNPJ", "emit/CNPJ"),
        ("total/ICMSTot/vProd", "total/ICMSTot/vProd"),
        ("total/ICMSTot/vNF", "total/ICMSTot/vNF"),
        ("det[1]/prod/cProd", "det[1]/prod/cProd"),
        ("det[1]/prod/xProd", "det[1]/prod/xProd"),
        ("det[1]/prod/NCM", "det[1]/prod/NCM"),
        ("det[1]/prod/CFOP", "det[1]/prod/CFOP"),
        ("det[1]/prod/uCom", "det[1]/prod/uCom"),
        ("det[1]/prod/qCom", "det[1]/prod/qCom"),
        ("det[1]/prod/vUnCom", "det[1]/prod/vUnCom"),
        ("det[1]/prod/vProd", "det[1]/prod/vProd"),
        ("det[2]/imposto/ICMS", "det[2]/imposto/ICMS"),
        ("det[2]/imposto/PIS", "det[2]/imposto/PIS"),
        ("det[2]/imposto/COFINS", "det[2]/imposto/COFINS"),
        ("det[3]/imposto/ICMS/ICMS00/CST", "det[3]/imposto/ICMS/CST|CSOSN"),
        ("det[3]/imposto/PIS/PISAliq/CST", "det[3]/imposto/PIS/CST"),
        ("det[3]/imposto/COFINS/COFINSAliq/CST", "det[3]/imposto/COFINS/CST"),
    ],
)
def test_missing_required_element_is_reported(valid_xml, path, location):
    report = mutate(valid_xml, path, None).validate()

    assert report.has("MISSING_ELEMENT", location), report.describe()


def test_document_without_items_is_reported(valid_xml):
    root = etree.fromstring(valid_xml)
    for det in root.xpath("//n:det", namespaces=NFE_NS):
        det.getparent().remove(det)

    assert NFCeValidator(root).validate().has("MISSING_ELEMENT", "det")


def test_empty_element_counts_as_missing(valid_xml):
    assert mutate(valid_xml, "emit/CNPJ", "  ").validate().has("MISSING_ELEMENT", "emit/CNPJ")


# --------------------------------------------------------------------------- validação de dados

@pytest.mark.smoke
def test_valid_file_has_no_data_issues(valid_doc):
    assert valid_doc.validate_data() == []


def test_access_key_is_present_and_valid(valid_doc):
    assert valid_doc.access_key == VALID_KEY
    assert len(valid_doc.access_key) == 44


def test_emitter_cnpj_is_present(valid_doc):
    assert valid_doc.emitter_cnpj == "11222333000181"


def test_number_and_series(valid_doc):
    assert (valid_doc.number, valid_doc.series) == ("1234", "1")


def test_issue_date_has_timezone(valid_doc):
    expected = datetime(2026, 10, 2, 14, 35, 10, tzinfo=timezone(timedelta(hours=-3)))
    assert valid_doc.issue_date == expected


def test_total_value(valid_doc):
    assert valid_doc.total_value == Decimal("84.76")


@pytest.mark.parametrize(
    "index, code, name, ncm, cfop, quantity, unit_value, total",
    [
        (0, "1001", "Arroz 5kg", "10063021", "5102", "2.0000", "25.9000", "51.80"),
        (1, "1002", "Feijão Carioca 1kg", "07133319", "5102", "3.0000", "8.4900", "25.47"),
        (2, "1003", "Açúcar Refinado a Granel", "17019900", "5102", "1.5000", "4.9900", "7.49"),
    ],
    ids=["arroz", "feijao", "acucar"],
)
def test_items_are_parsed(valid_doc, index, code, name, ncm, cfop, quantity, unit_value, total):
    item = valid_doc.items[index]

    assert (item.code, item.description, item.ncm, item.cfop) == (code, name, ncm, cfop)
    assert (item.quantity, item.unit_value, item.total_value) == (Decimal(quantity), Decimal(unit_value), Decimal(total))


def test_items_have_icms_pis_and_cofins_codes(valid_doc):
    assert len(valid_doc.items) == 3
    for item in valid_doc.items:
        assert (item.icms_cst, item.pis_cst, item.cofins_cst) == ("00", "01", "01")


def test_csosn_is_accepted_in_place_of_cst(valid_xml):
    root = etree.fromstring(valid_xml)
    icms = root.xpath("//n:det[3]/n:imposto/n:ICMS", namespaces=NFE_NS)[0]
    for child in list(icms):
        icms.remove(child)
    group = etree.SubElement(icms, f"{{{NFE_NS['n']}}}ICMSSN102")
    etree.SubElement(group, f"{{{NFE_NS['n']}}}orig").text = "0"
    etree.SubElement(group, f"{{{NFE_NS['n']}}}CSOSN").text = "102"
    doc = NFCeValidator(root)

    assert doc.items[2].icms_cst == "102"
    assert doc.validate().ok, doc.validate().describe()


@pytest.mark.parametrize(
    "path, value, code, location",
    [
        ("@Id", "NFe41261011222333000181650010000012341876543215", "INVALID_ACCESS_KEY", "infNFe/@Id"),
        ("@Id", "NFe123", "INVALID_ACCESS_KEY", "infNFe/@Id"),
        ("@Id", "NFeABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQ", "INVALID_ACCESS_KEY", "infNFe/@Id"),
        ("emit/CNPJ", "11222333000182", "INVALID_CNPJ", "emit/CNPJ"),
        ("emit/CNPJ", "123", "INVALID_CNPJ", "emit/CNPJ"),
        ("emit/CNPJ", "11111111111111", "INVALID_CNPJ", "emit/CNPJ"),
        ("ide/mod", "55", "INVALID_MODEL", "ide/mod"),
        ("ide/serie", "ABC", "INVALID_FORMAT", "ide/serie"),
        ("ide/serie", "1234", "INVALID_FORMAT", "ide/serie"),
        ("ide/nNF", "0", "INVALID_FORMAT", "ide/nNF"),
        ("ide/nNF", "abc", "INVALID_FORMAT", "ide/nNF"),
        ("ide/nNF", "1234567890", "INVALID_FORMAT", "ide/nNF"),
        ("ide/dhEmi", "2026-10-02T14:35:10", "INVALID_DATE", "ide/dhEmi"),
        ("ide/dhEmi", "02/10/2026", "INVALID_DATE", "ide/dhEmi"),
        ("total/ICMSTot/vNF", "0", "INVALID_VALUE", "total/ICMSTot/vNF"),
        ("total/ICMSTot/vNF", "-84.76", "INVALID_VALUE", "total/ICMSTot/vNF"),
        ("total/ICMSTot/vNF", "abc", "INVALID_VALUE", "total/ICMSTot/vNF"),
        ("det[1]/prod/qCom", "0", "INVALID_VALUE", "det[1]/prod/qCom"),
        ("det[1]/prod/qCom", "-2", "INVALID_VALUE", "det[1]/prod/qCom"),
        ("det[1]/prod/vUnCom", "abc", "INVALID_VALUE", "det[1]/prod/vUnCom"),
        ("det[1]/prod/vUnCom", "NaN", "INVALID_VALUE", "det[1]/prod/vUnCom"),
        ("det[1]/prod/vProd", "0", "INVALID_VALUE", "det[1]/prod/vProd"),
        ("det[1]/prod/NCM", "123", "INVALID_FORMAT", "det[1]/prod/NCM"),
        ("det[1]/prod/NCM", "1006302A", "INVALID_FORMAT", "det[1]/prod/NCM"),
        ("det[1]/prod/CFOP", "51", "INVALID_FORMAT", "det[1]/prod/CFOP"),
        ("det[1]/prod/CFOP", "ABCD", "INVALID_FORMAT", "det[1]/prod/CFOP"),
        ("det[1]/imposto/ICMS/ICMS00/CST", "0", "INVALID_FORMAT", "det[1]/imposto/ICMS"),
        ("det[1]/imposto/PIS/PISAliq/CST", "1", "INVALID_FORMAT", "det[1]/imposto/PIS"),
        ("det[1]/imposto/COFINS/COFINSAliq/CST", "AB", "INVALID_FORMAT", "det[1]/imposto/COFINS"),
        ("det[1]/imposto/ICMS/ICMS00/vICMS", "-1", "INVALID_VALUE", "det[1]/imposto/ICMS/vICMS"),
        ("det[1]/imposto/PIS/PISAliq/vPIS", "abc", "INVALID_VALUE", "det[1]/imposto/PIS/vPIS"),
        ("det[1]/imposto/COFINS/COFINSAliq/vCOFINS", "-0.5", "INVALID_VALUE", "det[1]/imposto/COFINS/vCOFINS"),
    ],
)
def test_invalid_data_is_reported(valid_xml, path, value, code, location):
    report = mutate(valid_xml, path, value).validate()

    assert report.has(code, location), report.describe()


# --------------------------------------------------------------------------- consistência

@pytest.mark.smoke
def test_valid_file_has_no_consistency_issues(valid_doc):
    assert valid_doc.validate_consistency() == []


def test_unit_value_times_quantity_accepts_rounding(valid_doc):
    # 1.5 x 4.99 = 7.485 e a nota informa 7.49: diferença de arredondamento tolerada
    item = valid_doc.items[2]
    assert item.quantity * item.unit_value == Decimal("7.4850")
    assert not valid_doc.validate().has("ITEM_TOTAL_MISMATCH")


def test_item_total_within_tolerance_is_accepted(valid_xml):
    report = mutate(valid_xml, "det[1]/prod/vProd", "51.81").validate()

    assert not report.has("ITEM_TOTAL_MISMATCH")


def test_item_total_beyond_tolerance_is_rejected(valid_xml):
    report = mutate(valid_xml, "det[1]/prod/vProd", "51.82").validate()

    assert report.has("ITEM_TOTAL_MISMATCH", "det[1]/prod/vProd")


def test_sum_of_items_must_match_products_total(valid_xml):
    report = mutate(valid_xml, "total/ICMSTot/vProd", "90.00").validate()

    assert report.has("PRODUCTS_TOTAL_MISMATCH", "total/ICMSTot/vProd")


def test_note_total_must_match_products_minus_discount(valid_xml):
    report = mutate(valid_xml, "total/ICMSTot/vNF", "99.99").validate()

    assert report.has("NOTE_TOTAL_MISMATCH", "total/ICMSTot/vNF")


def test_discount_is_considered_in_note_total(valid_xml):
    doc = mutate(valid_xml, "total/ICMSTot/vDesc", "5.00")
    assert doc.validate().has("NOTE_TOTAL_MISMATCH")

    root = etree.fromstring(valid_xml)
    root.xpath("//n:ICMSTot/n:vDesc", namespaces=NFE_NS)[0].text = "5.00"
    root.xpath("//n:ICMSTot/n:vNF", namespaces=NFE_NS)[0].text = "79.76"
    assert not NFCeValidator(root).validate().has("NOTE_TOTAL_MISMATCH")


@pytest.mark.parametrize(
    "path, value, location",
    [
        ("ide/nNF", "1235", "ide/nNF"),
        ("ide/serie", "2", "ide/serie"),
        ("ide/mod", "55", "ide/mod"),
        ("emit/CNPJ", "11444777000161", "emit/CNPJ"),  # CNPJ válido, mas diferente do da chave
        ("ide/dhEmi", "2026-11-02T14:35:10-03:00", "ide/dhEmi"),  # mês diferente do AAMM da chave
    ],
)
def test_access_key_must_match_note_fields(valid_xml, path, value, location):
    report = mutate(valid_xml, path, value).validate()

    assert report.has("ACCESS_KEY_MISMATCH", location), report.describe()


@pytest.mark.parametrize(
    "path, value, location",
    [
        ("det[1]/imposto/ICMS/ICMS00/vICMS", "9.40", "det[1]/imposto/ICMS/vICMS"),
        ("det[2]/imposto/PIS/PISAliq/vPIS", "0.50", "det[2]/imposto/PIS/vPIS"),
        ("det[3]/imposto/COFINS/COFINSAliq/vCOFINS", "2.00", "det[3]/imposto/COFINS/vCOFINS"),
    ],
)
def test_tax_amount_must_match_base_times_rate(valid_xml, path, value, location):
    report = mutate(valid_xml, path, value).validate()

    assert report.has("TAX_AMOUNT_MISMATCH", location), report.describe()


# --------------------------------------------------------------------------- documentos completos

@pytest.mark.smoke
def test_valid_nfce_passes_all_validations(valid_doc):
    report = valid_doc.validate()

    assert report.ok, report.describe()


@pytest.mark.smoke
def test_invalid_nfce_fails_validation(invalid_doc):
    assert not invalid_doc.validate().ok


@pytest.mark.parametrize(
    "code, location",
    [
        ("INVALID_ACCESS_KEY", "infNFe/@Id"),
        ("INVALID_CNPJ", "emit/CNPJ"),
        ("ACCESS_KEY_MISMATCH", "ide/nNF"),
        ("INVALID_DATE", "ide/dhEmi"),
        ("INVALID_FORMAT", "det[1]/prod/CFOP"),
        ("MISSING_ELEMENT", "det[2]/prod/NCM"),
        ("MISSING_ELEMENT", "det[2]/imposto/PIS/CST"),
        ("ITEM_TOTAL_MISMATCH", "det[3]/prod/vProd"),
        ("MISSING_ELEMENT", "det[3]/imposto/COFINS"),
        ("PRODUCTS_TOTAL_MISMATCH", "total/ICMSTot/vProd"),
        ("NOTE_TOTAL_MISMATCH", "total/ICMSTot/vNF"),
    ],
)
def test_invalid_nfce_reports_each_known_defect(invalid_doc, code, location):
    report = invalid_doc.validate()

    assert report.has(code, location), report.describe()


def test_invalid_nfce_has_issues_in_every_layer(invalid_doc):
    report = invalid_doc.validate()

    for layer in ("structural", "data", "consistency"):
        assert report.by_layer(layer), f"nenhum problema na camada {layer}"
