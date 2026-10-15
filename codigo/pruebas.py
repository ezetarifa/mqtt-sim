"""Verificación básica del mock-up, ejecutable con unittest."""
import unittest
from dataclasses import replace
from calculos import tamanio_publish
from simulacion import Configuracion, Mockup


class Pruebas(unittest.TestCase):
    def test_mensaje_aislado(self):
        c = Configuracion(payload_bytes=1024, mensajes=1, jitter_por_trayecto_s=0)
        r = Mockup(c).ejecutar()
        esperado = 1000 * (2 * 8 * tamanio_publish(1024, c.tema) / 10_000_000 + 0.081)
        self.assertAlmostEqual(r['resumen']['latencia_media_ms'], esperado)

    def test_propagacion_no_bloquea_transmisor(self):
        c = Configuracion(payload_bytes=2, frecuencia=50, mensajes=10, jitter_por_trayecto_s=0)
        r = Mockup(c).ejecutar()
        self.assertTrue(all(m['espera_subida_s'] == 0 for m in r['mensajes']))
        self.assertEqual(r['resumen']['descartados'], 0)

    def test_descarte_y_conservacion(self):
        c = Configuracion(payload_bytes=131072, frecuencia=50, mensajes=100, cola_maxima=3)
        r = Mockup(c).ejecutar()
        s = r['resumen']
        self.assertGreater(s['descartados'], 0)
        self.assertEqual(s['generados'], s['recibidos'] + s['descartados'] + s['pendientes'])
        self.assertLessEqual(s['cola_maxima_subida'], 3)

    def test_reproducibilidad(self):
        c = Configuracion(payload_bytes=131072, frecuencia=20, mensajes=30)
        self.assertEqual(Mockup(c).ejecutar(), Mockup(c).ejecutar())

    def test_cola_sin_espera(self):
        c = Configuracion(payload_bytes=131072, frecuencia=50, mensajes=30, cola_maxima=0)
        r = Mockup(c).ejecutar()
        self.assertEqual(r['resumen']['cola_maxima_subida'], 0)
        self.assertGreater(r['resumen']['descartados'], 0)


if __name__ == '__main__':
    unittest.main()
