import datetime
import io
import os
import sys
from time import sleep

import imagehash

from unittest import IsolatedAsyncioTestCase, mock
from unittest.mock import patch

from PIL import Image
from PIL.JpegImagePlugin import JpegImageFile

import main

from dallemini_command import convert_base64_strings_to_images, get_3x3_image_compilation, \
    get_given_prompt, send_image_response, split_to_chunks, get_image_file_name
from test.resources.images_base64_dummy import base64_dummy_images
from test_main import MockUpdate

sys.path.append('../web')  # needed for sibling import
import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "web.settings"
)
from django.conf import settings

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()


class Test(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.system("python ../web/manage.py migrate")

    def test_dallemini_command_no_prompt(self):
        update = MockUpdate()
        update.message.text = '/dallemini'
        main.message_handler(update)
        expected_reply = 'Anna jokin syöte komennon jälkeen. \'[.!/]prompt [syöte]\''
        self.assertEqual(expected_reply, update.message.reply_message_text)

    @mock.patch('requests.post')  # Mock 'requests' module 'post' method.
    def test_dallemini_command_with_prompt(self, mock_post):
        update = MockUpdate()
        update.message.text = '/dallemini 1337'

        # Mock response from the api call
        mock_post.return_value = mock_request_200()
        main.message_handler(update)

        expected_reply = '"_1337_"'
        self.assertEqual(expected_reply, update.message.reply_message_text)

    @mock.patch('requests.post')  # Mock 'requests' module 'post' method.
    def test_dallemini_command_api_call_failure(self, mock_post):
        update = MockUpdate()
        update.message.text = '/dallemini 1337'

        # Mock response from the api call
        mock_post.return_value.status_code = 403
        main.message_handler(update)
        expected_reply = 'Kuvan luominen epäonnistui. Lisätietoa Bobin lokeissa.'
        self.assertEqual(expected_reply, update.message.reply_message_text)

    def test_get_given_prompt(self):
        message = '!dallemini test . test/test-test\ntest\ttest .vai test'
        prompt_expected = 'test . test/test-test\ntest\ttest .vai test'
        prompt_actual = get_given_prompt(message)
        self.assertEqual(prompt_expected, prompt_actual)

    def test_send_image_response(self):
        update = MockUpdate()
        update.message.text = '.dallemini test'
        prompt = 'test'
        expected_image = Image.open('test/resources/test_get_3x3_image_compilation-expected.jpeg')
        send_image_response(update, prompt, expected_image)

        # Message text should be in quotes and in italics
        self.assertEqual('"_test_"', update.message.reply_message_text)

        actual_image_bytes = update.message.reply_image.field_tuple[1]
        actual_image_stream = io.BytesIO(actual_image_bytes)
        actual_image = Image.open(actual_image_stream)

        self.assert_images_are_similar_enough(expected_image, actual_image)

    def test_convert_base64_strings_to_images(self):
        images = convert_base64_strings_to_images(base64_dummy_images)
        self.assertEqual(len(images), 9)
        self.assertEqual(type(images[0]), JpegImageFile)

    def test_get_3x3_image_compilation(self):
        images = convert_base64_strings_to_images(base64_dummy_images)
        actual_image_obj = get_3x3_image_compilation(images)

        # Test dimensions to match
        expected_width = images[0].width * 3
        expected_height = images[0].height * 3
        self.assertEqual(expected_width, actual_image_obj.width, '3x3 image compilation width does not match')
        self.assertEqual(expected_height, actual_image_obj.height, '3x3 image compilation height does not match')

        # Load expected image from disk
        expected_image = Image.open('test/resources/test_get_3x3_image_compilation-expected.jpeg')

        self.assert_images_are_similar_enough(expected_image, actual_image_obj)
        expected_image.close()

    def test_split_to_chunks_basic_cases(self):
        iterable = [0, 1, 2, 3, 4, 5, 6, 7]
        chunk_size = 3
        expected = [[0, 1, 2], [3, 4, 5], [6, 7]]
        self.assertEqual(expected, split_to_chunks(iterable, chunk_size))

        iterable = []
        chunk_size = 3
        expected = []
        self.assertEqual(expected, split_to_chunks(iterable, chunk_size))

        iterable = ['a', 'b', 'c', 'd']
        chunk_size = 1
        expected = [['a'], ['b'], ['c'], ['d']]
        self.assertEqual(expected, split_to_chunks(iterable, chunk_size))

        iterable = None
        chunk_size = 1
        self.assertEqual([], split_to_chunks(iterable, chunk_size))

        iterable = ['a', 'b', 'c', 'd']
        chunk_size = -1
        self.assertEqual(['a', 'b', 'c', 'd'], split_to_chunks(iterable, chunk_size))

    def test_get_image_compilation_file_name(self):
        with patch('dallemini_command.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value = datetime.datetime(1970, 1, 1, 1, 1)

            non_valid_name = '!"#¤%&/()=?``^*@£$€{[]}`\\~`` test \t \n foo-_b.a.r.jpeg'
            expected = '1970-01-01_0101_dalle_mini_with_prompt_test-foo-_barjpeg.jpeg'
            self.assertEqual(expected, get_image_file_name(non_valid_name))

    def assert_images_are_similar_enough(self, image1, image2):
        hash1 = imagehash.average_hash(image1)
        hash2 = imagehash.average_hash(image2)
        hash_bit_difference = hash1 - hash2
        tolerance = 5  # maximum bits that could be different between the hashes.
        self.assertLess(hash_bit_difference, tolerance)


def mock_request_200():
    return MockResponse(
        status_code=200,
        content=str.encode(f'{{"images": {base64_dummy_images},"version":"mega-bf16:v0"}}\n')
    )


def mock_request_200_with_delay():
    sleep(1)
    return mock_request_200()


class MockResponse:
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content

