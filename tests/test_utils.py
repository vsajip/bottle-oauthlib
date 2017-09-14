import bottle
from bottle_oauthlib import oauth2
import unittest


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class extract_params_auth(unittest.TestCase):
    def setUp(self):
        self.request = AttrDict({
            "method": "GET",
            "url": "/sample_url",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"
            },
            "forms": {},
            "body": "{}",
            "auth": None
        })

    def test_empty(self):
        self.request.auth = (None, None)
        _, _, forms, headers = oauth2.extract_params(self.request)
        self.assertNotIn("client_id", forms)
        self.assertNotIn("client_secret", forms)
        self.assertNotIn("Authorization", headers)

    def test_auth_user(self):
        self.request.auth = ("foobar", None)
        _, _, forms, headers = oauth2.extract_params(self.request)
        self.assertEqual(forms["client_id"], "foobar")
        self.assertNotIn("client_secret", forms)
        self.assertNotIn("Authorization", headers)

    def test_auth_user_password_empty(self):
        self.request.auth = ("foobar", "")
        _, _, forms, headers = oauth2.extract_params(self.request)
        self.assertEqual(forms["client_id"], "foobar")
        self.assertEqual(forms["client_secret"], "")
        self.assertNotIn("Authorization", headers)

    def test_auth_password(self):
        self.request.auth = (None, "barsecret")
        _, _, forms, headers = oauth2.extract_params(self.request)
        self.assertNotIn("client_id", forms)
        self.assertEqual(forms["client_secret"], "barsecret")
        self.assertNotIn("Authorization", headers)

    def test_auth_user_password(self):
        self.request.auth = ("foobar", "barsecret")
        _, _, forms, headers = oauth2.extract_params(self.request)
        self.assertEqual(forms["client_id"], "foobar")
        self.assertEqual(forms["client_secret"], "barsecret")
        self.assertNotIn("Authorization", headers)

    def test_payload_user(self):
        self.request.forms["client_id"] = "foobar"
        _, _, forms, headers = oauth2.extract_params(self.request)
        self.assertEqual(forms["client_id"], "foobar")
        self.assertNotIn("client_secret", forms)
        self.assertNotIn("Authorization", headers)

    def test_payload_user_password_empty(self):
        self.request.forms["client_id"] = "foobar"
        self.request.forms["client_secret"] = ""
        _, _, forms, headers = oauth2.extract_params(self.request)
        self.assertEqual(forms["client_id"], "foobar")
        self.assertEqual(forms["client_secret"], "")
        self.assertNotIn("Authorization", headers)

    def test_payload_password(self):
        self.request.forms["client_secret"] = "barsecret"
        _, _, forms, headers = oauth2.extract_params(self.request)
        self.assertNotIn("client_id", forms)
        self.assertEqual(forms["client_secret"], "barsecret")
        self.assertNotIn("Authorization", headers)

    def test_payload_user_password(self):
        self.request.forms["client_id"] = "foobar"
        self.request.forms["client_secret"] = "barsecret"
        _, _, forms, headers = oauth2.extract_params(self.request)
        self.assertEqual(forms["client_id"], "foobar")
        self.assertEqual(forms["client_secret"], "barsecret")
        self.assertNotIn("Authorization", headers)

    def test_payload_overload_auth(self):
        self.request.auth = ("foobar", "barsecret")
        self.request.forms["client_id"] = "bigger_foobar"
        self.request.forms["client_secret"] = "bigger_barsecret"
        _, _, forms, headers = oauth2.extract_params(self.request)
        self.assertEqual(forms["client_id"], "bigger_foobar")
        self.assertEqual(forms["client_secret"], "bigger_barsecret")
        self.assertNotIn("Authorization", headers)

    def test_noforms_auth_user_password(self):
        """POSTed body is not a forms, so we need to decode authorization
        ourselves.
        """
        self.request.headers["Content-Type"] = "text/html"
        self.request.body = "<html>"
        self.request.auth = ("foobar", "barsecret")
        _, _, body, headers = oauth2.extract_params(self.request)
        self.assertEqual(body, "<html>")
        self.assertIn("Authorization", headers)

        import bottle
        client_id, client_secret = bottle.parse_auth(headers["Authorization"])
        self.assertEqual(client_id, "foobar")
        self.assertEqual(client_secret, "barsecret")


class add_params(unittest.TestCase):
    def setUp(self):
        self.request = AttrDict()

    def test_none(self):
        oauth2.add_params(self.request, None)
        self.assertIn("oauth", self.request)

    def test_empty(self):
        oauth2.add_params(self.request, {})
        self.assertIn("oauth", self.request)

    def test_simple(self):
        oauth2.add_params(self.request, {
            "foo": "bar",
            "lot": {
                "of": "things",
                "no": 42
            }
        })
        self.assertIn("oauth", self.request)
        self.assertEqual(self.request.oauth["foo"], "bar")
        self.assertEqual(self.request.oauth["lot"]["of"], "things")
        self.assertEqual(self.request.oauth["lot"]["no"], 42)


class set_response(unittest.TestCase):
    def setUp(self):
        self.request = AttrDict({
            "headers": {
            }
        })
        self.response = bottle.LocalResponse()

    def test_wrong_status(self):
        try:
            oauth2.set_response(self.request, self.response, {}, {}, "body")
        except ValueError:
            self.assertTrue(True)
        else:
            self.assertTrue(False, "must raise an error cuz not a valid HTTP status_code")

    def test_wrong_headers(self):
        try:
            oauth2.set_response(self.request, self.response, 200, "string", "body")
        except TypeError:
            self.assertTrue(True)
        else:
            self.assertTrue(False, "must raise an error cuz headers is not a valid dict")

    def test_wrong_body(self):
        try:
            oauth2.set_response(self.request, self.response, 200, {}, {})
        except TypeError:
            self.assertTrue(True)
        else:
            self.assertTrue(False, "must raise an error cuz body is not a valid string")

    def test_resp_headers(self):
        oauth2.set_response(self.request, self.response, 200, {
            "foo": "bar",
            "banana": "ananab"
        }, "")
        self.assertEqual(self.response.headers["foo"], "bar")
        self.assertEqual(self.response.headers["banana"], "ananab")

    def test_resp_body_string(self):
        oauth2.set_response(
            self.request, self.response, 200,
            {"Content-Type": "text/html"},
            "foobar"
        )
        self.assertEqual(self.response["Content-Type"], "text/html")
        self.assertEqual(self.response.body, "foobar")

    def test_resp_body_json_accept_json(self):
        self.request.headers["Accept"] = "application/json"
        oauth2.set_response(
            self.request, self.response, 200,
            {"Content-Type": "application/json; charset=utf-8"},
            '{"foo": "bar", "bar": "foo"}'
        )
        self.assertIn("application/json", self.response["Content-Type"])
        self.assertEqual(self.response.body, '{"foo": "bar", "bar": "foo"}')

    def test_resp_body_json_accept_all_single_item(self):
        self.request.headers["Accept"] = "*/*"
        oauth2.set_response(
            self.request, self.response, 200,
            {"Content-Type": "application/json; charset=utf-8"},
            '{"foo": "bar"}'
        )
        self.assertIn("application/x-www-form-urlencoded", self.response["Content-Type"])
        self.assertEqual(self.response.body, 'foo=bar')

    def test_resp_body_json_accept_all_multi_item(self):
        self.request.headers["Accept"] = "*/*"
        oauth2.set_response(
            self.request, self.response, 200,
            {"Content-Type": "application/json; charset=utf-8"},
            '{"foo": "bar", "bar": 42}'
        )
        self.assertIn("application/x-www-form-urlencoded", self.response["Content-Type"])
        self.assertEqual(self.response.body, 'foo=bar&bar=42')

    def test_resp_body_json_accept_all_encoded_item(self):
        self.request.headers["Accept"] = "*/*"
        oauth2.set_response(
            self.request, self.response, 200,
            {"Content-Type": "application/json; charset=utf-8"},
            '{"foo": "bar", "bar": "http://foo?bar#fragment"}'
        )
        self.assertIn("application/x-www-form-urlencoded", self.response["Content-Type"])
        self.assertEqual(self.response.body, 'foo=bar&bar=http%3A//foo%3Fbar%23fragment')