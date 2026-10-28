import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
(ROOT / ".build").mkdir(exist_ok=True)
os.environ["BASE_DIR"] = str(ROOT / ".build" / "test-state")
from PIL import Image
from jobs import Jobs
from processing import images_under, validate_paths, atomic_image, run_export, export_plan, export_signature
from app import app, jobs


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".build")
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.output = self.root / "output"

    def tearDown(self):
        self.temporary.cleanup()

    def wait(self, manager):
        manager.worker.join(timeout=10)
        self.assertFalse(manager.worker.is_alive())
        return manager.snapshot()

    def test_double_submission_is_rejected_and_cancel_waits(self):
        manager = Jobs()
        gate = threading.Event()
        manager.start("resize", lambda job: gate.wait(3), device_id="gpu:requested")
        self.assertEqual(manager.snapshot()["requested_device_id"], "gpu:requested")
        with self.assertRaises(ValueError):
            manager.start("resize", lambda job: None)
        manager.cancel()
        self.assertTrue(manager.snapshot()["active"])
        self.assertEqual(manager.snapshot()["status"], "cancelling")
        with self.assertRaises(ValueError):
            manager.start("resize", lambda job: None)
        gate.set()
        self.assertEqual(self.wait(manager)["status"], "cancelled")
        manager.start("audit", lambda job: {})
        self.assertEqual(self.wait(manager)["status"], "completed")

    def test_progress_counts_finished_files(self):
        manager = Jobs()
        def target(job):
            job.update(total=2, phase="Processing")
            self.assertEqual(job.snapshot()["progress"], 0)
            job.complete_file(True)
            self.assertEqual(job.snapshot()["progress"], 50)
            job.complete_file(False)
        manager.start("audit", target)
        result = self.wait(manager)
        self.assertEqual(result["status"], "completed_with_errors")
        self.assertEqual((result["current"], result["succeeded"], result["failed"]), (2, 1, 1))

    def test_log_cursor_survives_buffer_rollover_and_new_jobs(self):
        manager = Jobs()
        for index in range(600):
            manager.log(index)
        snapshot = manager.snapshot(after=590)
        self.assertEqual(len(snapshot["events"]), 10)
        manager.log("latest")
        self.assertEqual(manager.snapshot(after=snapshot["log_cursor"])["events"][0]["message"], "latest")

    def test_empty_job_finishes(self):
        from processing import run_images
        manager = Jobs()
        manager.start("resize", lambda job: run_images(job, "resize", self.source, self.output, "", "cpu"))
        result = self.wait(manager)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["progress"], 100)

    def test_image_scanner_deduplicates_windows_case(self):
        Image.new("RGB", (10, 10)).save(self.source / "UPPER.JPG")
        Image.new("RGB", (10, 10)).save(self.source / "photo.webp")
        self.assertEqual(len(images_under(self.source)), 2)

    def test_invalid_path_relationships_rejected(self):
        for destination in [self.source, self.source / "output", self.root]:
            with self.assertRaises(ValueError):
                validate_paths(self.source, destination)
        with self.assertRaises(ValueError):
            validate_paths(self.source, self.output, "..")

    def test_atomic_output(self):
        destination = self.output / "image.png"
        atomic_image(Image.new("RGB", (1200, 1800)), destination)
        with Image.open(destination) as image:
            self.assertEqual(image.size, (1200, 1800))
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_logo_rejects_wrong_resolution_before_processing(self):
        Image.new('RGB', (80, 120)).save(self.source / 'image.png')
        response = app.test_client().post('/api/logo/apply', json={'source': str(self.source), 'destination': str(self.output), 'target_width': 1200, 'target_height': 1800})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Run Resize', response.json['error'])
        self.assertFalse(self.output.exists())

    def test_resize_rejects_excessive_output_dimensions(self):
        response = app.test_client().post('/api/resize', json={'root_dir': str(self.source), 'dest_dir': str(self.output), 'target_width': 999999, 'target_height': 1800})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.output.exists())

    def test_review_all_images_keeps_padding_count_separate(self):
        product = self.source / 'Product'; product.mkdir()
        resized = self.output / 'Product'; resized.mkdir(parents=True)
        for name in ('one.png', 'two.png'):
            Image.new('RGB', (12, 18)).save(product / name)
            Image.new('RGB', (12, 18)).save(resized / name)
        (self.output / 'manual_patch_list.md').write_text('- `Product/one.png`\n', encoding='utf-8')
        response = app.test_client().get('/api/patch-list', query_string={'root_dir': str(self.source), 'dest_dir': str(self.output), 'all': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['padded_count'], 1)
        self.assertEqual(len(response.json['items']), 2)
        self.assertEqual(sum(item['padded'] for item in response.json['items']), 1)

    def test_export_preserves_original_and_handles_collision(self):
        original = self.source / "image.jpg"
        Image.new("RGB", (10, 10)).save(original)
        for run in range(2):
            manager = Jobs()
            manager.start("export", lambda job: run_export(job, self.source, self.output))
            result = self.wait(manager)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result['skipped'], run)
        self.assertTrue(original.exists())
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_export_preserves_nested_and_empty_folders(self):
        paths = [self.source / "Summer" / "Burgundy Dress" / "Untitled Export" / "a.jpg",
                 self.source / "Winter" / "Burgundy Dress" / "Untitled Export" / "b.jpg",
                 self.source / "Teal Saree" / "c.png"]
        for index, path in enumerate(paths):
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (10, 10), (index * 30, 0, 0)).save(path)
        (self.source / "Empty collection" / "Empty subfolder").mkdir(parents=True)
        manager = Jobs()
        manager.start("export", lambda job: run_export(job, self.source, self.output, 'lightroom'))
        result = self.wait(manager)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['succeeded'], 2)
        for path in paths:
            if path.parent.name == 'Untitled Export':
                exported = self.output / path.parent.parent.relative_to(self.source) / f'{path.parent.parent.name}_1{path.suffix}'
                self.assertTrue(exported.is_file(), exported)
                self.assertEqual(exported.read_bytes(), path.read_bytes())
            self.assertTrue(path.exists())
        self.assertFalse((self.output / 'Teal Saree').exists())
        self.assertFalse(any(p.name == 'Untitled Export' for p in self.output.rglob('*')))

    def test_export_conflict_does_not_overwrite(self):
        original = self.source / 'image.jpg'
        Image.new('RGB', (10, 10), 'red').save(original)
        self.output.mkdir()
        target = self.output / f'{self.source.name}_1.jpg'
        target.write_bytes(b'keep existing file')
        _, _, plan = export_plan(self.source, self.output, 'native')
        self.assertEqual(plan[0]['status'], 'conflict')
        job = Jobs()
        job.start('export', lambda worker: run_export(worker, self.source, self.output, 'native'))
        self.assertEqual(self.wait(job)['status'], 'completed_with_errors')
        self.assertEqual(target.read_bytes(), b'keep existing file')

    def test_lightroom_preview_api_and_native_mode(self):
        product = self.source / 'Date' / 'Dress'
        (product / 'Untitled Export').mkdir(parents=True)
        Image.new('RGB', (10, 10), 'white').save(product / 'original.png')
        Image.new('RGB', (10, 10), 'white').save(product / 'Untitled Export' / 'final.JPG')
        client = app.test_client()
        payload = {'export_src': str(self.source), 'export_dest': str(self.output), 'mode': 'lightroom'}
        response = client.post('/api/export/preview', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['total'], 1)
        self.assertEqual(response.json['entries'][0]['output'], 'Date/Dress/Dress_1.jpg')
        self.assertFalse(self.output.exists())
        payload['mode'] = 'native'
        native = client.post('/api/export/preview', json=payload).json
        self.assertEqual(native['total'], 2)
        self.assertTrue(all('/Untitled Export/' not in entry['output'] for entry in native['entries']))

    def test_export_strips_selected_suffix_from_names_in_both_modes(self):
        folder = self.source / 'Collection' / 'Rose_selected_images'
        (folder / 'Untitled Export').mkdir(parents=True)
        Image.new('RGB', (10, 10)).save(folder / 'native.png')
        Image.new('RGB', (10, 10)).save(folder / 'Untitled Export' / 'lightroom.jpg')
        for mode in ('native', 'lightroom'):
            _, _, entries = export_plan(self.source, self.output, mode)
            self.assertTrue(entries)
            self.assertTrue(all(Path(item['output']).name.startswith('Rose_') for item in entries))
            self.assertTrue(all('Rose_selected_images/' in item['output'] for item in entries))

    def test_export_stops_if_files_change_after_preview(self):
        first = self.source / 'one.jpg'
        Image.new('RGB', (10, 10), 'white').save(first)
        source, destination, entries = export_plan(self.source, self.output, 'native')
        signature = export_signature(source, destination, 'native', entries)
        Image.new('RGB', (10, 10), 'blue').save(self.source / 'two.jpg')
        job = Jobs()
        job.start('export', lambda worker: run_export(worker, self.source, self.output, 'native', signature))
        result = self.wait(job)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('changed after preview', result['error'])
        self.assertFalse(self.output.exists())

    def test_failed_export_preserves_original(self):
        original = self.source / "image.jpg"
        Image.new("RGB", (10, 10)).save(original)
        manager = Jobs()
        with patch("processing.shutil.copy2", side_effect=OSError("disk full")):
            manager.start("export", lambda job: run_export(job, self.source, self.output))
            result = self.wait(manager)
        self.assertEqual(result["status"], "completed_with_errors")
        self.assertTrue(original.exists())
        self.assertEqual(list(self.output.iterdir()), [])

    def test_legacy_export_does_not_delete_failed_copy(self):
        import move_to_shopify
        original = self.source / "image.jpg"
        Image.new("RGB", (10, 10)).save(original)
        with patch("move_to_shopify.shutil.copy2", side_effect=OSError("disk full")):
            move_to_shopify.run_export(str(self.source), str(self.output), dry_run=False, delete_empty_src=True, log_callback=lambda _: None)
        self.assertTrue(original.exists())

    def test_corrupt_image_is_reported_without_stopping_batch(self):
        from processing import run_images
        (self.source / "bad.jpg").write_bytes(b"not an image")
        Image.new("RGB", (10, 10)).save(self.source / "good.jpg")
        class FakeDetector:
            device = {"name": "fake", "provider": "test"}
            def __init__(self, _): pass
            def detect(self, image): return None
            def close(self): pass
        manager = Jobs()
        with patch("inference.Detector", FakeDetector):
            manager.start("resize", lambda job: run_images(job, "resize", self.source, self.output, "", "cpu"))
            result = self.wait(manager)
        self.assertEqual(result["status"], "completed_with_errors")
        self.assertEqual(result["succeeded"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertTrue((self.output / "good.jpg").exists())

    def test_api_local_origin_and_path_validation(self):
        client = app.test_client()
        response = client.post("/api/resize", json={}, headers={"Origin": "https://example.org"})
        self.assertEqual(response.status_code, 403)
        response = client.post("/api/resize", json={"root_dir": str(self.source), "dest_dir": str(self.source)})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(client.get("/api/health").json["app"], "janvi-image-resize")

    def test_ui_monitor_is_shared_between_sections(self):
        document = app.test_client().get("/").text
        self.assertLess(document.index('id="active-task-card"'), document.index('id="sec-dashboard"'))
        self.assertNotIn("fonts.googleapis.com", document)
        self.assertIn("/static/monitor.js", document)

    def test_unavailable_device_is_rejected(self):
        from inference import Detector
        with patch("inference.inventory", return_value=[]):
            with self.assertRaisesRegex(ValueError, "unavailable"):
                Detector("gpu:missing")

    def test_gpu_cannot_silently_become_cpu(self):
        from inference import Detector
        device = {"id": "gpu:test", "available": True, "index": 0}
        class CPUOnlySession:
            def disable_fallback(self): pass
            def get_providers(self): return ["CPUExecutionProvider"]
        with patch("inference.inventory", return_value=[device]), patch("inference.ort.InferenceSession", return_value=CPUOnlySession()):
            with self.assertRaisesRegex(RuntimeError, "fell back"):
                Detector("gpu:test")

    def test_bad_device_finishes_as_failed_job(self):
        from processing import run_images
        Image.new("RGB", (10, 10)).save(self.source / "image.jpg")
        manager = Jobs()
        manager.start("resize", lambda job: run_images(job, "resize", self.source, self.output, "", "gpu:missing"))
        result = self.wait(manager)
        self.assertEqual(result["status"], "failed")
        self.assertIn("unavailable", result["error"])


if __name__ == "__main__":
    unittest.main()
