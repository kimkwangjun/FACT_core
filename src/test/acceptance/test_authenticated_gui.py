import pytest

from test.acceptance.auth_base import TestAuthenticatedAcceptanceBase


class TestAcceptanceNormalSearch(TestAuthenticatedAcceptanceBase):

    def test_redirection(self):
        response = self.test_client.get('/', follow_redirects=False)
        self.assertIn(b'Redirecting', response.data, 'no redirection taking place')

    def test_show_login_page(self):
        response = self.test_client.get('/', follow_redirects=True)
        self.assertIn(b'Remember Me', response.data, 'no authorization required')

    def test_api_key_auth(self):
        response = self.test_client.get('/', headers={'Authorization': self.guest.key}, follow_redirects=True)
        self.assertNotIn(b'Remember Me', response.data, 'authorization not working')

    def test_role_based_access(self):
        self._start_backend()
        response = self.test_client.get('/upload', headers={'Authorization': self.guest.key}, follow_redirects=True)
        self.assertIn(b'Remember Me', response.data, 'upload should not be accessible for guest')

        response = self.test_client.get('/upload', headers={'Authorization': self.guest_analyst.key}, follow_redirects=True)
        self.assertIn(b'Remember Me', response.data, 'upload should not be accessible for guest_analyst')

        response = self.test_client.get('/upload', headers={'Authorization': self.superuser.key}, follow_redirects=True)
        self.assertNotIn(b'Remember Me', response.data, 'upload should not be accessible for guest')
        self._stop_backend()

    def test_login(self):
        '''
        As of now, not working in tests. Can not yet determine the reason. Maybe bad creation of request.
        Does not apply to production code though.
        Writing tests for this is postponed for now.
        '''
        pass

    def test_all_endpoints_need_authentication(self):
        for endpoint_rule in list(self.frontend.app.url_map.iter_rules()):
            endpoint = endpoint_rule.rule.replace('<>', '')

            with self.subTest(endpoint=endpoint):
                response = self.test_client.get(endpoint, follow_redirects=True)
                if b'404 Not Found' in response.data or b'405 Method Not Allowed' in response.data:
                    response = self.test_client.put(endpoint, follow_redirects=True)
                    if b'404 Not Found' in response.data or b'405 Method Not Allowed' in response.data:
                        response = self.test_client.post(endpoint, follow_redirects=True)

                if endpoint.startswith('/static'):
                    pass  # static routes should be served without auth so that css and logos are shown in login screen
                else:
                    self.assertIn(b'Remember Me', response.data, 'no authorization required {}'.format(endpoint))
