import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import base64
import bot

class TestBotUtils(unittest.TestCase):

    def test_random_string(self):
        s = bot.random_string(10)
        self.assertEqual(len(s), 10)
        self.assertTrue(s.isalnum())

    def test_detect_otp(self):
        self.assertEqual(bot.detect_otp("Your code is 1234"), "1234")
        self.assertEqual(bot.detect_otp("Code: 123456"), "123456")
        self.assertEqual(bot.detect_otp("12345678"), "12345678")
        self.assertIsNone(bot.detect_otp("123")) # Too short
        self.assertIsNone(bot.detect_otp("123456789")) # Too long
        self.assertIsNone(bot.detect_otp("abc"))

    def test_recovery_token(self):
        data = {"email": "test@example.com", "password": "pass", "token": "jwt"}
        token = bot.encode_recovery_token(data)
        decoded = bot.decode_recovery_token(token)
        self.assertEqual(data, decoded)

class TestMailTM(unittest.TestCase):

    @patch('bot.requests.get')
    def test_get_domains(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"hydra:member": [{"domain": "example.com"}]}
        mock_get.return_value = mock_response

        domains = bot.get_domains()
        self.assertEqual(domains, ["example.com"])

    @patch('bot.requests.post')
    def test_create_account(self, mock_post):
        mock_response = MagicMock()
        mock_post.return_value = mock_response

        bot.create_account("test@example.com", "password")
        mock_post.assert_called_with(
            f"{bot.MAILTM_BASE}/accounts",
            json={"address": "test@example.com", "password": "password"},
            timeout=10
        )

    @patch('bot.requests.post')
    def test_get_token(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "jwt_token"}
        mock_post.return_value = mock_response

        token = bot.get_token("test@example.com", "password")
        self.assertEqual(token, "jwt_token")

class TestBotCommands(unittest.IsolatedAsyncioTestCase):

    async def test_new_email(self):
        with patch('bot.get_domains', return_value=["example.com"]), \
             patch('bot.create_account') as mock_create, \
             patch('bot.get_token', return_value="jwt_token"):

            update = MagicMock()
            update.effective_user.id = 123
            update.message.reply_text = AsyncMock()
            context = MagicMock()

            await bot.new_email(update, context)

            self.assertIn(123, bot.ACTIVE_SESSIONS)
            self.assertEqual(bot.ACTIVE_SESSIONS[123]['token'], "jwt_token")
            update.message.reply_text.assert_called()

    async def test_repair(self):
        update = MagicMock()
        update.effective_user.id = 456
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        data = {"email": "old@example.com", "password": "pass", "token": "old_jwt"}
        token = bot.encode_recovery_token(data)
        context.args = [token]

        await bot.repair(update, context)

        self.assertIn(456, bot.ACTIVE_SESSIONS)
        self.assertEqual(bot.ACTIVE_SESSIONS[456]['email'], "old@example.com")

    async def test_read_no_session(self):
        update = MagicMock()
        update.effective_user.id = 999
        update.message.reply_text = AsyncMock()
        bot.ACTIVE_SESSIONS = {} # Clear sessions
        context = MagicMock()

        await bot.read(update, context)

        update.message.reply_text.assert_called_with("No active inbox.\nUse /new or /repair <token>.")

    async def test_read_with_messages(self):
        bot.ACTIVE_SESSIONS[777] = {"token": "jwt", "email": "test", "password": "pass"}

        with patch('bot.fetch_messages', return_value=[{"id": "msg1"}]), \
             patch('bot.read_message', return_value={"text": "Your OTP is 1234", "from": {"address": "sender"}, "subject": "Hi"}), \
             patch('bot.delete_message') as mock_delete:

            update = MagicMock()
            update.effective_user.id = 777
            update.message.reply_text = AsyncMock()
            context = MagicMock()

            await bot.read(update, context)

            mock_delete.assert_called_with("jwt", "msg1")
            args, kwargs = update.message.reply_text.call_args
            self.assertIn("*OTP*: `1234`", args[0])

if __name__ == '__main__':
    unittest.main()
