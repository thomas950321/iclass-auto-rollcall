import unittest
import copy
import contextvars
import troTHU.runtime_context as ctx
import troTHU.web_gui as web_gui

class TestSessionIsolation(unittest.TestCase):
    def setUp(self):
        # Initialize session isolation setup
        web_gui.setup_session_isolation()
        # Reset session states
        web_gui.USER_SESSIONS.clear()

    def test_session_isolation_config(self):
        # 1. Start with session A
        token_a = web_gui.CURRENT_SESSION_ID.set("session_A")
        try:
            state_a = web_gui.get_session_state("session_A")
            # Default value should be YOUR_STUDENT_ID
            self.assertEqual(ctx.CONFIG['accounts']['profiles']['default']['user'], 'YOUR_STUDENT_ID')
            
            # Update CONFIG in session A
            ctx.CONFIG['accounts']['profiles']['default']['user'] = 'student_A'
            ctx.CONFIG['accounts']['profiles']['default']['passwd'] = 'pass_A'
            ctx.CONFIG['provider']['current'] = 'thu'
            
            # Verify update took effect in session A
            self.assertEqual(ctx.CONFIG['accounts']['profiles']['default']['user'], 'student_A')
        finally:
            web_gui.CURRENT_SESSION_ID.reset(token_a)

        # 2. Switch to session B
        token_b = web_gui.CURRENT_SESSION_ID.set("session_B")
        try:
            state_b = web_gui.get_session_state("session_B")
            # Default value for session B should still be YOUR_STUDENT_ID (no bleeding!)
            self.assertEqual(ctx.CONFIG['accounts']['profiles']['default']['user'], 'YOUR_STUDENT_ID')
            
            # Update CONFIG in session B
            ctx.CONFIG['accounts']['profiles']['default']['user'] = 'student_B'
            ctx.CONFIG['accounts']['profiles']['default']['passwd'] = 'pass_B'
            
            # Verify update in session B
            self.assertEqual(ctx.CONFIG['accounts']['profiles']['default']['user'], 'student_B')
        finally:
            web_gui.CURRENT_SESSION_ID.reset(token_b)

        # 3. Check session A again to make sure it was not overwritten by B
        token_a = web_gui.CURRENT_SESSION_ID.set("session_A")
        try:
            self.assertEqual(ctx.CONFIG['accounts']['profiles']['default']['user'], 'student_A')
        finally:
            web_gui.CURRENT_SESSION_ID.reset(token_a)

    def test_session_isolation_logs(self):
        # Session A log append
        token_a = web_gui.CURRENT_SESSION_ID.set("session_A")
        try:
            ctx.append_gui_log("A was here")
            self.assertIn("A was here", ctx.GUI_LOGS)
        finally:
            web_gui.CURRENT_SESSION_ID.reset(token_a)

        # Session B log check
        token_b = web_gui.CURRENT_SESSION_ID.set("session_B")
        try:
            self.assertNotIn("A was here", ctx.GUI_LOGS)
            ctx.append_gui_log("B was here")
            self.assertIn("B was here", ctx.GUI_LOGS)
        finally:
            web_gui.CURRENT_SESSION_ID.reset(token_b)

    def test_session_isolation_cookies_mock(self):
        class DummySession:
            def __init__(self):
                self.cookie_jar = []

        token_a = web_gui.CURRENT_SESSION_ID.set("session_A")
        try:
            sess = DummySession()
            # Mock cookies inside cookie_jar
            class MockCookie:
                def __init__(self, key, val):
                    self.key = key
                    self.value = val
                def get(self, prop, default=None):
                    if prop == 'domain': return 'example.com'
                    return default

            sess.cookie_jar.append(MockCookie('foo', 'bar'))
            
            # Save cookies
            res_save = ctx.save_session_cookies(sess, None, 'default')
            self.assertTrue(res_save)
            
            # Check cookie cache in state
            state_a = web_gui.get_session_state("session_A")
            self.assertIn('default', state_a.cookie_cache)
            self.assertEqual(state_a.cookie_cache['default'][0]['key'], 'foo')
            self.assertEqual(state_a.cookie_cache['default'][0]['value'], 'bar')
        finally:
            web_gui.CURRENT_SESSION_ID.reset(token_a)

        # Session B should not see Session A's cookies
        token_b = web_gui.CURRENT_SESSION_ID.set("session_B")
        try:
            sess_b = DummySession()
            res_load = ctx.load_session_cookies(sess_b, None, 'default')
            # Should fail to load since session B has no cookies
            self.assertFalse(res_load)
            self.assertEqual(len(sess_b.cookie_jar), 0)
        finally:
            web_gui.CURRENT_SESSION_ID.reset(token_b)

    def test_session_fallback_when_no_session_id(self):
        # When CURRENT_SESSION_ID is None (e.g. standard CLI runs),
        # accessing ctx attributes should fall back to standard module dictionary values.
        self.assertIsNone(web_gui.CURRENT_SESSION_ID.get())
        
        # Write to ctx.IS_LOGGING_IN
        ctx.IS_LOGGING_IN = True
        self.assertTrue(ctx.IS_LOGGING_IN)
        
        # Clean up
        ctx.IS_LOGGING_IN = False
