from textwrap import dedent
from unittest.mock import Mock, patch

from .common import ForwardBotCase, MockResponse


class TestMergeRequest(ForwardBotCase):
    def test_01_obtain_from_event_create(self):
        payload = self._gen_payload(50)
        merge_request, created = self.model_mr.gitlab_obtain_from_event(payload)

        self.assertMergeRequestEqual(payload, merge_request)
        self.assertTrue(created)

    def test_02_obtain_from_event_read(self):
        payload = self._gen_payload(56)

        merge_request, created = self.model_mr.gitlab_obtain_from_event(payload)
        self.assertTrue(created)

        read_mr, created = self.model_mr.gitlab_obtain_from_event(payload)
        self.assertEqual(merge_request, read_mr)
        self.assertFalse(created)

    def test_03_create_from_event_bad_payload(self):
        bad_payload = {
            "object_attributes": {
                "id": 99,
                "target_branch": "master",
            }
        }

        with self.assertRaises(KeyError):
            self.env["fwbot.merge.request"].gitlab_obtain_from_event(bad_payload)

    def test_04_create_forward_port(self):
        merge_request, _ = self.model_mr.gitlab_obtain_from_event(self._gen_payload(80))
        merge_request.create_forward_port()

        self.assertEqual(merge_request.target_branch, "11.0")
        self.assertEqual(merge_request.forward_port_id.target_branch, "12.0")
        self.assertIn(
            f"This is an automatic forward port for !{merge_request.internal_id}",
            merge_request.forward_port_id.description,
        )

        description = dedent(
            """
        This is a merge request with a descriptive and elaborate
        multiline description. I surely hope the correct information
        is modified for resulting forward ports.

        ---
        This is an automatic forward port for !911
        """
        )
        merge_request, _ = self.model_mr.gitlab_obtain_from_event(self._gen_payload(761, description=description))
        merge_request.create_forward_port()

        self.assertNotIn("This is an automatic forward port for !911", merge_request.forward_port_id.description)
        self.assertIn(
            f"This is an automatic forward port for !{merge_request.internal_id}",
            merge_request.forward_port_id.description,
        )

    def test_05_forward_port_not_repeated(self):
        merge_request, _ = self.model_mr.gitlab_obtain_from_event(self._gen_payload(85))

        original_id = merge_request.create_forward_port().id
        self.assertTrue(original_id)

        second_call_id = merge_request.create_forward_port().id
        self.assertEqual(original_id, second_call_id)

    def test_06_prune_merge_request_invalid_target(self):
        merge_request, _ = self.model_mr.gitlab_obtain_from_event(self._gen_payload(99, target_branch="rando"))
        merge_request.target_repository_id.stable_branches = "15.0"

        self.assertEqual(self.env["fwbot.merge.request"].search_count([("id", "=", merge_request.id)]), 1)
        merge_request.prune_merge_requests()
        self.assertEqual(self.env["fwbot.merge.request"].search_count([("id", "=", merge_request.id)]), 0)

    @patch("odoo.addons.fwbot.models.fwbot_merge_request.ForwardbotGitlabClient.get")
    @patch("odoo.addons.fwbot.models.fwbot_merge_request.ForwardbotGitlabClient.send")
    @patch("odoo.addons.fwbot.models.fwbot_merge_request.ForwardbotGitlabClient.delete")
    @patch("odoo.addons.fwbot.models.fwbot_merge_request.ForwardbotGitlabClient.post")
    def test_07_process_pending_for_forward_ports(
        self, post_mock: Mock, delete_mock: Mock, push_mock: Mock, get_mock: Mock
    ):
        post_mock.side_effect = lambda *args, **kwargs: MockResponse(status_code=200, ok=True)
        delete_mock.side_effect = lambda *args, **kwargs: MockResponse(status_code=200)
        push_mock.side_effect = lambda *args, **kwargs: MockResponse(
            status_code=200, json_data={"id": 567, "iid": 889, "state": "opened"}
        )
        get_mock.side_effect = lambda *args, **kwargs: MockResponse(
            status_code=200, json_data=[{"id": "kiwi"}, {"id": "mango"}]
        )

        merge_request, _ = self.model_mr.gitlab_obtain_from_event(self._gen_payload(753, target_branch="saas-17"))
        merge_request.state = "merged"

        repo_data = {"url": "https://git.local", "token": "trusty", "stable_branches": "15.0,saas-17,master"}
        merge_request.target_repository_id.write(repo_data)
        merge_request.source_repository_id.write(repo_data)

        merge_request.gitlab_process_pending_for_forward_ports()

        self.assertEqual(post_mock.call_count, 3)
        self.assertEqual(merge_request.forward_port_id.global_id, 567)
        self.assertEqual(merge_request.forward_port_id.internal_id, 889)
        self.assertEqual(merge_request.forward_port_id.state, "opened")
        self.assertEqual(merge_request.forward_port_id.target_branch, "master")
