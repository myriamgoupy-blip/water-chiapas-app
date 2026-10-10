"""Group water-title holders into broad types (who holds the water), from the holder's name in REPDA."""
import re

RULES = [
    ("utility", r"AYUNTAMIENTO|MUNICIPIO|SAPAM|SISTEMA (MUNICIPAL )?DE AGUA|AGUA POTABLE Y ALCANTARILLADO|ORGANISMO|COAPAM|PRESIDENCIA MUNICIPAL"),
    ("government", r"\bIMSS\b|ISSSTE|GOBIERNO|SECRETAR[IÍ]A|\bCFE\b|COMISI[OÓ]N|INSTITUTO|UNIVERSIDAD|ESCUELA|HOSPITAL|COLEGIO|SEDENA|CONAGUA|D\.?I\.?F\b"),
    ("irrigation", r"UNIDAD DE RIEGO|\bRIEGO\b|DISTRITO DE RIEGO"),
    ("company", r"\bS\.? ?A\.?\b|S\.? ?DE ?R\.? ?L|S\.? ?P\.? ?R\.?|SOCIEDAD|\bS\.? ?C\.?\b|INMUEBLES|EMBOTELLADORA|EMPRESA|CORPORA|COMERCIAL|INDUSTRIA|\bS\.? DE S\.? ?S\.?|HOTEL"),
    ("community", r"EJIDO|COMUNIDAD|COMIT[EÉ]|PATRONATO|JUNTA|BIENES COMUNALES|LOCALIDAD|PARAJE|COLONIA|BARRIO|USUARIOS|ASOCIACI[OÓ]N|GRUPO|COOPERATIVA|UNI[OÓ]N"),
]


def holder_type(name):
    s = str(name).upper()
    for label, pat in RULES:
        if re.search(pat, s):
            return label
    return "individual"
