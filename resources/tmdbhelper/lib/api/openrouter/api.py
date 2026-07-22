from tmdbhelper.lib.addon.plugin import get_setting
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper.lib.api.gemini.api import BaseAIRecommender


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_FREE_MODEL_ID = "openrouter/free"  # auto-routes to a currently-available free model


class OpenRouter(BaseAIRecommender):

    api_key = get_setting('openrouter_apikey', 'str')

    def __init__(self, api_key=None):
        api_key = api_key or self.api_key

        super(OpenRouter, self).__init__(
            req_api_name='OpenRouter',
            req_api_url=OPENROUTER_API_URL,
            timeout=30,
        )

        OpenRouter.api_key = api_key

    @property
    def headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    @headers.setter
    def headers(self, value):
        """ Ignore base class req_api attempting to set headers """
        return

    def get_prompt_postdata(self, prompt_text):
        return {
            "model": OPENROUTER_FREE_MODEL_ID,
            "messages": [
                {"role": "user", "content": prompt_text}
            ]
        }

    @staticmethod
    def get_candidates(data):
        try:
            return data['choices'][0]['message']['content'].strip()
        except (TypeError, IndexError, KeyError, AttributeError):
            kodi_log(f'OpenRouter FAILED: Unable to get message content', 1)
            return
