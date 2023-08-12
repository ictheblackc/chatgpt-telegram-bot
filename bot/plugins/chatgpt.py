import os
import logging
import openai
import requests
import re
import tiktoken
from bot.config import Config as conf
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma


class ChatGPT:
    def __init__(self):
        pass

    @classmethod
    def set_key(cls):
        openai.api_key = conf.OPENAI_API_KEY
        os.environ['OPENAI_API_KEY'] = openai.api_key
        logging.info('OpenAI API key saved')

    @classmethod
    def load_search_indexes(cls, url: str) -> Chroma:
        # Extract the document ID from the URL
        match_ = re.search('/document/d/([a-zA-Z0-9-_]+)', url)
        if match_ is None:
            raise ValueError('Invalid Google Docs URL')
        doc_id = match_.group(1)

        # Download the document as plain text
        response = requests.get(f'https://docs.google.com/document/d/{doc_id}/export?format=txt')
        response.raise_for_status()
        text = response.text
        return cls.create_embedding(text)

    @classmethod
    def load_prompt(cls, url: str) -> str:
        # Extract the document ID from the URL
        match_ = re.search('/document/d/([a-zA-Z0-9-_]+)', url)
        if match_ is None:
            raise ValueError('Invalid Google Docs URL')
        doc_id = match_.group(1)

        # Download the document as plain text
        response = requests.get(f'https://docs.google.com/document/d/{doc_id}/export?format=txt')
        response.raise_for_status()
        text = response.text
        return f'{text}'

    @classmethod
    def num_tokens_from_string(cls, string: str, encoding_name: str) -> int:
        """Returns the number of tokens in a text string."""
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens

    @classmethod
    def create_embedding(cls, data):
        source_chunks = []
        splitter = CharacterTextSplitter(separator='\n', chunk_size=1024, chunk_overlap=0)

        for chunk in splitter.split_text(data):
            source_chunks.append(Document(page_content=chunk, metadata={}))

        search_index = Chroma.from_documents(source_chunks, OpenAIEmbeddings(), )
        count_token = cls.num_tokens_from_string(' '.join([x.page_content for x in source_chunks]), 'cl100k_base')
        request_cost = 0.0004 * (count_token / 1000)
        logging.info('Number of tokens in the document: {}'.format(count_token))
        logging.info('Approximate cost of the request: {}$'.format(request_cost))
        return search_index

    @classmethod
    def answer(cls, system, topic, temp=1):
        messages = [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': topic},
        ]

        completion = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=messages,
            temperature=temp
        )

        return completion.choices[0].message.content

    @classmethod
    def get_num_tokens_from_messages(cls, messages, model='gpt-3.5-turbo-0301'):
        """Returns the number of tokens used by a list of messages."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding('cl100k_base')
        if model == 'gpt-3.5-turbo-0301':
            num_tokens = 0
            for message in messages:
                num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))
                    if key == 'name':  # if there's a name, the role is omitted
                        num_tokens += -1  # role is always required and always 1 token
            num_tokens += 2  # every reply is primed with <im_start>assistant
            return num_tokens
        else:
            raise NotImplementedError(f"""get_num_tokens_from_messages() is not presently implemented for model {model}.
            See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are
            converted to tokens.""")

    @classmethod
    def insert_newlines(cls, text: str, max_len: int = 170) -> str:
        words = text.split()
        lines = []
        current_line = ''
        for word in words:
            if len(current_line + " " + word) > max_len:
                lines.append(current_line)
                current_line = ''
            current_line += ' ' + word
        lines.append(current_line)
        return '\n'.join(lines)

    @classmethod
    def answer_index(cls, system, topic, search_index, temp=1, verbose=0):
        """Select text by similarity with the query."""
        docs = search_index.similarity_search(topic, k=5)
        message_content = re.sub(r'\n{2}', ' ', '\n '.join(
            [f'\n\nDocument excerpt №{i + 1}\n\n' + doc.page_content + '\n' for i, doc in
             enumerate(docs)]))
        if verbose:
            print('\n\n', message_content)

        messages = [
            {'role': 'system', 'content': system + f"{message_content}"},
            {'role': 'user', 'content': topic},
        ]
        if verbose:
            print(f"\n{cls.get_num_tokens_from_messages(messages, 'gpt-3.5-turbo-0301')} tokens used per request.")
        completion = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=messages,
            temperature=temp
        )
        if verbose:
            print(f'\n{completion["usage"]["total_tokens"]} total tokens used.')
        if verbose:
            print('\nRequest cost :', 0.002 * (completion["usage"]["total_tokens"] / 1000), ' $\n')

        return cls.insert_newlines(completion.choices[0].message.content)


chatgpt = ChatGPT()
