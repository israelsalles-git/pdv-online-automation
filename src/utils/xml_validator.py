"""Validação de XML de NFC-e (modelo 65) em três camadas independentes.

1. Estrutural   - os elementos esperados existem?
2. De dados     - os valores presentes têm formato/domínio válido?
3. Consistência - os valores batem entre si (qtd x unitário = total, soma dos itens = total)?

É um validador de QUALIDADE DE DADOS para testes automatizados, não substitui a validação
oficial por XSD/SEFAZ. Só regras objetivas e verificáveis são aplicadas (dígitos verificadores,
formatos, aritmética com tolerância de arredondamento).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from lxml import etree

from src.utils.logger import get_logger

log = get_logger("xml")

NFE_NS = {"n": "http://www.portalfiscal.inf.br/nfe"}
MONEY_TOLERANCE = Decimal("0.01")  # NFC-e arredonda cada valor para 2 casas

STRUCTURAL, DATA, CONSISTENCY = "structural", "data", "consistency"

# Caminhos relativos a infNFe / det.
_HEADER_REQUIRED = [
    "ide/mod", "ide/serie", "ide/nNF", "ide/dhEmi", "emit/CNPJ",
    "total/ICMSTot/vProd", "total/ICMSTot/vNF",
]
_ITEM_REQUIRED = [
    "prod/cProd", "prod/xProd", "prod/NCM", "prod/CFOP",
    "prod/uCom", "prod/qCom", "prod/vUnCom", "prod/vProd",
]
# grupo de imposto -> (tags que carregam o código de situação tributária, regra de formato)
_TAX_GROUPS = {
    "ICMS": (("CST", "CSOSN"), r"\d{2,3}"),
    "PIS": (("CST",), r"\d{2}"),
    "COFINS": (("CST",), r"\d{2}"),
}
# (grupo, tag da base, tag da alíquota, tag do valor) para a conferência base x alíquota
_TAX_AMOUNTS = [
    ("ICMS", "vBC", "pICMS", "vICMS"),
    ("PIS", "vBC", "pPIS", "vPIS"),
    ("COFINS", "vBC", "pCOFINS", "vCOFINS"),
]


class XmlParseError(ValueError):
    """O conteúdo não é um XML bem formado."""


@dataclass(frozen=True)
class ValidationIssue:
    layer: str
    code: str
    location: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues

    def by_layer(self, layer: str) -> list[ValidationIssue]:
        return [i for i in self.issues if i.layer == layer]

    def has(self, code: str, location: str | None = None) -> bool:
        return any(i.code == code and location in (None, i.location) for i in self.issues)

    def describe(self) -> str:
        return "\n".join(f"[{i.layer}] {i.code} @ {i.location}: {i.message}" for i in self.issues) or "sem problemas"


@dataclass(frozen=True)
class NFCeItem:
    number: int
    code: str | None
    description: str | None
    ncm: str | None
    cfop: str | None
    quantity: Decimal | None
    unit_value: Decimal | None
    total_value: Decimal | None
    icms_cst: str | None  # CST (regime normal) ou CSOSN (Simples Nacional)
    pis_cst: str | None
    cofins_cst: str | None


def _xp(path: str) -> str:
    return "/".join(f"n:{part}" for part in path.split("/"))


def _text(node: etree._Element | None, path: str) -> str | None:
    if node is None:
        return None
    found = node.xpath(_xp(path), namespaces=NFE_NS)
    text = found[0].text.strip() if found and found[0].text else ""
    return text or None


def _decimal(node: etree._Element | None, path: str) -> Decimal | None:
    raw = _text(node, path)
    try:
        value = Decimal(raw) if raw is not None else None
    except InvalidOperation:
        return None
    return value if value is not None and value.is_finite() else None


def _close(a: Decimal, b: Decimal, tolerance: Decimal) -> bool:
    return abs(a - b) <= tolerance


def is_valid_cnpj(cnpj: str) -> bool:
    """Valida tamanho e dígitos verificadores (módulo 11) do CNPJ."""
    if not re.fullmatch(r"\d{14}", cnpj) or len(set(cnpj)) == 1:
        return False

    def digit(base: str, weights: list[int]) -> str:
        remainder = sum(int(d) * w for d, w in zip(base, weights)) % 11
        return "0" if remainder < 2 else str(11 - remainder)

    first = digit(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = digit(cnpj[:12] + first, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return cnpj[12:] == first + second


def is_valid_access_key(key: str) -> bool:
    """44 dígitos; o último é o DV (módulo 11, pesos 2..9 da direita para a esquerda)."""
    if not re.fullmatch(r"\d{44}", key):
        return False
    total, weight = 0, 2
    for digit in reversed(key[:43]):
        total += int(digit) * weight
        weight = 2 if weight == 9 else weight + 1
    remainder = total % 11
    return key[43] == ("0" if remainder < 2 else str(11 - remainder))


class NFCeValidator:
    def __init__(self, root: etree._Element, tolerance: Decimal = MONEY_TOLERANCE) -> None:
        self._root = root
        self._tolerance = tolerance
        found = root.xpath("//n:infNFe", namespaces=NFE_NS)
        self._inf: etree._Element | None = found[0] if found else None

    # ------------------------------------------------------------------ carga

    @classmethod
    def from_bytes(cls, content: bytes, **kwargs) -> "NFCeValidator":
        # Sem resolução de entidades/rede: XML de entrada não é confiável (XXE).
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        try:
            return cls(etree.fromstring(content, parser), **kwargs)
        except etree.XMLSyntaxError as exc:
            log.error("XML mal formado: %s", exc)
            raise XmlParseError(f"XML mal formado: {exc}") from exc

    @classmethod
    def from_file(cls, path: str | Path, **kwargs) -> "NFCeValidator":
        log.info("Carregando NFC-e %s", path)
        return cls.from_bytes(Path(path).read_bytes(), **kwargs)

    # ------------------------------------------------------------------ acesso aos dados

    @property
    def access_key(self) -> str | None:
        raw = self._inf.get("Id") if self._inf is not None else None
        return raw[3:] if raw and raw.startswith("NFe") else raw

    @property
    def emitter_cnpj(self) -> str | None:
        return _text(self._inf, "emit/CNPJ")

    @property
    def number(self) -> str | None:
        return _text(self._inf, "ide/nNF")

    @property
    def series(self) -> str | None:
        return _text(self._inf, "ide/serie")

    @property
    def issue_date(self) -> datetime | None:
        raw = _text(self._inf, "ide/dhEmi")
        try:
            parsed = datetime.fromisoformat(raw) if raw else None
        except ValueError:
            return None
        return parsed if parsed and parsed.tzinfo else None  # a NF-e exige fuso horário

    @property
    def total_value(self) -> Decimal | None:
        return _decimal(self._inf, "total/ICMSTot/vNF")

    @property
    def items(self) -> list[NFCeItem]:
        return [self._build_item(i, det) for i, det in enumerate(self._dets(), 1)]

    def _dets(self) -> list[etree._Element]:
        return self._inf.xpath("n:det", namespaces=NFE_NS) if self._inf is not None else []

    @staticmethod
    def _tax_code(det: etree._Element, group: str) -> str | None:
        node = det.xpath(f"n:imposto/n:{group}/*", namespaces=NFE_NS)
        if not node:
            return None
        return next((t for tag in _TAX_GROUPS[group][0] if (t := _text(node[0], tag))), None)

    def _build_item(self, index: int, det: etree._Element) -> NFCeItem:
        return NFCeItem(
            number=index,
            code=_text(det, "prod/cProd"),
            description=_text(det, "prod/xProd"),
            ncm=_text(det, "prod/NCM"),
            cfop=_text(det, "prod/CFOP"),
            quantity=_decimal(det, "prod/qCom"),
            unit_value=_decimal(det, "prod/vUnCom"),
            total_value=_decimal(det, "prod/vProd"),
            icms_cst=self._tax_code(det, "ICMS"),
            pis_cst=self._tax_code(det, "PIS"),
            cofins_cst=self._tax_code(det, "COFINS"),
        )

    # ------------------------------------------------------------------ 1. estrutural

    def validate_structure(self) -> list[ValidationIssue]:
        if self._inf is None:
            return [ValidationIssue(STRUCTURAL, "MISSING_ELEMENT", "infNFe", "infNFe não encontrado no namespace da NF-e")]
        issues: list[ValidationIssue] = []

        def missing(location: str) -> None:
            issues.append(ValidationIssue(STRUCTURAL, "MISSING_ELEMENT", location, f"Elemento obrigatório ausente ou vazio: {location}"))

        if not self._inf.get("Id"):
            missing("infNFe/@Id")
        for path in _HEADER_REQUIRED:
            if _text(self._inf, path) is None:
                missing(path)

        dets = self._dets()
        if not dets:
            missing("det")
        for index, det in enumerate(dets, 1):
            for path in _ITEM_REQUIRED:
                if _text(det, path) is None:
                    missing(f"det[{index}]/{path}")
            for group, (code_tags, _) in _TAX_GROUPS.items():
                if not det.xpath(f"n:imposto/n:{group}/*", namespaces=NFE_NS):
                    missing(f"det[{index}]/imposto/{group}")
                elif self._tax_code(det, group) is None:
                    missing(f"det[{index}]/imposto/{group}/{'|'.join(code_tags)}")
        return issues

    # ------------------------------------------------------------------ 2. dados

    def validate_data(self) -> list[ValidationIssue]:
        if self._inf is None:
            return []
        issues: list[ValidationIssue] = []

        def invalid(code: str, location: str, message: str) -> None:
            issues.append(ValidationIssue(DATA, code, location, message))

        key = self.access_key
        if key is not None and not is_valid_access_key(key):
            invalid("INVALID_ACCESS_KEY", "infNFe/@Id", f"Chave de acesso inválida (44 dígitos + DV): {key}")
        if self.emitter_cnpj is not None and not is_valid_cnpj(self.emitter_cnpj):
            invalid("INVALID_CNPJ", "emit/CNPJ", f"CNPJ do emitente inválido: {self.emitter_cnpj}")
        if _text(self._inf, "ide/mod") not in (None, "65"):
            invalid("INVALID_MODEL", "ide/mod", "NFC-e deve ter modelo 65")
        for path, pattern in (("ide/serie", r"\d{1,3}"), ("ide/nNF", r"[1-9]\d{0,8}")):
            value = _text(self._inf, path)
            if value is not None and not re.fullmatch(pattern, value):
                invalid("INVALID_FORMAT", path, f"Valor fora do formato esperado: {value}")
        if _text(self._inf, "ide/dhEmi") is not None and self.issue_date is None:
            invalid("INVALID_DATE", "ide/dhEmi", "Data de emissão deve ser ISO 8601 com fuso horário")
        total = _decimal(self._inf, "total/ICMSTot/vNF")
        if _text(self._inf, "total/ICMSTot/vNF") is not None and (total is None or total <= 0):
            invalid("INVALID_VALUE", "total/ICMSTot/vNF", "Valor total deve ser numérico e maior que zero")

        for index, det in enumerate(self._dets(), 1):
            self._validate_item_data(index, det, invalid)
        return issues

    def _validate_item_data(self, index: int, det: etree._Element, invalid) -> None:
        for path in ("prod/qCom", "prod/vUnCom", "prod/vProd"):
            value = _decimal(det, path)
            if _text(det, path) is not None and (value is None or value <= 0):
                invalid("INVALID_VALUE", f"det[{index}]/{path}", "Deve ser numérico e maior que zero")
        for path, pattern in (("prod/NCM", r"\d{8}"), ("prod/CFOP", r"\d{4}")):
            value = _text(det, path)
            if value is not None and not re.fullmatch(pattern, value):
                invalid("INVALID_FORMAT", f"det[{index}]/{path}", f"Valor fora do formato esperado: {value}")
        for group, (_, pattern) in _TAX_GROUPS.items():
            code = self._tax_code(det, group)
            if code is not None and not re.fullmatch(pattern, code):
                invalid("INVALID_FORMAT", f"det[{index}]/imposto/{group}", f"CST/CSOSN fora do formato esperado: {code}")
        for group, _, _, amount_tag in _TAX_AMOUNTS:
            for node in det.xpath(f"n:imposto/n:{group}/*", namespaces=NFE_NS):
                amount = _decimal(node, amount_tag)
                if _text(node, amount_tag) is not None and (amount is None or amount < 0):
                    invalid("INVALID_VALUE", f"det[{index}]/imposto/{group}/{amount_tag}", "Valor do imposto deve ser numérico e não negativo")

    # ------------------------------------------------------------------ 3. consistência

    def validate_consistency(self) -> list[ValidationIssue]:
        if self._inf is None:
            return []
        issues: list[ValidationIssue] = []

        def inconsistent(code: str, location: str, message: str) -> None:
            issues.append(ValidationIssue(CONSISTENCY, code, location, message))

        self._check_access_key_against_fields(inconsistent)

        items_sum = Decimal("0")
        for index, det in enumerate(self._dets(), 1):
            qty, unit, total = (_decimal(det, f"prod/{t}") for t in ("qCom", "vUnCom", "vProd"))
            if None not in (qty, unit, total):
                items_sum += total
                if not _close(qty * unit, total, self._tolerance):
                    inconsistent("ITEM_TOTAL_MISMATCH", f"det[{index}]/prod/vProd",
                                 f"{qty} x {unit} = {qty * unit}, mas vProd = {total}")
            self._check_tax_amounts(index, det, inconsistent)

        products_total = _decimal(self._inf, "total/ICMSTot/vProd")
        if products_total is not None and not _close(items_sum, products_total, self._tolerance):
            inconsistent("PRODUCTS_TOTAL_MISMATCH", "total/ICMSTot/vProd",
                         f"Soma dos itens = {items_sum}, mas vProd total = {products_total}")

        # Simplificação deliberada: vNF = vProd - vDesc + vOutro (sem ST, frete, seguro etc.).
        if products_total is not None and self.total_value is not None:
            discount = _decimal(self._inf, "total/ICMSTot/vDesc") or Decimal("0")
            other = _decimal(self._inf, "total/ICMSTot/vOutro") or Decimal("0")
            expected = products_total - discount + other
            if not _close(expected, self.total_value, self._tolerance):
                inconsistent("NOTE_TOTAL_MISMATCH", "total/ICMSTot/vNF",
                             f"vProd - vDesc + vOutro = {expected}, mas vNF = {self.total_value}")
        return issues

    def _check_access_key_against_fields(self, inconsistent) -> None:
        key = self.access_key
        if key is None or not re.fullmatch(r"\d{44}", key):
            return  # já reportado como erro de dados
        issued = self.issue_date
        parts = {
            "emit/CNPJ": (key[6:20], self.emitter_cnpj),
            "ide/mod": (key[20:22], _text(self._inf, "ide/mod")),
            "ide/serie": (key[22:25], (self.series or "").zfill(3)),
            "ide/nNF": (key[25:34], (self.number or "").zfill(9)),
            "ide/dhEmi": (key[2:6], issued.strftime("%y%m") if issued else None),
        }
        for location, (from_key, from_field) in parts.items():
            if from_field is not None and from_key != from_field:
                inconsistent("ACCESS_KEY_MISMATCH", location,
                             f"Chave de acesso contém '{from_key}', mas o campo tem '{from_field}'")

    def _check_tax_amounts(self, index: int, det: etree._Element, inconsistent) -> None:
        for group, base_tag, rate_tag, amount_tag in _TAX_AMOUNTS:
            for node in det.xpath(f"n:imposto/n:{group}/*", namespaces=NFE_NS):
                base, rate, amount = (_decimal(node, t) for t in (base_tag, rate_tag, amount_tag))
                if None in (base, rate, amount):
                    continue
                expected = base * rate / 100
                if not _close(expected, amount, self._tolerance):
                    inconsistent("TAX_AMOUNT_MISMATCH", f"det[{index}]/imposto/{group}/{amount_tag}",
                                 f"{base} x {rate}% = {expected:.4f}, mas {amount_tag} = {amount}")

    # ------------------------------------------------------------------ resultado

    def validate(self) -> ValidationReport:
        issues = (*self.validate_structure(), *self.validate_data(), *self.validate_consistency())
        report = ValidationReport(issues)
        log.info("Validação de NFC-e %s: %d problema(s)", self.access_key, len(issues))
        if issues:
            log.warning("Problemas encontrados:\n%s", report.describe())
        return report
