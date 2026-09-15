from enum import StrEnum


class Stage(StrEnum):
    NUEVO = "NUEVO"
    DESCUBRIMIENTO = "DESCUBRIMIENTO"
    INTERES_CONCRETO = "INTERES_CONCRETO"
    DERIVACION_PENDIENTE = "DERIVACION_PENDIENTE"
    DERIVADO = "DERIVADO"


class CanalPreferido(StrEnum):
    WHATSAPP = "WHATSAPP"
    LLAMADA = "LLAMADA"
    EMAIL = "EMAIL"
    CHAT = "CHAT"


class UsoPrincipal(StrEnum):
    CIUDAD = "CIUDAD"
    TRABAJO = "TRABAJO"
    FAMILIA = "FAMILIA"
    VIAJES = "VIAJES"
    MIXTO = "MIXTO"


class TipoVehiculo(StrEnum):
    SUV = "SUV"
    SEDAN = "SEDAN"
    HATCHBACK = "HATCHBACK"
    PICKUP = "PICKUP"
    VAN = "VAN"
    CROSSOVER = "CROSSOVER"
    OTRO = "OTRO"


class Motorizacion(StrEnum):
    GASOLINA = "GASOLINA"
    DIESEL = "DIESEL"
    HIBRIDO = "HIBRIDO"
    ELECTRICO = "ELECTRICO"
    GLP_GNV = "GLP_GNV"
    NO_DEFINIDO = "NO_DEFINIDO"


class NivelInteres(StrEnum):
    BAJO = "BAJO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"


class MotivoHandoff(StrEnum):
    TEST_DRIVE = "TEST_DRIVE"
    COTIZACION_FORMAL = "COTIZACION_FORMAL"
    COMPRA_INMEDIATA = "COMPRA_INMEDIATA"
    DISCONFORMIDAD = "DISCONFORMIDAD"
    FUERA_DE_ALCANCE = "FUERA_DE_ALCANCE"


class Urgencia(StrEnum):
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"


class HandoffStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"


class CategoriaKb(StrEnum):
    CARROCERIAS = "CARROCERIAS"
    SEGMENTOS = "SEGMENTOS"
    MOTORIZACION = "MOTORIZACION"
    TRANSMISION = "TRANSMISION"
    CONSUMO = "CONSUMO"
    MANTENIMIENTO = "MANTENIMIENTO"
    SEGURIDAD = "SEGURIDAD"
    USO = "USO"
    GLOSARIO = "GLOSARIO"


class ToolStatus(StrEnum):
    OK = "ok"
    NO_RESULTS = "no_results"
    ERROR = "error"


class GuardrailLayer(StrEnum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
