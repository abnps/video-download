import os
import unittest

from yt_dlp import YoutubeDL

from videodl.presets import OUTPUT_NAME, PRESETS, build_ydl_options, get_preset, safe_folder_name


class PresetOptionsTest(unittest.TestCase):
    def test_video_preset_merges_to_mp4_without_postprocessing(self):
        opts = build_ydl_options(get_preset("1080p"), r"C:\Preuzimanja")
        self.assertEqual(opts["format"], "bv*+ba/b")
        self.assertEqual(opts["merge_output_format"], "mp4")
        self.assertEqual(opts["format_sort"][0], "res:1080")
        self.assertIn("vcodec:h264", opts["format_sort"])
        self.assertNotIn("postprocessors", opts)
        self.assertTrue(opts["noplaylist"])

    def test_audio_presets_extract_audio_and_set_final_ext(self):
        for key, codec in (("mp3", "mp3"), ("m4a", "m4a")):
            opts = build_ydl_options(get_preset(key), r"C:\Preuzimanja")
            self.assertEqual(opts["postprocessors"][0]["key"], "FFmpegExtractAudio")
            self.assertEqual(opts["postprocessors"][0]["preferredcodec"], codec)
            self.assertEqual(opts["final_ext"], codec)
            self.assertNotIn("merge_output_format", opts)

    def test_output_template_escapes_percent_and_sanitizes_subfolder(self):
        opts = build_ydl_options(get_preset("best"), r"C:\100% video", subfolder="Moja/lista: dio?")
        folder, name = opts["outtmpl"].rsplit(os.sep, 1)
        self.assertEqual(name, OUTPUT_NAME)
        self.assertTrue(folder.startswith(r"C:\100%% video" + os.sep))
        subfolder = folder.rsplit(os.sep, 1)[1]
        for forbidden in '/:?':
            self.assertNotIn(forbidden, subfolder)

    def test_js_runtimes_include_node(self):
        opts = build_ydl_options(get_preset("best"), r"C:\Preuzimanja")
        self.assertIn("node", opts["js_runtimes"])

    def test_every_preset_is_accepted_by_yt_dlp(self):
        for preset in PRESETS:
            with self.subTest(preset=preset.key):
                with YoutubeDL(build_ydl_options(preset, r"C:\Preuzimanja")) as ydl:
                    self.assertEqual(ydl.params["format"], preset.format)

    def test_safe_folder_name_falls_back_and_trims(self):
        self.assertEqual(safe_folder_name(""), "Plejlista")
        self.assertEqual(safe_folder_name("..."), "Plejlista")
        self.assertLessEqual(len(safe_folder_name("x" * 300)), 80)

    def test_unknown_preset_raises(self):
        with self.assertRaises(KeyError):
            get_preset("nepostoji")


if __name__ == "__main__":
    unittest.main()
