import openai
from decouple import config

from ai_config import prompts, banned_words


async def generate_ai_answer(text: str) -> str:
    """Generates AI answer based on post text"""

    if not config('OPENAI_API_KEY', default=''):
        return 'Ok!'

    ai_answer = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[{
                'role': 'assistant', 'content': 'You are a helpful assistant.'
            },
            {
                'role': 'user', 'content': f'{prompts[config("PROMPT_LANGUAGE", "ru")]}{text}'
            }
        ]
    )
    ai_text = ai_answer['choices'][0]['message']['content']
    ban_words = banned_words[config('PROMPT_LANGUAGE', 'ru')]
    ban_words += [i.upper() for i in ban_words] + [i.capitalize() for i in ban_words]
    [ai_text.replace(i, '***') for i in ban_words]
    return ai_text
