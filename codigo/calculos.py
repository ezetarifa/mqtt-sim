"""Cálculo del tamaño de un PUBLISH MQTT 3.1.1 con QoS 0."""

def bytes_remaining_length(valor):
    if not isinstance(valor, int) or not 0 <= valor <= 268435455:
        raise ValueError("Remaining Length fuera de rango")
    cantidad = 1
    while valor >= 128:
        valor //= 128
        cantidad += 1
    return cantidad


def tamanio_publish(payload_bytes, tema):
    if not isinstance(payload_bytes, int) or payload_bytes < 0:
        raise ValueError("El payload debe ser un entero no negativo")
    tema_utf8 = tema.encode("utf-8")
    if not tema_utf8 or len(tema_utf8) > 65535 or any(c in tema for c in ("+", "#", "\0")):
        raise ValueError("Tema PUBLISH no admitido por este módulo")
    restante = 2 + len(tema_utf8) + payload_bytes
    return 1 + bytes_remaining_length(restante) + restante


