import json

from odoo.tests.common import HttpCase

from .common import ForwardBotCase


class TestWebhook(HttpCase, ForwardBotCase):
    test_tags = {"standard", "post_install"}  # TODO: DELETE ME, I DON'T EXIST IN ODOO11
    post_install = True
    at_install = False

    gitlab_headers = {
        "user-agent": "GitLab/16.0.4",
        "accept": "*/*",
        "accept-encoding": "gzip;q=1.0,deflate;q=0.6,identity;q=0.3",
        "content-type": "application/json",
        "x-gitlab-event": "Merge Request Hook",
        "x-gitlab-event-uuid": "ded5ab40-709c-4551-a13b-4a684b8b2703",
        "x-gitlab-instance": "https://git.vauxoo.com",
    }

    def send_payload(self, payload):
        return self.url_open("/fwbot_gitlab", data=json.dumps(payload), headers=self.gitlab_headers)

    def test_01_create_mr(self):
        payload = self._gen_payload(150)
        response = self.send_payload(payload)
        self.assertEqual(response.status_code, 200)

        merge_request = self.model_mr.search([("global_id", "=", 150)])
        self.assertMergeRequestEqual(payload, merge_request)

    def test_02_update_mr(self):
        payload = self._gen_payload(55)
        response = self.send_payload(payload)
        self.assertEqual(response.status_code, 200)

        merge_request = self.model_mr.search([("global_id", "=", 55)])
        self.assertMergeRequestEqual(payload, merge_request)

        updated_payload = self._gen_payload(55, action="update", title="Just updated this")
        response = self.send_payload(updated_payload)
        self.assertEqual(response.status_code, 200)
        self.assertMergeRequestEqual(updated_payload, self.model_mr.browse([merge_request.id]))
