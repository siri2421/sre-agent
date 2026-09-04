import os
import sys
import time
import uuid
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock streamlit if not installed in current environment
try:
    import streamlit
except ImportError:
    from unittest.mock import MagicMock
    class SessionStateMock(dict):
        def __getattr__(self, item):
            try:
                return self[item]
            except KeyError:
                raise AttributeError(item)
        def __setattr__(self, key, value):
            self[key] = value

    mock_st = MagicMock()
    mock_st.session_state = SessionStateMock()
    mock_cache = MagicMock()
    mock_cache.return_value = lambda f: f
    mock_cache.clear = MagicMock()
    mock_st.cache_data = mock_cache
    mock_st.tabs = lambda titles: [MagicMock() for _ in titles]
    mock_st.columns = lambda spec: [MagicMock() for _ in (spec if isinstance(spec, list) else range(spec))]
    sys.modules["streamlit"] = mock_st

from app.config import (
    PROJECT_ID,
    TELEMETRY_BUCKET,
    upload_gcs_file,
    list_gcs_files,
    read_gcs_file,
    save_postmortem_to_gcs
)
from app.investigator_agent import (
    incident_report_writer,
    rca_telemetry_expert,
    write_gcs_file,
    upload_postmortem_report,
    list_gcs_reports
)

class TestPostmortemWorkflow(unittest.TestCase):

    def test_gcs_config_and_bucket(self):
        self.assertTrue(len(TELEMETRY_BUCKET) > 0)
        self.assertFalse(TELEMETRY_BUCKET.startswith('gs://'))
        print(f'✅ TELEMETRY_BUCKET resolved: {TELEMETRY_BUCKET}')

    def test_gcs_upload_read_list_live(self):
        test_id = f"TEST-{uuid.uuid4().hex[:8]}"
        test_content = f"# Post-Mortem Verification Report\n\nIncident ID: {test_id}\nStatus: RESOLVED\nTelemetry verification test."
        
        gcs_uri = save_postmortem_to_gcs(test_content, incident_id=test_id)
        self.assertTrue(gcs_uri.startswith('gs://'), f'Failed GCS upload: {gcs_uri}')
        self.assertIn(test_id, gcs_uri)
        print(f'✅ Successfully archived postmortem: {gcs_uri}')
        
        files = list_gcs_files(TELEMETRY_BUCKET, prefix='reports/')
        self.assertTrue(len(files) > 0, 'Expected at least one file in GCS reports/')
        file_names = [f.get('name') for f in files]
        target_obj = f'reports/post_mortem_{test_id}.md'
        self.assertIn(target_obj, file_names, f'Expected {target_obj} in {file_names}')
        print(f'✅ Successfully listed postmortem from GCS archive ({len(files)} total files)')
        
        read_back = read_gcs_file(TELEMETRY_BUCKET, target_obj)
        self.assertIn(test_id, read_back)
        self.assertIn('RESOLVED', read_back)
        print(f'✅ Successfully read back archived postmortem content ({len(read_back)} chars)')

    def test_agent_tools_registered(self):
        writer_tool_names = [getattr(t, '__name__', getattr(t, 'name', str(t))) for t in incident_report_writer.tools]
        self.assertIn('upload_postmortem_report', writer_tool_names)
        self.assertIn('write_gcs_file', writer_tool_names)
        self.assertIn('list_gcs_reports', writer_tool_names)
        print(f'✅ incident_report_writer has GCS tools: {writer_tool_names}')

        rca_tool_names = [getattr(t, '__name__', getattr(t, 'name', str(t))) for t in rca_telemetry_expert.tools]
        self.assertIn('upload_postmortem_report', rca_tool_names)
        self.assertIn('write_gcs_file', rca_tool_names)
        print(f'✅ rca_telemetry_expert has postmortem tools: {rca_tool_names}')

    def test_ui_async_postmortem_thread(self):
        from ui.streamlit_app import trigger_async_postmortem, _ASYNC_REPORTS_STORE
        
        test_key = str(uuid.uuid4())
        test_details = 'Test Auto-Remediation executed for frontend scale recovery. GKE pods restored to 1/1.'
        
        trigger_async_postmortem(test_key, test_details, incident_id=f'TEST-ASYNC-{test_key[:6]}')
        self.assertIn(test_key, _ASYNC_REPORTS_STORE)
        self.assertEqual(_ASYNC_REPORTS_STORE[test_key]['status'], 'IN_PROGRESS ⏳')
        print(f'✅ Triggered async postmortem thread for key: {test_key}')

if __name__ == '__main__':
    unittest.main()
