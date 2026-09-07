"""Offline integration checks: execute production functions with external services mocked."""
import ast
import base64
import io
import json
import logging
import re
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
from PIL import Image, ImageDraw
from src.standards import ALLOWED_VALUES, CYBOW_11M_STANDARDS
from src.cybow_reference import enforce_strict_cybow_standards
from src.image_diagnostics import prepare_image, image_quality, sample_regions

ROOT = Path(__file__).parent

def functions_from(path, names, namespace):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8-sig"))
    selected = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    for n in selected:
        n.decorator_list = []
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    return namespace

class WorkflowTests(unittest.TestCase):
    def run_workflow(self, payload):
        image = Image.effect_noise((400,400),12).convert("RGB")
        draw = ImageDraw.Draw(image)
        # Paint each proposed pad with the matching reference color so the happy-path
        # fixture represents a physically coherent strip rather than random noise.
        for i, p in enumerate(ALLOWED_VALUES):
            x1, y1, x2, y2 = [.05+i*.08,.1,.1+i*.08,.3]
            ref = next((r for r in CYBOW_11M_STANDARDS[p] if r["value"] == payload.get(p)), None)
            color = ref["rgb"] if ref else (80 + i*10, 120, 180)
            draw.rectangle((int(x1*400), int(y1*400), int(x2*400), int(y2*400)), fill=color)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        raw = buffer.getvalue()
        line = MagicMock()
        line.get_message_content.return_value.iter_content.return_value = [raw]
        client = MagicMock()
        client.chat.completions.create.return_value.choices = [
            type("Choice", (), {"message":type("Message", (), {"content":json.dumps(payload)})()})()]
        db = MagicMock()
        db.insert_record.return_value = True
        import os
        ns = dict(os=os, json=json, re=re, base64=base64, datetime=datetime, ALLOWED_VALUES=ALLOWED_VALUES,
                  prepare_image=prepare_image, image_quality=image_quality, sample_regions=sample_regions,
                  enforce_strict_cybow_standards=enforce_strict_cybow_standards,
                  line_bot_api=line, client=client, db_handler=db, logger=logging.getLogger("test"),
                  TextSendMessage=lambda **kw: kw, resize_image_to_base64_from_bytes=lambda *a,**kw:base64.b64encode(raw))
        functions_from("bot.py", {"process_image_with_ai","extract_safe_float"}, ns)
        ns["process_image_with_ai"]("image","user","test")
        return db, line

    def complete(self):
        data = {p: v[0] for p,v in ALLOWED_VALUES.items()}
        data["pad_regions"] = {p:[.05+i*.08,.1,.1+i*.08,.3] for i,p in enumerate(ALLOWED_VALUES)}
        return data

    def test_complete_record_persists_pixels_and_list(self):
        db, line = self.run_workflow(self.complete())
        db.insert_record.assert_called_once()
        kwargs = db.insert_record.call_args.kwargs
        self.assertIsInstance(kwargs["clinical_bullets"], list)
        self.assertEqual(len(kwargs["diagnostics"]["detected_rgb"]),11)
        self.assertNotIn("85.0%", str(line.push_message.call_args))

    def test_incomplete_record_never_persisted(self):
        data = self.complete()
        data["protein"] = "unreadable"
        db, _ = self.run_workflow(data)
        db.insert_record.assert_not_called()

    def test_missing_regions_never_persisted(self):
        data = self.complete()
        data["pad_regions"] = {}
        db, _ = self.run_workflow(data)
        db.insert_record.assert_not_called()

class DatabaseTests(unittest.TestCase):
    def test_connection_preserves_encoded_credentials_and_tls(self):
        from urllib.parse import urlparse
        driver = MagicMock()
        url = 'postgresql://test:p%40ss@localhost/db?sslmode=verify-full'
        ns = functions_from('src/db_handler.py', {'get_connection'},
                            {'DATABASE_URL':url, 'urlparse':urlparse, 'psycopg2':driver})
        ns['get_connection']()
        driver.connect.assert_called_once_with(url, connect_timeout=15)

    def test_insert_serializes_once_and_preserves_diagnostics(self):
        connection = MagicMock()
        ns = functions_from("src/db_handler.py", {"insert_record"}, {"get_connection":lambda:connection})
        kwargs = {p:v[0] for p,v in ALLOWED_VALUES.items()}
        self.assertTrue(ns["insert_record"]("2026-01-01", **kwargs, clinical_bullets=["hello"],
                                          diagnostics={"detected_rgb":{"glucose":[1,2,3]}}))
        sql, values = connection.cursor.return_value.execute.call_args.args
        self.assertEqual(sql.count("%s"), len(values))
        self.assertEqual(json.loads(values[-2]), ["hello"])
        self.assertEqual(json.loads(values[-1])["detected_rgb"]["glucose"], [1,2,3])

    def test_migration_repairs_existing_policy(self):
        connection = MagicMock()
        ns = functions_from("src/db_handler.py", {"init_db"}, {"get_connection":lambda:connection})
        ns["init_db"]()
        queries = [c.args[0] for c in connection.cursor.return_value.execute.call_args_list]
        self.assertTrue(any("TO service_role" in sql for sql in queries))
        self.assertTrue(any("diagnostics JSONB" in sql for sql in queries))
        connection.commit.assert_called_once()

    def test_cursor_failure_does_not_mask_error(self):
        connection = MagicMock()
        connection.cursor.side_effect = RuntimeError("cursor unavailable")
        ns = functions_from("src/db_handler.py", {"insert_record"}, {"get_connection":lambda:connection})
        self.assertFalse(ns["insert_record"]("date", **{p:v[0] for p,v in ALLOWED_VALUES.items()}))
        connection.close.assert_called_once()

    def test_no_top_level_migration(self):
        tree = ast.parse((ROOT/"src/db_handler.py").read_text(encoding="utf-8-sig"))
        self.assertFalse(any(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
                            and isinstance(n.value.func,ast.Name) and n.value.func.id=="init_db" for n in tree.body))

    def test_legacy_double_json(self):
        import ast as ast_module
        ns = functions_from("src/analysis.py", {"sanitize_thai_text","parse_clinical_bullets"},
                            {"json":json,"ast":ast_module,"re":re})
        expected = ["คำแนะนำภาษาไทย", "Glucose result"]
        encoded = json.dumps(json.dumps(expected, ensure_ascii=False), ensure_ascii=False)
        self.assertEqual(ns["parse_clinical_bullets"](encoded),expected)

if __name__ == "__main__":
    unittest.main()
