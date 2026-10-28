import json
import os
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from subject_aware_resize import smart_crop_and_resize, padding_geometry, crop_decision
from photoshop_repair import update_padding_queue, repair_status, checksum, workspace


class PhotoshopQueueTests(unittest.TestCase):
    def test_custom_dimensions_are_used_for_padding_and_recorded_geometry(self):
        image = Image.new('RGB', (600, 900), 'red')
        output, padded, geometry = smart_crop_and_resize(image, None, include_geometry=True, target_width=1000, target_height=1000)
        self.assertTrue(padded)
        self.assertEqual(output.size, (1000, 1000))
        self.assertEqual((geometry['canvas_width'], geometry['canvas_height']), (1000, 1000))
        self.assertEqual(geometry['padding']['left'], 167)
        self.assertEqual(geometry['padding']['right'], 167)

    def test_custom_ratio_exact_match_never_crops(self):
        image = Image.new('RGB', (400, 400), 'blue')
        output, padded, geometry = smart_crop_and_resize(image, None, include_geometry=True, target_width=1200, target_height=1200)
        self.assertEqual(output.size, (1200, 1200))
        self.assertFalse(padded)
        self.assertIsNone(geometry)

    def test_exact_ratio_preserves_composition_without_a_detection(self):
        image = Image.new('RGB', (200, 300), 'red')
        image.putpixel((0, 0), (0, 255, 0))
        output, padded, geometry = smart_crop_and_resize(image, None, include_geometry=True)
        self.assertFalse(padded)
        self.assertIsNone(geometry)
        self.assertEqual(output.getpixel((0, 0)), (0, 255, 0))
        self.assertEqual(crop_decision(image.size, None)['reason'], 'correct_ratio')

    def test_missing_subject_and_tight_subject_are_padded(self):
        self.assertEqual(crop_decision((1080, 1920), None)['reason'], 'no_subject_detected')
        self.assertTrue(crop_decision((1080, 1920), [61, 201, 1076, 1818])['padded'])
        _, padded, geometry = smart_crop_and_resize(Image.new('RGB', (1080, 1920)), None, include_geometry=True)
        self.assertTrue(padded)
        self.assertEqual(geometry['padding']['left'], 94)

    def test_horizontal_padding_uses_actual_fit_and_odd_pixel_rounding(self):
        image = Image.new('RGB', (511, 1800))
        output, padded, geometry = smart_crop_and_resize(image, (0, 0, 511, 1800), include_geometry=True)
        self.assertTrue(padded)
        self.assertEqual(output.size, (1200, 1800))
        self.assertEqual(geometry['padding'], dict(left=344, right=345, top=0, bottom=0))
        self.assertEqual(sum(r['width'] * r['height'] for r in geometry['rectangles']) + 511 * 1800, 1200 * 1800)

    def test_vertical_padding_and_legacy_return_contract(self):
        image = Image.new('RGB', (1280, 720))
        _, padded, geometry = smart_crop_and_resize(image, (0, 0, 1280, 720), include_geometry=True)
        self.assertTrue(padded)
        self.assertEqual(geometry['padding'], dict(left=0, right=0, top=562, bottom=563))
        self.assertEqual(len(smart_crop_and_resize(image, None)), 2)

    def test_no_padding_has_no_photoshop_selection(self):
        _, padded, geometry = smart_crop_and_resize(Image.new('RGB', (1200, 1800)), None, include_geometry=True)
        self.assertFalse(padded)
        self.assertIsNone(geometry)

    def test_nested_unicode_queue_preserves_gallery_bullets_and_embeds_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = "Collection/Product name/image 'வண்ணம்'.png"
            image = root / relative
            image.parent.mkdir(parents=True)
            Image.new('RGB', (1200, 1800)).save(image)
            record = dict(file=relative, status='ok', padded=True, geometry=padding_geometry(100, 0, 1000, 1800))
            manifest = update_padding_queue(root, [record], 'test-job', {relative, 'legacy.jpg'})
            self.assertEqual(manifest['entries'][0]['sha256'], checksum(image))
            self.assertEqual(manifest['missing_geometry'], ['legacy.jpg'])
            self.assertIn(f'- `{relative}`\n', (workspace(root) / 'manual_patch_list.md').read_text(encoding='utf-8'))
            self.assertIn('left 100 px', (workspace(root) / 'manual_patch_list.md').read_text(encoding='utf-8'))
            self.assertTrue((workspace(root) / 'Start_Photoshop_Repair.cmd').is_file())
            self.assertTrue((workspace(root) / 'Start_Photoshop_Repair.ps1').is_file())
            self.assertNotIn('/*__JANVI_QUEUE__*/null', (workspace(root) / 'Repair_Padding.jsx').read_text(encoding='utf-8'))
            state = repair_status(root)
            self.assertEqual((state['total'], state['missing_geometry']), (1, 1))

    def test_failed_retry_preserves_geometry_but_successful_unpadded_replaces_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (1200, 1800)).save(root / 'image.png')
            record = dict(file='image.png', status='ok', padded=True, geometry=padding_geometry(100, 0, 1000, 1800))
            first = update_padding_queue(root, [record], 'first', {'image.png'})
            retry = update_padding_queue(root, [dict(file='image.png', status='failed')], 'retry', {'image.png'})
            self.assertEqual(first['fingerprint'], retry['fingerprint'])
            final = update_padding_queue(root, [dict(file='image.png', status='ok', padded=False)], 'new', set())
            self.assertEqual(final['entries'], [])

    def test_completed_report_is_read_without_hiding_original_padded_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (1200, 1800)).save(root / 'image.png')
            record = dict(file='image.png', status='ok', padded=True, geometry=padding_geometry(100, 0, 1000, 1800))
            manifest = update_padding_queue(root, [record], 'test', {'image.png'})
            (workspace(root) / manifest['report']).write_text(json.dumps(dict(status='completed', items=[dict(file='image.png', status='done')])) )
            self.assertEqual(repair_status(root)['report']['status'], 'completed')
            self.assertIn('- `image.png`', (workspace(root) / 'manual_patch_list.md').read_text())

    def test_review_api_serves_generated_script_and_completion_report(self):
        from app import app
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (1200, 1800)).save(root / 'image.png')
            record = dict(file='image.png', status='ok', padded=True, geometry=padding_geometry(100, 0, 1000, 1800))
            update_padding_queue(root, [record], 'test', {'image.png'})
            client = app.test_client()
            result = client.get('/api/photoshop/status', query_string=dict(dest_dir=str(root)))
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json['total'], 1)
            self.assertTrue(result.json['valid_script'])
            download = client.get('/api/photoshop/script', query_string=dict(dest_dir=str(root)))
            self.assertEqual(download.status_code, 200)
            self.assertIn('attachment', download.headers['Content-Disposition'])
            self.assertEqual(download.data, (workspace(root) / 'Repair_Padding.jsx').read_bytes())
            (workspace(root) / 'Repair_Padding.jsx').write_text('unexpected code', encoding='utf-8')
            self.assertFalse(client.get('/api/photoshop/status', query_string=dict(dest_dir=str(root))).json['valid_script'])
            download.close()

    def test_review_api_handles_legacy_output_without_script(self):
        from app import app
        with tempfile.TemporaryDirectory() as directory:
            client = app.test_client()
            self.assertFalse(client.get('/api/photoshop/status', query_string=dict(dest_dir=directory)).json['available'])
            self.assertEqual(client.get('/api/photoshop/script', query_string=dict(dest_dir=directory)).status_code, 404)

    def test_existing_root_queue_remains_readable_after_workspace_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (1200, 1800)).save(root / 'image.png')
            record = dict(file='image.png', status='ok', padded=True, geometry=padding_geometry(100, 0, 1000, 1800))
            update_padding_queue(root, [record], 'test', {'image.png'})
            queue = workspace(root)
            for file in queue.iterdir():
                file.replace(root / file.name)
            queue.rmdir()
            self.assertTrue(repair_status(root)['valid_script'])

    def test_processing_rejects_photoshop_locked_folders(self):
        from processing import validate_paths
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'input', root / 'output'
            source.mkdir()
            output.mkdir()
            (workspace(source) / '.janvi-photoshop-running').mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'Photoshop'):
                validate_paths(source, output)


if __name__ == '__main__':
    unittest.main()
