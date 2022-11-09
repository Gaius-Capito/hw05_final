from django.conf import settings
from django.test import TestCase

from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        expected_object_name = post.text[:settings.POST_CHAR_LENGTH]
        self.assertEqual(expected_object_name, str(post))

        group = PostModelTest.group
        expected_object_name = group.title[:settings.CHAR_LENGTH]
        self.assertEqual(expected_object_name, str(group))

    def test_verbose_name_group(self):
        """Тесты verbose_name группы"""
        group = self.group
        fields = {
            'title': 'Заголовок',
            'description': 'Описание',
        }
        for field, expected_value in fields.items():
            with self.subTest(field=field):
                self.assertEqual(
                    group._meta.get_field(field).verbose_name, expected_value
                )

    def test_verbose_name_post(self):
        """Тесты verbose_name поста"""
        post = self.post
        fields = {
            'text': 'Текст',
            'pub_date': 'Время публикации',
            'author': 'Автор',
            'group': 'Группа',
        }
        for field, expected_value in fields.items():
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).verbose_name, expected_value
                )

    def test_help_text_post(self):
        """Тесты help_text модели post """
        post = self.post
        fields = {
            'text': 'Введите текст поста',
            'group': 'Выберете название группы',
        }
        for value, expected in fields.items():
            with self.subTest(value=value):
                self.assertEqual(
                    post._meta.get_field(value).help_text, expected
                )
