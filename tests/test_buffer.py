"""The Buffer login and channel choice. No network: run with python -B -m unittest discover -s tests"""
import io
import os
import unittest
from unittest import mock

from studio import buffer

CHANS = [
    {"id": "yt1", "service": "youtube", "name": "Owner"},
    {"id": "ig1", "service": "instagram", "name": "ownerclips"},
    {"id": "yt2", "service": "youtube", "name": "Client"},
    {"id": "tt1", "service": "tiktok", "name": "client.tok"},
]


class KeyVar(unittest.TestCase):
    def test_label_becomes_variable_name(self):
        self.assertEqual(buffer.key_var("client"), "BUFFER_API_KEY_CLIENT")
        self.assertEqual(buffer.key_var("my-shop_2"), "BUFFER_API_KEY_MY_SHOP_2")
        self.assertEqual(buffer.key_var("a b.c"), "BUFFER_API_KEY_A_B_C")


class UseLogin(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, buffer, "KEY_VAR", buffer.KEY_VAR)

    def test_missing_key_stops_and_never_falls_back(self):
        with mock.patch.dict(os.environ, {"BUFFER_API_KEY": "main-key"}, clear=True):
            with self.assertRaises(SystemExit) as stop:
                buffer.use_login("client")
        self.assertIn("BUFFER_API_KEY_CLIENT", str(stop.exception))
        self.assertNotIn("main-key", str(stop.exception))
        self.assertEqual(buffer.KEY_VAR, "BUFFER_API_KEY")

    def test_calls_carry_the_key_of_the_label(self):
        answer = mock.MagicMock()
        answer.__enter__.return_value = io.BytesIO(b'{"data": {"ok": true}}')
        env = {"BUFFER_API_KEY": "main-key", "BUFFER_API_KEY_CLIENT": "client-key"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("urllib.request.urlopen", return_value=answer) as sent:
            buffer.use_login("client")
            self.assertEqual(buffer.gql("query { ok }"), {"ok": True})
        self.assertEqual(sent.call_args[0][0].get_header("Authorization"), "Bearer client-key")


class PickChannels(unittest.TestCase):
    def ids(self, *a):
        return [c["id"] for c in buffer.pick_channels(CHANS, *a)]

    def test_services_only_is_the_old_behaviour(self):
        self.assertEqual(self.ids("YouTube, instagram"), ["yt1", "ig1", "yt2"])

    def test_ids_narrow_the_services(self):
        self.assertEqual(self.ids("youtube,instagram", "yt2"), ["yt2"])
        self.assertEqual(self.ids("youtube,instagram", " ig1 , yt2 "), ["ig1", "yt2"])

    def test_no_channel_left(self):
        for args in (("facebook",), ("youtube", "nope"), ("youtube", "tt1")):
            with self.assertRaises(ValueError):
                buffer.pick_channels(CHANS, *args)

    def test_an_id_that_cannot_be_used_stops(self):
        # A wrong id, an id of a service that --services left out, and a value with no id in it.
        for ids in ("yt1,ig-typo", "yt1,tt1", " , "):
            with self.assertRaises(ValueError):
                buffer.pick_channels(CHANS, "youtube,instagram", ids)
        with self.assertRaises(ValueError) as stop:
            buffer.pick_channels(CHANS, "youtube,instagram", "yt1,ig-typo")
        self.assertIn("ig-typo", str(stop.exception))
        self.assertNotIn("yt1", str(stop.exception))

    def test_two_channels_of_one_service(self):
        with self.assertRaises(ValueError) as stop:
            buffer.pick_channels(CHANS, "youtube,instagram", "yt1,yt2")
        self.assertIn("one channel per service", str(stop.exception))


if __name__ == "__main__":
    unittest.main()
