import os
import unittest

from yt_dlp import YoutubeDL

from videodl.presets import OUTPUT_NAME, PRESETS, build_ydl_options, get_preset, playlist_number, safe_folder_name


class PresetOptionsTest(unittest.TestCase):
    def test_original_video_is_merged_into_mkv_without_reencoding(self):
        # Faza 2 (Ahmed 29.10.2026): kodeci sa sajta (VP9/AV1, Opus) samo spojeni u MKV, bez pretvaranja.
        opts = build_ydl_options(get_preset("original"), r"C:\Preuzimanja")
        self.assertEqual((opts["format"], opts["merge_output_format"], opts["format_sort"]), ("bv*+ba/b", "mkv", ["res"]))
        self.assertNotIn("postprocessors", opts)
        self.assertNotIn("final_ext", opts)

    def test_original_audio_keeps_the_codec_from_the_site(self):
        preset = get_preset("audio_original")
        self.assertTrue(preset.is_audio and preset.keeps_original_audio)
        opts = build_ydl_options(preset, r"C:\Preuzimanja")
        extract = opts["postprocessors"][0]
        self.assertEqual((extract["key"], extract["preferredcodec"]), ("FFmpegExtractAudio", "best"))
        self.assertNotIn("preferredquality", extract)
        self.assertNotIn("final_ext", opts)  # ekstenzija zavisi od kodeka (opus, m4a…)

    def test_clip_cut_is_precise_by_default_and_fast_on_request(self):
        precise = build_ydl_options(get_preset("best"), r"C:\P", section=(10.0, 20.0))
        fast = build_ydl_options(get_preset("best"), r"C:\P", section=(10.0, 20.0), precise_cut=False)
        self.assertTrue(precise["force_keyframes_at_cuts"])
        self.assertFalse(fast["force_keyframes_at_cuts"])
        self.assertIn("download_ranges", fast)

    def test_playlist_number_goes_in_front_of_the_name(self):
        self.assertEqual((playlist_number(3, 9), playlist_number(7, 120), playlist_number(12, 40)), ("03", "007", "12"))
        opts = build_ydl_options(get_preset("mp3"), r"C:\P", "Lista", number="03")
        self.assertTrue(opts["outtmpl"].endswith(os.sep + "03 - " + OUTPUT_NAME))
        self.assertNotIn("03 - ", build_ydl_options(get_preset("mp3"), r"C:\P", "Lista")["outtmpl"])

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

    def test_car_video_converts_to_avi_like_the_working_sample(self):
        # Prijateljev Audi Q5 (MMI) pušta AVI, MPEG-4 Part 2 (FMP4), 720×480, 25 fps, stereo MP3 44,1 kHz.
        opts = build_ydl_options(get_preset("car"), r"C:\Preuzimanja", thumbnail=True, subtitles=True, chapters=True)
        self.assertEqual([pp["key"] for pp in opts["postprocessors"]], ["FFmpegVideoConvertor"])
        self.assertEqual(opts["postprocessors"][0]["preferedformat"], "avi")
        self.assertEqual(opts["final_ext"], "avi")
        args = opts["postprocessor_args"]["videoconvertor"]
        for pair in (("-c:v", "mpeg4"), ("-vtag", "FMP4"), ("-c:a", "libmp3lame"), ("-ar", "44100"), ("-ac", "2")):
            self.assertIn(list(pair), [args[i:i + 2] for i in range(len(args) - 1)])
        self.assertIn("scale=720:480", args[args.index("-vf") + 1])
        self.assertIn("fps=25", args[args.index("-vf") + 1])
        self.assertNotIn("writesubtitles", opts)
        self.assertNotIn("writethumbnail", opts)

    def test_car_mp3_is_44khz_stereo_id3v23_without_cover_and_separate_name(self):
        opts = build_ydl_options(get_preset("mp3car"), r"C:\Preuzimanja", thumbnail=True, chapters=True)
        self.assertEqual([pp["key"] for pp in opts["postprocessors"]], ["FFmpegExtractAudio"])
        self.assertEqual(opts["postprocessor_args"]["extractaudio"], ["-ar", "44100", "-ac", "2", "-id3v2_version", "3"])
        self.assertEqual(opts["final_ext"], "mp3")
        self.assertTrue(opts["outtmpl"].endswith(" [car].%(ext)s"))  # ne zamijeni obični MP3 istog videa
        self.assertTrue(build_ydl_options(get_preset("mp3"), r"C:\P")["outtmpl"].endswith("[%(id)s].%(ext)s"))

    def test_output_template_escapes_percent_and_sanitizes_subfolder(self):
        opts = build_ydl_options(get_preset("best"), r"C:\100% video", subfolder="Moja/lista: dio?")
        folder, name = opts["outtmpl"].rsplit(os.sep, 1)
        self.assertEqual(name, OUTPUT_NAME)
        self.assertTrue(folder.startswith(r"C:\100%% video" + os.sep))
        subfolder = folder.rsplit(os.sep, 1)[1]
        for forbidden in '/:?':
            self.assertNotIn(forbidden, subfolder)

    def test_browser_stream_uses_page_title_and_headers(self):
        preset = get_preset("best")
        opts = build_ydl_options(preset, r"C:\d", http_headers={"Referer": "https://a.ba/"},
                                 filename_title="Lekcija: 100% <uvod>",
                                 source_url="https://cdn.a.ba/x/index.m3u8?token=1")
        name = opts["outtmpl"].rsplit(os.sep, 1)[1]
        self.assertTrue(name.endswith("].%(ext)s"))
        self.assertIn("100%%", name)
        for forbidden in ':<>':
            self.assertNotIn(forbidden, name)
        self.assertEqual(opts["http_headers"], {"Referer": "https://a.ba/"})

        # Potpis u linku se mijenja, putanja toka ne: ime fajla ostaje isto.
        same = build_ydl_options(preset, r"C:\d", filename_title="Lekcija: 100% <uvod>",
                                 source_url="https://cdn.a.ba/x/index.m3u8?token=2")
        other = build_ydl_options(preset, r"C:\d", filename_title="Lekcija: 100% <uvod>",
                                  source_url="https://cdn.a.ba/y/index.m3u8")
        self.assertEqual(opts["outtmpl"], same["outtmpl"])
        self.assertNotEqual(opts["outtmpl"], other["outtmpl"])

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
