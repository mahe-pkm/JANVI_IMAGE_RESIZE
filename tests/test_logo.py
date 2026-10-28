import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
(ROOT / ".build").mkdir(exist_ok=True)
os.environ.setdefault("BASE_DIR", str(ROOT / ".build" / "logo-test-state"))
import app as dashboard
from jobs import Jobs
from logo_processing import composite, read_logo, DEFAULT_LOGO, run_logo, save_new_image, save_preset, list_presets, settings_for


class LogoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".build")
        self.root = Path(self.temp.name)
        self.base = self.root / "data"
        self.base.mkdir()
        self.source = self.root / "input"
        self.source.mkdir()
        self.output = self.root / "output"
        self.patch = patch.object(dashboard, "BASE_DIR", self.base)
        self.patch.start()
        self.client = dashboard.app.test_client()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_position_opacity_and_invalid_geometry(self):
        image = Image.new("RGB", (100, 100), "white")
        logo = Image.new("RGBA", (10, 10), (255, 0, 0, 128))
        settings = {"position": "bottom-right", "width_pct": 20, "opacity_pct": 50,
                    "offset_x_pct": 0, "offset_y_pct": 0}
        result = composite(image, logo, settings)
        self.assertEqual(result.getpixel((10, 10)), (255, 255, 255, 255))
        self.assertEqual(result.getpixel((90, 90)), (255, 191, 191, 255))
        settings["opacity_pct"] = 0
        self.assertEqual(composite(image, logo, settings).getpixel((90, 90)), (255, 255, 255, 255))
        settings["position"] = "top-left"
        settings["opacity_pct"] = 100
        self.assertEqual(composite(image, logo, settings).getpixel((5, 5)), (255, 127, 127, 255))
        settings["width_pct"] = "NaN"
        with self.assertRaises(ValueError):
            settings_for(settings)
        with self.assertRaises(ValueError):
            composite(Image.new("RGB", (200, 20)), Image.new("RGBA", (1, 5), "red"), {"width_pct": 60})

    def test_default_values_follow_supplied_lightroom_settings(self):
        self.assertEqual(settings_for({}), {"position": "top-left", "width_pct": 15.0,
            "opacity_pct": 88.1, "offset_x_pct": 0.0, "offset_y_pct": 0.0, "rotation": 0, "size_mode": "proportional"})

    def test_default_logo_preserves_transparent_canvas(self):
        logo = read_logo(DEFAULT_LOGO)
        self.assertEqual(logo.size, (135, 191))
        self.assertEqual(logo.getchannel('A').getbbox(), (17, 22, 115, 172))
        result = composite(Image.new('RGB', (1200, 1800), 'white'), logo, {})
        self.assertEqual(result.getpixel((0, 0)), (255, 255, 255, 255))
        self.assertNotEqual(result.getpixel((90, 100)), (255, 255, 255, 255))

    def test_nested_duplicate_names_and_extensions_are_preserved(self):
        for folder in ('Collection A/Export', 'Collection B/Export'):
            path = self.source / folder / 'Photo 01.JPG'
            path.parent.mkdir(parents=True)
            Image.new('RGB', (120, 180), 'white').save(path, format='JPEG')
        (self.source / 'Empty' / 'Nested').mkdir(parents=True)
        job = Jobs()
        job.start('logo', lambda worker: run_logo(worker, self.base, self.source, self.output, 'default', {}))
        job.worker.join(10)
        self.assertEqual(job.snapshot()['succeeded'], 2)
        self.assertTrue((self.output / 'Collection A/Export/Photo 01.JPG').is_file())
        self.assertTrue((self.output / 'Collection B/Export/Photo 01.JPG').is_file())
        self.assertTrue((self.output / 'Empty/Nested').is_dir())

    @unittest.skipUnless(os.name == 'nt', 'Windows folder picker')
    def test_folder_picker_result_cancel_and_failure(self):
        import json
        with patch.object(dashboard.subprocess, 'run', return_value=SimpleNamespace(stdout=json.dumps({'selected_path': str(self.source)}))):
            result = self.client.post('/api/select-folder', json={'initial_dir': str(self.source)})
            self.assertEqual(result.json['selected_path'], str(self.source.resolve()))
        with patch.object(dashboard.subprocess, 'run', return_value=SimpleNamespace(stdout='{"selected_path":""}')):
            self.assertEqual(self.client.post('/api/select-folder', json={}).json['selected_path'], '')
        with patch.object(dashboard.subprocess, 'run', side_effect=OSError('unavailable')):
            result = self.client.post('/api/select-folder', json={})
            self.assertEqual(result.status_code, 500)
            self.assertIn('manually', result.json['error'])

    def test_fit_fill_and_legacy_size_settings(self):
        image = Image.new("RGB", (100, 100), "white")
        logo = Image.new("RGBA", (10, 20), (255, 0, 0, 255))
        base = {"position": "top-left", "opacity_pct": 100, "offset_x_pct": 0, "offset_y_pct": 0}
        fit = composite(image, logo, dict(base, size_mode="fit"))
        fill = composite(image, logo, dict(base, size_mode="fill"))
        self.assertEqual(fit.getpixel((25, 50)), (255, 0, 0, 255))
        self.assertEqual(fit.getpixel((75, 50)), (255, 255, 255, 255))
        self.assertEqual(fill.getpixel((75, 50)), (255, 0, 0, 255))
        self.assertEqual(settings_for(base)["size_mode"], "proportional")
        with self.assertRaises(ValueError):
            settings_for(dict(base, size_mode="invalid"))

    def test_rotation_and_legacy_settings(self):
        image = Image.new("RGB", (100, 100), "white")
        logo = Image.new("RGBA", (10, 20), (255, 0, 0, 255))
        base = {"position": "top-left", "width_pct": 20, "opacity_pct": 100, "offset_x_pct": 0, "offset_y_pct": 0}
        normal = composite(image, logo, base)
        rotated = composite(image, logo, dict(base, rotation=90))
        self.assertEqual(normal.getpixel((10, 30)), (255, 0, 0, 255))
        self.assertEqual(rotated.getpixel((10, 30)), (255, 255, 255, 255))
        self.assertEqual(settings_for(base)["rotation"], 0)
        with self.assertRaises(ValueError):
            settings_for(dict(base, rotation=45))

    def test_jpeg_logo_upload_is_supported(self):
        logo = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(logo, format="JPEG")
        logo.seek(0)
        response = self.client.post("/api/logo/assets", data={"file": (logo, "brand.jpg")})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertTrue((self.base / "logos" / (response.json["id"] + ".png")).exists())

    def test_preview_matches_batch_and_skips_existing_files(self):
        first = self.source / "Burgundy" / "Untitled Export" / "a.png"
        first.parent.mkdir(parents=True)
        Image.new("RGB", (120, 180), "white").save(first)
        (self.source / "Empty" / "Nested").mkdir(parents=True)
        original_bytes = first.read_bytes()
        overlay = io.BytesIO()
        Image.new("RGBA", (10, 20), (255, 0, 0, 150)).save(overlay, format="PNG")
        overlay.seek(0)
        response = self.client.post("/api/logo/assets", data={"file": (overlay, "test-logo.png")})
        self.assertEqual(response.status_code, 201, response.text)
        asset_id = response.json["id"]
        settings = {"position": "bottom-right", "width_pct": 20, "opacity_pct": 60,
                    "offset_x_pct": 5, "offset_y_pct": 5, "rotation": 90}
        response = self.client.post("/api/logo/preview", json={"source": str(self.source),
                                    "image": first.relative_to(self.source).as_posix(),
                                    "asset_id": asset_id, "settings": settings})
        self.assertEqual(response.status_code, 200, response.status)
        expected = Image.open(io.BytesIO(response.data)).convert("RGBA")
        job = Jobs()
        job.start("logo", lambda worker: run_logo(worker, self.base, self.source, self.output, asset_id, settings))
        job.worker.join(10)
        result = job.snapshot()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["succeeded"], 1)
        self.assertEqual(result["results"]["source_dir"], str(self.source.resolve()))
        self.assertEqual(result["results"]["output_dir"], str(self.output.resolve()))
        marked = self.output / first.relative_to(self.source)
        with Image.open(marked) as actual:
            self.assertEqual(actual.convert("RGBA").tobytes(), expected.tobytes())
        self.assertEqual(first.read_bytes(), original_bytes)
        self.assertTrue((self.output / "Empty" / "Nested").is_dir())
        existing_bytes = marked.read_bytes()
        again = Jobs()
        again.start("logo", lambda worker: run_logo(worker, self.base, self.source, self.output, asset_id, settings))
        again.worker.join(10)
        self.assertEqual(again.snapshot()["skipped"], 1)
        self.assertEqual(marked.read_bytes(), existing_bytes)
        fill_settings = dict(settings, size_mode="fill")
        response = self.client.post("/api/logo/preview", json={"source": str(self.source),
            "image": first.relative_to(self.source).as_posix(), "asset_id": asset_id, "settings": fill_settings})
        self.assertEqual(response.status_code, 200)
        filled_preview = Image.open(io.BytesIO(response.data)).convert("RGBA")
        filled_output = self.root / "fill-output"
        fill_job = Jobs()
        fill_job.start("logo", lambda worker: run_logo(worker, self.base, self.source, filled_output, asset_id, fill_settings))
        fill_job.worker.join(10)
        self.assertEqual(fill_job.snapshot()["status"], "completed")
        with Image.open(filled_output / first.relative_to(self.source)) as result:
            self.assertEqual(result.convert("RGBA").tobytes(), filled_preview.tobytes())

    def test_jpeg_orientation_and_color_profile(self):
        path = self.source / "rotated.jpg"
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (30, 50), "white").save(path, exif=exif, icc_profile=b"test-profile")
        original = path.read_bytes()
        job = Jobs()
        job.start("logo", lambda worker: run_logo(worker, self.base, self.source, self.output, "default", {}))
        job.worker.join(10)
        self.assertEqual(job.snapshot()["status"], "completed")
        with Image.open(self.output / "rotated.jpg") as result:
            self.assertEqual(result.size, (50, 30))
            self.assertNotEqual(result.getexif().get(274), 6)
            self.assertEqual(result.info.get("icc_profile"), b"test-profile")
        self.assertEqual(path.read_bytes(), original)

    def test_presets_persist_and_duplicate_names_are_rejected(self):
        preset = save_preset(self.base, "Janvi", "default", {"position": "top-left"})
        self.assertEqual(list_presets(self.base)[0], preset)
        with self.assertRaises(ValueError):
            save_preset(self.base, "janvi", "default", {})
        self.assertEqual(len(list_presets(self.base)), 1)

    def test_invalid_and_outside_preview_files_are_rejected(self):
        outside = self.root / "outside.png"
        Image.new("RGB", (10, 10)).save(outside)
        response = self.client.post("/api/logo/preview", json={"source": str(self.source), "image": "../outside.png", "asset_id": "default"})
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/logo/apply", json={"source": str(self.source), "destination": str(self.source), "asset_id": "default"})
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/logo/assets", data={"file": (io.BytesIO(b"not an image"), "invalid.png")})
        self.assertEqual(response.status_code, 400)

    def test_exclusive_copy_fallback_does_not_replace_existing_output(self):
        self.output.mkdir()
        target = self.output / "existing.png"
        Image.new("RGBA", (12, 12), "blue").save(target)
        before = target.read_bytes()
        with patch("logo_processing.os.link", side_effect=OSError("hard links unsupported")):
            self.assertFalse(save_new_image(Image.new("RGBA", (12, 12), "red"), {}, target))
            fresh = self.output / "fresh.png"
            self.assertTrue(save_new_image(Image.new("RGBA", (12, 12), "red"), {}, fresh))
        self.assertEqual(target.read_bytes(), before)
        with Image.open(fresh) as result:
            self.assertEqual(result.getpixel((0, 0)), (255, 0, 0, 255))
        self.assertEqual(len(list(self.output.iterdir())), 2)

    def test_failed_file_does_not_stop_batch(self):
        (self.source / "bad.jpg").write_bytes(b"not an image")
        Image.new("RGB", (120, 180)).save(self.source / "good.png")
        job = Jobs()
        job.start("logo", lambda worker: run_logo(worker, self.base, self.source, self.output, "default", {}))
        job.worker.join(10)
        result = job.snapshot()
        self.assertEqual(result["status"], "completed_with_errors")
        self.assertEqual((result["succeeded"], result["failed"]), (1, 1))
        self.assertTrue((self.output / "good.png").is_file())

    def test_logo_job_report_is_persisted(self):
        Image.new('RGB', (120, 180), 'white').save(self.source / 'sample.png')
        job = Jobs(self.base / 'job-logs')
        job.start('logo', lambda worker: run_logo(worker, self.base, self.source, self.output, 'default', {}))
        job.worker.join(10)
        result = job.snapshot()
        self.assertEqual(result['status'], 'completed')
        report = Path(result['report_path']).read_text(encoding='utf-8')
        self.assertIn('Logo added: sample.png', report)
        self.assertIn('1 succeeded', report)


if __name__ == "__main__":
    unittest.main()
