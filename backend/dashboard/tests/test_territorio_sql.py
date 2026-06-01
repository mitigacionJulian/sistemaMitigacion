from django.test import SimpleTestCase

from dashboard.kpis import FiltrosKpi
from dashboard.territorio_sql import (
    append_filtros_territoriales,
    barrio_fk_col,
    comuna_fk_col,
    meta_filtros_dict,
    parse_modo_punto_critico,
    parse_modo_territorio,
    punto_critico_serie_sql,
)


class TerritorioSqlTests(SimpleTestCase):
    def test_parse_modo_territorio_default(self):
        self.assertEqual(parse_modo_territorio(None), "registro")
        self.assertEqual(parse_modo_territorio(""), "registro")
        self.assertEqual(parse_modo_territorio("registro"), "registro")

    def test_parse_modo_territorio_espacial_aliases(self):
        self.assertEqual(parse_modo_territorio("espacial"), "espacial")
        self.assertEqual(parse_modo_territorio("spatial"), "espacial")
        self.assertEqual(parse_modo_territorio("postgis"), "espacial")

    def test_columnas_fk_por_modo(self):
        self.assertEqual(comuna_fk_col("registro"), "comuna_id")
        self.assertEqual(comuna_fk_col("espacial"), "comuna_id_espacial")
        self.assertEqual(barrio_fk_col("espacial"), "barrio_id_espacial")

    def test_append_filtros_registro(self):
        where: list[str] = ["i.fecha_incidente >= %s"]
        params: list = ["2021-01-01"]
        f = FiltrosKpi(comuna_id=5, barrio_id=12)
        append_filtros_territoriales(where, params, f)
        self.assertIn("i.comuna_id = %s", where)
        self.assertIn("i.barrio_id = %s", where)
        self.assertNotIn("i.ubicacion IS NOT NULL", where)
        self.assertEqual(params, ["2021-01-01", 5, 12])

    def test_append_filtros_espacial(self):
        where: list[str] = []
        params: list = []
        f = FiltrosKpi(comuna_id=3, modo_territorio="espacial")
        append_filtros_territoriales(where, params, f)
        self.assertIn("i.ubicacion IS NOT NULL", where)
        self.assertIn("i.comuna_id_espacial = %s", where)
        self.assertEqual(meta_filtros_dict(f)["territorio"], "espacial")

    def test_parse_modo_punto_critico(self):
        self.assertEqual(parse_modo_punto_critico(None), "registro")
        self.assertEqual(parse_modo_punto_critico("proximidad"), "proximidad")
        self.assertEqual(parse_modo_punto_critico("dwithin"), "proximidad")

    def test_punto_critico_serie_sql_registro(self):
        join, jparams, wh, params = punto_critico_serie_sql(
            FiltrosKpi(punto_critico_id=7, punto_critico_modo="registro")
        )
        self.assertEqual(join, "")
        self.assertEqual(wh, ["i.punto_critico_id = %s"])
        self.assertEqual(params, [7])

    def test_punto_critico_serie_sql_proximidad(self):
        join, jparams, wh, params = punto_critico_serie_sql(
            FiltrosKpi(punto_critico_id=7, punto_critico_modo="proximidad")
        )
        self.assertIn("punto_critico pc", join)
        self.assertEqual(jparams, [7])
        self.assertTrue(any("ST_DWithin" in w for w in wh))
        self.assertEqual(params, [])
